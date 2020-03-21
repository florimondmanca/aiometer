from typing import Awaitable, Callable, Dict, List, Sequence

from ._amap import amap
from ._types import T
from ._utils import list_from_indexed_dict


async def run_all(async_fns: Sequence[Callable[..., Awaitable[T]]]) -> List[T]:
    results: Dict[int, T] = {}

    async with amap(lambda fn: fn(), async_fns, _include_index=True) as amap_results:
        async for index, result in amap_results:
            results[index] = result

    return list_from_indexed_dict(results)
