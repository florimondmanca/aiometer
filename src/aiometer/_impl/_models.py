from typing import List, NamedTuple, Optional

import anyio

from .._concurrency import MemorySendChannel
from ._utils import check_strictly_positive


class MeterState:
    async def wait_task_can_start(self) -> None:
        raise NotImplementedError  # pragma: no cover

    def notify_task_started(self) -> None:
        raise NotImplementedError  # pragma: no cover

    async def notify_task_finished(self) -> None:
        raise NotImplementedError  # pragma: no cover


class Meter:
    def new_state(self) -> MeterState:
        raise NotImplementedError  # pragma: no cover


class MaxAtOnceMeter(Meter):
    class State(MeterState):
        def __init__(self, max_at_once: int) -> None:
            self.semaphore = anyio.create_semaphore(max_at_once)

        async def wait_task_can_start(self) -> None:
            # anyio semaphore interface has no '.acquire()'.
            await self.semaphore.__aenter__()

        def notify_task_started(self) -> None:
            pass

        async def notify_task_finished(self) -> None:
            # anyio semaphore interface has no '.release()'.
            await self.semaphore.__aexit__(None, None, None)

    def __init__(self, max_at_once: int) -> None:
        check_strictly_positive("max_at_once", max_at_once)
        self.max_at_once = max_at_once

    def new_state(self) -> MeterState:
        return type(self).State(self.max_at_once)


class Config(NamedTuple):
    include_index: bool
    send_to: Optional[MemorySendChannel]
    meter_states: List[MeterState]
