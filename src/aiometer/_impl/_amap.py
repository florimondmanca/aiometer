from contextlib import asynccontextmanager
from typing import (
    AsyncContextManager,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Literal,
    Sequence,
    Tuple,
    overload,
)

import anyio

from .._concurrency import open_memory_channel
from ._run_each import run_each
from ._types import T, U


@overload
def amap(
    async_fn: Callable[[U], Awaitable[T]], args: Sequence[U],
) -> AsyncContextManager[AsyncIterable[Tuple[T]]]:
    ...  # pragma: no cover


@overload
def amap(
    async_fn: Callable[[U], Awaitable[T]],
    args: Sequence[U],
    _include_index: Literal[False],
) -> AsyncContextManager[AsyncIterable[Tuple[T]]]:
    ...  # pragma: no cover


@overload
def amap(
    async_fn: Callable[[U], Awaitable[T]],
    args: Sequence[U],
    _include_index: Literal[True],
) -> AsyncContextManager[AsyncIterable[Tuple[int, T]]]:
    ...  # pragma: no cover


# Wrap decorator usage so we can properly type this as returning an async context
# manager. (The `AsyncIterator` annotation is correct here, but confusing to type
# checkers on the client side.)
def amap(
    async_fn: Callable[[U], Awaitable[T]],
    args: Sequence[U],
    _include_index: bool = False,
) -> AsyncContextManager[AsyncIterable[T]]:
    @asynccontextmanager
    async def _amap() -> AsyncIterator[AsyncIterable[T]]:
        receive_channel, send_channel = open_memory_channel[T](
            max_buffer_size=len(args)
        )

        async with receive_channel, send_channel:
            async with anyio.create_task_group() as task_group:

                async def run_each_and_break() -> None:
                    await run_each(
                        async_fn,
                        args=args,
                        _include_index=_include_index,
                        _send_to=send_channel,
                    )
                    # Make any `async for _ in receive_channel: ...` terminate.
                    await send_channel.aclose()

                await task_group.spawn(run_each_and_break)
                yield receive_channel
                task_group.cancel_scope.cancel()

    return _amap()
