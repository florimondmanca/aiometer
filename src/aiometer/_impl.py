from contextlib import asynccontextmanager
from typing import (
    Any,
    AsyncContextManager,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    NamedTuple,
    Optional,
    Sequence,
    TypeVar,
)

import anyio

from ._concurrency import MemorySendChannel, open_memory_channel

T = TypeVar("T")


class Config(NamedTuple):
    send_to: Optional[MemorySendChannel]


async def _worker(
    async_fn: Callable[..., Awaitable], value: Any, config: Config
) -> None:
    result = await async_fn(value)
    if config.send_to is not None:
        await config.send_to.send(result)


async def run_each(
    async_fn: Callable[..., Awaitable],
    args: Sequence,
    _send_to: MemorySendChannel = None,
) -> None:
    config = Config(send_to=_send_to)
    async with anyio.create_task_group() as task_group:
        for value in args:
            await task_group.spawn(_worker, async_fn, value, config)


# Wrap decorator usage so we can properly type this as returning an async context
# manager. (The `AsyncIterator` annotation is correct here, but confusing to type
# checkers on the client side.)
def amap(
    async_fn: Callable[..., Awaitable[T]], args: Sequence
) -> AsyncContextManager[AsyncIterable[T]]:
    @asynccontextmanager
    async def _amap() -> AsyncIterator[AsyncIterable[T]]:
        receive_channel, send_channel = open_memory_channel[T](
            max_buffer_size=len(args)
        )

        async with receive_channel, send_channel:
            async with anyio.create_task_group() as task_group:

                async def run_each_and_break() -> None:
                    await run_each(async_fn, args=args, _send_to=send_channel)
                    # Make any `async for _ in receive_channel: ...` terminate.
                    await send_channel.aclose()

                await task_group.spawn(run_each_and_break)
                yield receive_channel
                task_group.cancel_scope.cancel()

    return _amap()
