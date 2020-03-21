from contextlib import asynccontextmanager
from typing import (
    Any,
    AsyncContextManager,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Sequence,
    Tuple,
    overload,
)

import anyio

from .._concurrency import open_memory_channel
from ._run_on_each import run_on_each
from ._types import T, U

try:
    from typing_extensions import Literal  # Python 3.7.
except ImportError:  # pragma: no cover
    from typing import Literal  # type: ignore


@overload
def amap(
    async_fn: Callable[[U], Awaitable[T]],
    args: Sequence[U],
    *,
    max_at_once: int = None,
    max_per_second: float = None,
    _include_index: Literal[False] = False,
) -> AsyncContextManager[AsyncIterable[T]]:
    ...  # pragma: no cover


@overload
def amap(
    async_fn: Callable[[U], Awaitable[T]],
    args: Sequence[U],
    *,
    max_at_once: int = None,
    max_per_second: float = None,
    _include_index: Literal[True],
) -> AsyncContextManager[AsyncIterable[Tuple[int, T]]]:
    ...  # pragma: no cover


# Wrap decorator usage so we can properly type this as returning an async context
# manager. (The `AsyncIterator` annotation is correct here, but confusing to type
# checkers on the client side.)
def amap(
    async_fn: Callable[[U], Awaitable],
    args: Sequence[U],
    *,
    max_at_once: int = None,
    max_per_second: float = None,
    _include_index: bool = False,
) -> AsyncContextManager[AsyncIterable]:
    @asynccontextmanager
    async def _amap() -> AsyncIterator[AsyncIterable]:
        receive_channel, send_channel = open_memory_channel[Any](
            max_buffer_size=len(args)
        )

        async with receive_channel, send_channel:
            async with anyio.create_task_group() as task_group:

                async def sender() -> None:
                    await run_on_each(
                        async_fn,
                        args,
                        max_at_once=max_at_once,
                        max_per_second=max_per_second,
                        _include_index=_include_index,
                        _send_to=send_channel,
                    )
                    # Make any `async for ... in results: ...` terminate.
                    await send_channel.aclose()

                await task_group.spawn(sender)

                yield receive_channel

    return _amap()
