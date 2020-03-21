from typing import Any, Awaitable, Callable, Sequence

import anyio

from .._concurrency import MemorySendChannel
from ._models import Config
from ._types import T, U


async def _worker(
    async_fn: Callable[..., Awaitable[T]], index: int, value: T, config: Config
) -> None:
    result: Any = await async_fn(value)

    if config.send_to is None:
        return

    if config.include_index:
        result = (index, result)
    await config.send_to.send(result)


async def run_each(
    async_fn: Callable[[U], Awaitable],
    args: Sequence[U],
    *,
    _include_index: bool = False,
    _send_to: MemorySendChannel = None,
) -> None:
    config = Config(include_index=_include_index, send_to=_send_to)
    async with anyio.create_task_group() as task_group:
        for index, value in enumerate(args):
            await task_group.spawn(_worker, async_fn, index, value, config)
