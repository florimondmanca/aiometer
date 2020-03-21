"""
A basic implementation of trio's memory channels over anyio.
See: https://trio.readthedocs.io/en/stable/reference-core.html#trio.open_memory_channel
"""
import types
from typing import Any, AsyncIterator, Generic, Tuple, TypeVar

import anyio

__all__ = ["open_memory_channel", "MemoryReceiveChannel", "MemorySendChannel"]

T = TypeVar("T")


class IterableQueue:
    def __init__(self, capacity: int):
        capacity += 1  # Leave room for `Break` item.
        self._queue = anyio.create_queue(capacity)
        self._break = object()

    async def put(self, item: Any) -> None:
        await self._queue.put(item)

    async def __aiter__(self) -> AsyncIterator:
        while True:
            item = await self._queue.get()
            if item is self._break:
                break
            yield item

    async def aclose(self) -> None:
        if not self._queue.full():
            await self._queue.put(self._break)


class MemoryReceiveChannel(Generic[T]):
    def __init__(self, queue: IterableQueue) -> None:
        self._queue = queue

    async def __aenter__(self) -> None:
        return None

    async def __aiter__(self) -> AsyncIterator[T]:
        async for item in self._queue:
            yield item

    async def aclose(self) -> None:
        await self._queue.aclose()

    async def __aexit__(
        self,
        typ: type = None,
        exc: BaseException = None,
        tb: types.TracebackType = None,
    ) -> None:
        await self.aclose()


class MemorySendChannel(Generic[T]):
    def __init__(self, queue: IterableQueue) -> None:
        self._queue = queue

    async def __aenter__(self) -> None:
        return None

    async def send(self, item: T) -> None:
        await self._queue.put(item)

    async def aclose(self) -> None:
        await self._queue.aclose()

    async def __aexit__(
        self,
        typ: type = None,
        exc: BaseException = None,
        tb: types.TracebackType = None,
    ) -> None:
        await self.aclose()


def _open_memory_channel(max_buffer_size: int) -> tuple:
    queue = IterableQueue(capacity=max_buffer_size)
    return MemoryReceiveChannel(queue), MemorySendChannel(queue)


# Written as a class so we can do `open_memory_channel[int](...)`.
class open_memory_channel(Tuple[MemoryReceiveChannel[T], MemorySendChannel[T]]):
    def __new__(cls, max_buffer_size: int) -> "open_memory_channel":
        return tuple.__new__(open_memory_channel, _open_memory_channel(max_buffer_size))

    # For autocomplete purposes.
    def __init__(self, max_buffer_size: int) -> None:
        ...
