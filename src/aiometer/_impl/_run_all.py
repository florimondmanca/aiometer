from typing import Awaitable, Callable, Dict, List, Sequence

from ._amap import amap
from ._types import T
from ._utils import list_from_indexed_dict


async def run_all(
    async_fns: Sequence[Callable[[], Awaitable[T]]],
    *,
    max_at_once: int = None,
    max_per_second: float = None,
) -> List[T]:
    results: Dict[int, T] = {}

    async with amap(
        lambda fn: fn(),
        async_fns,
        max_at_once=max_at_once,
        max_per_second=max_per_second,
        _include_index=True,
    ) as amap_results:
        async for index, result in amap_results:
            results[index] = result

    return list_from_indexed_dict(results)
