import sys
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

from .run_on_each import run_on_each
from .types import T, U

if sys.version_info > (3, 8):  # pragma: no cover
    from typing import Literal
else:  # pragma: no cover
    from typing_extensions import Literal

if sys.version_info > (3, 7):  # pragma: no cover
    from contextlib import asynccontextmanager
else:  # pragma: no cover
    from contextlib2 import asynccontextmanager


@overload
def amap(
    async_fn: Callable[[T], Awaitable[U]],
    args: Sequence[T],
    *,
    max_at_once: int = None,
    max_per_second: float = None,
    _include_index: Literal[False] = False,
) -> AsyncContextManager[AsyncIterable[U]]:
    ...  # pragma: no cover


@overload
def amap(
    async_fn: Callable[[T], Awaitable[U]],
    args: Sequence[T],
    *,
    max_at_once: int = None,
    max_per_second: float = None,
    _include_index: Literal[True],
) -> AsyncContextManager[AsyncIterable[Tuple[int, U]]]:
    ...  # pragma: no cover


# Wrap decorator usage so we can properly type this as returning an async context
# manager. (The `AsyncIterator` annotation is correct here, but confusing to type
# checkers on the client side.)
def amap(
    async_fn: Callable[[Any], Awaitable],
    args: Sequence,
    *,
    max_at_once: int = None,
    max_per_second: float = None,
    _include_index: bool = False,
) -> AsyncContextManager[AsyncIterable]:
    @asynccontextmanager
    async def _amap() -> AsyncIterator[AsyncIterable]:
        send_channel, receive_channel = anyio.create_memory_object_stream(
            max_buffer_size=len(args)
        )

        with send_channel, receive_channel:
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
