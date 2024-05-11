from typing import Awaitable, Callable, List, NamedTuple, Optional, Sequence, Union, AsyncIterable

import anyio
from anyio.streams.memory import MemoryObjectSendStream

from .meters import HardLimitMeter, Meter, MeterState, RateLimitMeter
from .types import T
from .utils import is_async_iter, as_async_iter


class _Config(NamedTuple):
    include_index: bool
    send_to: Optional[MemoryObjectSendStream]
    meter_states: List[MeterState]


async def _worker(
    async_fn: Callable[[T], Awaitable], index: int, value: T, config: _Config
) -> None:
    result = await async_fn(value)

    if config.send_to is not None:
        if config.include_index:
            result = (index, result)
        await config.send_to.send(result)

    for state in config.meter_states:
        await state.notify_task_finished()


async def run_on_each(
    async_fn: Callable[[T], Awaitable],
    args: Union[Sequence[T], AsyncIterable[T]],
    *,
    max_at_once: Optional[int] = None,
    max_per_second: Optional[float] = None,
    _include_index: bool = False,
    _send_to: Optional[MemoryObjectSendStream] = None,
) -> None:
    meters: List[Meter] = []

    if not is_async_iter(args):
        args = as_async_iter(args)

    if max_at_once is not None:
        meters.append(HardLimitMeter(max_at_once))
    if max_per_second is not None:
        meters.append(RateLimitMeter(max_per_second))

    meter_states = [await meter.new_state() for meter in meters]

    config = _Config(
        include_index=_include_index, send_to=_send_to, meter_states=meter_states
    )

    async with anyio.create_task_group() as task_group:
        index = 0
        async for value in args:
            for state in meter_states:
                await state.wait_task_can_start()

            for state in meter_states:
                await state.notify_task_started()

            task_group.start_soon(_worker, async_fn, index, value, config)
            index += 1
