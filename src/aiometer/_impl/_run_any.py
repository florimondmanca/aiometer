from typing import Awaitable, Callable, Sequence

from ._amap import amap
from ._types import T


async def run_any(
    async_fns: Sequence[Callable[..., Awaitable[T]]], *, max_at_once: int = None
) -> T:
    async with amap(
        lambda fn: fn(), async_fns, max_at_once=max_at_once,
    ) as amap_results:
        return await (amap_results.__aiter__()).__anext__()
