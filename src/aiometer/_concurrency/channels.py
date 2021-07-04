"""
A basic implementation of trio's memory channels for anyio.
See: https://trio.readthedocs.io/en/stable/reference-core.html#trio.open_memory_channel
"""
from typing import Tuple, TypeVar

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream as MemoryReceiveChannel
from anyio.streams.memory import MemoryObjectSendStream as MemorySendChannel

__all__ = ["open_memory_channel", "MemoryReceiveChannel", "MemorySendChannel"]

T = TypeVar("T")


# Written as a class so we can do `open_memory_channel[int](...)`.
class open_memory_channel(Tuple[MemoryReceiveChannel[T], MemorySendChannel[T]]):
    def __new__(cls, max_buffer_size: int) -> "open_memory_channel":
        tx, rx = anyio.create_memory_object_stream(max_buffer_size)

        return tuple.__new__(open_memory_channel, (rx, tx))

    # For autocomplete purposes.
    def __init__(self, max_buffer_size: int) -> None:
        ...
