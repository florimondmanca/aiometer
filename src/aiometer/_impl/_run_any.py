from typing import Awaitable, Callable, Sequence

from ._amap import amap
from ._types import T


async def run_any(
    async_fns: Sequence[Callable[[], Awaitable[T]]],
    *,
    max_at_once: int = None,
    max_per_second: float = None,
) -> T:
    async with amap(
        lambda fn: fn(),
        async_fns,
        max_at_once=max_at_once,
        max_per_second=max_per_second,
    ) as results:
        return await (results.__aiter__()).__anext__()
