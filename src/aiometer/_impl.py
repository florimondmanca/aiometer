from typing import Any, Awaitable, Callable, Iterable

import anyio

AsyncFn = Callable[..., Awaitable]


async def _worker(async_fn: AsyncFn, value: Any) -> None:
    await async_fn(value)


async def run_each(async_fn: AsyncFn, args: Iterable) -> None:
    async with anyio.create_task_group() as task_group:
        for value in args:
            await task_group.spawn(_worker, async_fn, value)
