import random
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Awaitable, Callable, List

import anyio
import pytest

import aiometer


@pytest.mark.anyio
class TestRunners:
    async def test_run_on_each(self) -> None:
        output = set()

        async def process(item: str) -> None:
            output.add(item)

        items = ["apple", "banana", "cherry", "apple"]
        result = await aiometer.run_on_each(process, items)

        assert result is None
        assert output == {"apple", "banana", "cherry"}

    async def test_run_all(self) -> None:
        async def process_fast() -> str:
            return "fast"

        async def process_slow() -> str:
            await anyio.sleep(0.01)
            return "slow"

        assert await aiometer.run_all([process_fast, process_slow]) == ["fast", "slow"]
        assert await aiometer.run_all([process_slow, process_fast]) == ["slow", "fast"]

    async def test_amap(self) -> None:
        async def process(item: str) -> str:
            return item.capitalize()

        items = ["apple", "banana", "cherry", "apple"]
        async with aiometer.amap(process, items) as results:
            output = {result async for result in results}

        assert output == {"Apple", "Banana", "Cherry"}

    async def test_amap_ignore_results(self) -> None:
        called = 0

        async def process(item: str) -> None:
            nonlocal called
            called += 1

        items = ["apple", "banana", "cherry", "apple"]
        async with aiometer.amap(process, items):
            pass

        # Should have waited for all tasks to complete before exiting.
        assert called == 4

    # TODO: allow managing exceptions via `outcome`?
    async def test_amap_task_exception(self) -> None:
        class Failure(Exception):
            pass

        async def process(item: str) -> str:
            if item == "fail":
                raise Failure
            return item

        items = ["apple", "banana", "fail", "apple"]
        with pytest.raises(Failure):
            async with aiometer.amap(process, items) as results:
                async for result in results:
                    pass  # pragma: no cover  # Python 3.7 fix.

    async def test_run_any(self) -> None:
        async def process_fast() -> str:
            return "fast"

        async def process_slow() -> str:
            await anyio.sleep(0.01)
            return "slow"

        assert await aiometer.run_any([process_slow, process_fast]) == "fast"


@pytest.mark.anyio
class TestMaxAtOnce:
    class _Spy:
        def __init__(self, num_tasks: int) -> None:
            self.num_tasks = num_tasks
            self.num_running = 0
            self.max_running = 0

        def build_args(self) -> List[None]:
            return [None for _ in range(self.num_tasks)]

        def build_tasks(self) -> list:
            return [self.process for _ in range(self.num_tasks)]

        async def process(self, *args: Any) -> None:
            self.num_running += 1
            self.max_running = max(self.num_running, self.max_running)
            await anyio.sleep(0.01 * random.random())
            self.num_running -= 1

        def assert_max_tasks_respected(self, max_at_once: int) -> None:
            assert self.max_running <= max_at_once

    num_tasks = 10
    values = [1, 2, 5, 10, 20]

    def create_spy(self) -> "_Spy":
        return self._Spy(num_tasks=self.num_tasks)

    @pytest.mark.parametrize("max_at_once", values)
    async def test_run_on_each(self, max_at_once: int) -> None:
        spy = self.create_spy()
        await aiometer.run_on_each(
            spy.process, spy.build_args(), max_at_once=max_at_once
        )
        spy.assert_max_tasks_respected(max_at_once)

    @pytest.mark.parametrize("max_at_once", values)
    async def test_run_all(self, max_at_once: int) -> None:
        spy = self.create_spy()
        await aiometer.run_all(spy.build_tasks(), max_at_once=max_at_once)
        spy.assert_max_tasks_respected(max_at_once)

    @pytest.mark.parametrize("max_at_once", values)
    async def test_amap(self, max_at_once: int) -> None:
        spy = self.create_spy()

        async with aiometer.amap(
            spy.process, spy.build_args(), max_at_once=max_at_once
        ) as results:
            async for _ in results:
                pass  # pragma: no cover  # Python 3.7 fix.

        spy.assert_max_tasks_respected(max_at_once)

    @pytest.mark.parametrize("max_at_once", values)
    async def test_run_any(self, max_at_once: int) -> None:
        spy = self.create_spy()
        await aiometer.run_any(spy.build_tasks(), max_at_once=max_at_once)
        spy.assert_max_tasks_respected(max_at_once)

    @pytest.mark.parametrize("max_at_once", (0, -1, -10))
    async def test_max_at_once_must_be_positive(self, max_at_once: int) -> None:
        async def process(item: str) -> None:
            pass  # pragma: no cover

        with pytest.raises(ValueError):
            await aiometer.run_on_each(process, ["test"], max_at_once=max_at_once)


@pytest.mark.anyio
class TestMaxPerSecond:
    class _Spy:
        def __init__(self, num_tasks: int, task: Callable[[], Awaitable[None]]) -> None:
            self.num_tasks = num_tasks
            self.task = task
            self.num_started = 0
            self.start = time.time()

        def build_args(self) -> List[None]:
            return [None for _ in range(self.num_tasks)]

        def build_tasks(self) -> list:
            return [self.process for _ in range(self.num_tasks)]

        async def process(self, *args: Any) -> None:
            self.num_started += 1
            await self.task()

    values = [1, 2, 5, 10, 25, 100]

    @asynccontextmanager
    async def create_spy(self, max_per_second: float) -> AsyncIterator["_Spy"]:
        # Simplest would be to look at how many tasks have started within 1 second,
        # but tests would then be too slow.
        # So, scale this down (but not too much)...
        task_seconds = 0.1
        # ...and take it into account to run more tasks:
        num_tasks = int(max(self.values) / task_seconds)

        spy = self._Spy(num_tasks=num_tasks, task=lambda: anyio.sleep(task_seconds))
        wait = task_seconds * 1.1  # Give it a better chance to spawn all tasks.
        async with anyio.move_on_after(wait):
            yield spy

        expected_num_started = max(1, round(task_seconds * max_per_second))
        assert spy.num_started == pytest.approx(expected_num_started, abs=1)

    @pytest.mark.parametrize("max_per_second", values)
    async def test_run_on_each(self, max_per_second: float) -> None:
        async with self.create_spy(max_per_second) as spy:
            await aiometer.run_on_each(
                spy.process, spy.build_args(), max_per_second=max_per_second
            )

    @pytest.mark.parametrize("max_per_second", values)
    async def test_run_all(self, max_per_second: float) -> None:
        async with self.create_spy(max_per_second) as spy:
            await aiometer.run_all(spy.build_tasks(), max_per_second=max_per_second)

    @pytest.mark.parametrize("max_per_second", values)
    async def test_amap(self, max_per_second: float) -> None:
        async with self.create_spy(max_per_second) as spy:
            async with aiometer.amap(
                spy.process, spy.build_args(), max_per_second=max_per_second
            ) as results:
                async for _ in results:
                    pass  # pragma: no cover  # Python 3.7 fix.

    @pytest.mark.parametrize("max_per_second", values)
    async def test_run_any(self, max_per_second: float) -> None:
        async with self.create_spy(max_per_second) as spy:
            await aiometer.run_any(spy.build_tasks(), max_per_second=max_per_second)
