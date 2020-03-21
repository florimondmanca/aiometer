import anyio

from ._utils import check_strictly_positive


class MeterState:
    async def wait_task_can_start(self) -> None:
        raise NotImplementedError  # pragma: no cover

    async def notify_task_started(self) -> None:
        raise NotImplementedError  # pragma: no cover

    async def notify_task_finished(self) -> None:
        raise NotImplementedError  # pragma: no cover


class Meter:
    async def new_state(self) -> MeterState:
        raise NotImplementedError  # pragma: no cover


class MaxAtOnceMeter(Meter):
    class State(MeterState):
        def __init__(self, max_at_once: int) -> None:
            self.semaphore = anyio.create_semaphore(max_at_once)

        async def wait_task_can_start(self) -> None:
            # anyio semaphore interface has no '.acquire()'.
            await self.semaphore.__aenter__()

        async def notify_task_started(self) -> None:
            pass

        async def notify_task_finished(self) -> None:
            # anyio semaphore interface has no '.release()'.
            await self.semaphore.__aexit__(None, None, None)

    def __init__(self, max_at_once: int) -> None:
        check_strictly_positive("max_at_once", max_at_once)
        self.max_at_once = max_at_once

    async def new_state(self) -> MeterState:
        return type(self).State(self.max_at_once)


class TokenBucketMeter(Meter):
    class State(MeterState):
        def __init__(self, max_per_second: float, now: float) -> None:
            self.max_per_second = max_per_second
            self.max_bursts = 1  # TODO: make this configurable
            self.last_update_time = now
            self.tokens = 1  # type: float  # Allow accumulating partial tokens.

        async def _update(self) -> None:
            now = await anyio.current_time()
            elapsed = now - self.last_update_time
            self.tokens += elapsed * self.max_per_second
            self.tokens = min(self.tokens, self.max_bursts)
            self.last_update_time = now

        async def wait_task_can_start(self) -> None:
            while True:
                await self._update()
                if self.tokens >= 1:
                    break
                wait_next_token = max(0, (1 - self.tokens) / self.max_per_second)
                await anyio.sleep(wait_next_token)

        async def notify_task_started(self) -> None:
            await self._update()
            if self.tokens < 1:  # pragma: no cover
                raise RuntimeError("Should be at least one token left")
            self.tokens -= 1

        async def notify_task_finished(self) -> None:
            pass

    def __init__(self, max_per_second: float) -> None:
        check_strictly_positive("max_per_second", max_per_second)
        self.max_per_second = max_per_second

    async def new_state(self) -> MeterState:
        now = await anyio.current_time()
        return type(self).State(self.max_per_second, now=now)
