from typing import Any, Awaitable, Callable, List, NamedTuple, Optional, Sequence

import anyio

from .._concurrency import MemorySendChannel
from ._meters import MaxAtOnceMeter, Meter, MeterState, TokenBucketMeter
from ._types import T, U


class _Config(NamedTuple):
    include_index: bool
    send_to: Optional[MemorySendChannel]
    meter_states: List[MeterState]


async def _worker(
    async_fn: Callable[[U], Awaitable[T]], index: int, value: U, config: _Config
) -> None:
    result: Any = await async_fn(value)

    if config.send_to is not None:
        if config.include_index:
            result = (index, result)
        await config.send_to.send(result)

    for state in config.meter_states:
        await state.notify_task_finished()


async def run_on_each(
    async_fn: Callable[[U], Awaitable],
    args: Sequence[U],
    *,
    max_at_once: int = None,
    max_per_second: float = None,
    _include_index: bool = False,
    _send_to: MemorySendChannel = None,
) -> None:
    meters: List[Meter] = []

    if max_at_once is not None:
        meters.append(MaxAtOnceMeter(max_at_once))
    if max_per_second is not None:
        meters.append(TokenBucketMeter(max_per_second))

    meter_states = [await meter.new_state() for meter in meters]

    config = _Config(
        include_index=_include_index, send_to=_send_to, meter_states=meter_states
    )

    async with anyio.create_task_group() as task_group:
        for index, value in enumerate(args):
            for state in meter_states:
                await state.wait_task_can_start()

            for state in meter_states:
                await state.notify_task_started()

            await task_group.spawn(_worker, async_fn, index, value, config)
