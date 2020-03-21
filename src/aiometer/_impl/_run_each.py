from typing import Any, Awaitable, Callable, List, Sequence

import anyio

from .._concurrency import MemorySendChannel
from ._models import Config, MaxAtOnceMeter, Meter
from ._types import T, U


async def _worker(
    async_fn: Callable[..., Awaitable[T]], index: int, value: T, config: Config
) -> None:
    result: Any = await async_fn(value)

    if config.send_to is not None:
        if config.include_index:
            result = (index, result)
        await config.send_to.send(result)

    for state in config.meter_states:
        await state.notify_task_finished()


async def run_each(
    async_fn: Callable[[U], Awaitable],
    args: Sequence[U],
    *,
    max_at_once: int = None,
    _include_index: bool = False,
    _send_to: MemorySendChannel = None,
) -> None:
    meters: List[Meter] = []

    if max_at_once is not None:
        meters.append(MaxAtOnceMeter(max_at_once))

    meter_states = [meter.new_state() for meter in meters]

    config = Config(
        include_index=_include_index, send_to=_send_to, meter_states=meter_states
    )

    async with anyio.create_task_group() as task_group:
        for index, value in enumerate(args):
            for state in meter_states:
                await state.wait_task_can_start()

            for state in meter_states:
                state.notify_task_started()

            await task_group.spawn(_worker, async_fn, index, value, config)
