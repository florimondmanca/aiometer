import math
from contextlib import asynccontextmanager
from typing import (
    Any,
    AsyncContextManager,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Literal,
    Optional,
    Sequence,
    Tuple,
    Union,
    overload,
)

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from .._compat import collapse_excgroups
from .run_on_each import run_on_each
from .types import T, U
from .utils import as_async_iter, is_async_iter

@overload
def amap(
    async_fn: Callable[[T], Awaitable[U]],
    args: Sequence[T],
    *,
    max_at_once: Optional[int] = None,
    max_per_second: Optional[float] = None,
    _include_index: Literal[False] = False,
) -> AsyncContextManager[AsyncIterable[U]]:
    ...  # pragma: no cover


@overload
def amap(
    async_fn: Callable[[T], Awaitable[U]],
    args: Sequence[T],
    *,
    max_at_once: Optional[int] = None,
    max_per_second: Optional[float] = None,
    _include_index: Literal[True],
) -> AsyncContextManager[AsyncIterable[Tuple[int, U]]]:
    ...  # pragma: no cover


# Wrap decorator usage so we can properly type this as returning an async context
# manager. (The `AsyncIterator` annotation is correct here, but confusing to type
# checkers on the client side.)
def amap(
    async_fn: Callable[[Any], Awaitable],
    args: Union[Sequence,AsyncIterable],
    *,
    max_at_once: Optional[int] = None,
    max_per_second: Optional[float] = None,
    _include_index: bool = False,
) -> AsyncContextManager[AsyncIterable]:
    
    if not is_async_iter(args):
        args = as_async_iter(args)

    @asynccontextmanager
    async def _amap() -> AsyncIterator[AsyncIterable]:
        try:
            channels: Tuple[
                MemoryObjectSendStream, MemoryObjectReceiveStream
            ] = anyio.create_memory_object_stream(max_buffer_size=len(args))
        except TypeError:
            channels: Tuple[
                MemoryObjectSendStream, MemoryObjectReceiveStream
            ] = anyio.create_memory_object_stream(max_buffer_size=math.inf)

        send_channel, receive_channel = channels

        with send_channel, receive_channel:
            with collapse_excgroups():
                async with anyio.create_task_group() as task_group:

                    async def sender() -> None:
                        # Make any `async for ... in results: ...` terminate.
                        with send_channel:
                            await run_on_each(
                                async_fn,
                                args,
                                max_at_once=max_at_once,
                                max_per_second=max_per_second,
                                _include_index=_include_index,
                                _send_to=send_channel,
                            )

                    task_group.start_soon(sender)

                    yield receive_channel

    return _amap()
