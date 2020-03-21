import random
from typing import Any, List

import anyio
import pytest

import aiometer


@pytest.mark.anyio
async def test_run_each() -> None:
    output = set()

    async def process(item: str) -> None:
        output.add(item)

    items = ["apple", "banana", "cherry", "apple"]

    result = await aiometer.run_each(process, items)
    assert result is None

    assert output == {"apple", "banana", "cherry"}


@pytest.mark.anyio
async def test_amap() -> None:
    async def process(item: str) -> str:
        return item.capitalize()

    items = ["apple", "banana", "cherry", "apple"]

    async with aiometer.amap(process, items) as results:
        output = {result async for result in results}

    assert output == {"Apple", "Banana", "Cherry"}


@pytest.mark.anyio
async def test_amap_ignore_results() -> None:
    called = 0

    async def process(item: str) -> None:
        nonlocal called
        called += 1

    items = ["apple", "banana", "cherry", "apple"]

    async with aiometer.amap(process, items):
        pass

    # Should have waited for all tasks to complete before exiting.
    assert called == 4


@pytest.mark.anyio
async def test_amap_task_exception() -> None:
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
                pass


@pytest.mark.anyio
async def test_run_all() -> None:
    async def process_fast() -> str:
        return "fast"

    async def process_slow() -> str:
        await anyio.sleep(0.1)
        return "slow"

    assert await aiometer.run_all([process_fast, process_slow]) == ["fast", "slow"]
    assert await aiometer.run_all([process_slow, process_fast]) == ["slow", "fast"]


@pytest.mark.anyio
async def test_run_any() -> None:
    async def process_fast() -> str:
        return "fast"

    async def process_slow() -> str:
        await anyio.sleep(0.1)
        return "slow"

    assert await aiometer.run_any([process_slow, process_fast]) == "fast"


@pytest.mark.anyio
class TestMaxAtOnce:
    class _Spy:
        def __init__(self, num_tasks: int) -> None:
            self.num_tasks = num_tasks
            self.num_running = 0
            self.record: List[int] = []

        def build_args(self) -> List[None]:
            return [None for _ in range(self.num_tasks)]

        def build_tasks(self) -> list:
            return [self.process for _ in range(self.num_tasks)]

        async def process(self, *args: Any) -> None:
            self.record.append(self.num_running)
            self.num_running += 1
            await anyio.sleep(0.01 * random.random())
            self.num_running -= 1

        def assert_max_tasks_respected(self, max_at_once: int) -> None:
            assert all(
                num_running < min(self.num_tasks, max_at_once)
                for num_running in self.record
            )

    num_tasks = 10
    values = [1, 2, 5, 10, 20]

    def create_spy(self) -> "_Spy":
        return self._Spy(num_tasks=self.num_tasks)

    @pytest.mark.parametrize("max_at_once", values)
    async def test_run_each(self, max_at_once: int) -> None:
        spy = self.create_spy()
        await aiometer.run_each(spy.process, spy.build_args(), max_at_once=max_at_once)
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
                pass

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
            await aiometer.run_each(process, ["test"], max_at_once=max_at_once)
