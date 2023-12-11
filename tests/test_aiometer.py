import random
from contextlib import contextmanager
from typing import Any, Callable, Iterator, List

import anyio
import pytest

import aiometer

from ._utils import pairwise


@pytest.mark.anyio
class TestRunners:
    async def test_run_on_each(self) -> None:
        output = set()

        async def process(item: str) -> None:
            output.add(item)

        items = ["apple", "banana", "cherry", "apple"]
        await aiometer.run_on_each(process, items)

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
                    pass  # pragma: nopy38

    async def test_run_any(self) -> None:
        async def process_fast() -> str:
            return "fast"

        async def process_slow() -> str:
            await anyio.sleep(0.01)
            return "slow"

        assert await aiometer.run_any([process_slow, process_fast]) == "fast"

    @pytest.mark.parametrize("run", [aiometer.run_all, aiometer.run_any])
    async def test_disallow_buggy_lambdas(self, run: Callable) -> None:
        items = ["apple", "banana", "cherry", "apple"]

        async def process(item: str) -> None:
            pass  # pragma: no cover

        async_fns = [lambda: process(item) for item in items]

        with pytest.raises(ValueError) as exc_info:
            await run(async_fns)

        # Ensure the message is specific and provides a hint for a fix.
        message = str(exc_info.value)
        assert run.__name__ in message
        assert "functools.partial" in message


@pytest.mark.anyio
class TestMaxAtOnce:
    class Spy:
        def __init__(self, num_tasks: int) -> None:
            self.num_tasks = num_tasks
            self.num_running = 0
            self.max_running = 0
            self.async_fns = [self.async_fn for _ in range(self.num_tasks)]
            self.args = [None for _ in range(self.num_tasks)]

        async def async_fn(self, *args: Any) -> None:
            self.num_running += 1
            self.max_running = max(self.num_running, self.max_running)
            await anyio.sleep(0.01 * random.random())
            self.num_running -= 1

    max_at_once_params = [1, 2, 5, 10, 20]

    @classmethod
    @contextmanager
    def assert_limit(cls, max_at_once: int) -> Iterator["Spy"]:
        spy = cls.Spy(num_tasks=max(cls.max_at_once_params) + 10)
        yield spy
        assert 0 < spy.max_running <= max_at_once

    @pytest.mark.slow
    @pytest.mark.parametrize("max_at_once", max_at_once_params)
    async def test_run_on_each(self, max_at_once: int) -> None:
        with self.assert_limit(max_at_once) as spy:
            await aiometer.run_on_each(spy.async_fn, spy.args, max_at_once=max_at_once)

    @pytest.mark.slow
    @pytest.mark.parametrize("max_at_once", max_at_once_params)
    async def test_run_all(self, max_at_once: int) -> None:
        with self.assert_limit(max_at_once) as spy:
            await aiometer.run_all(spy.async_fns, max_at_once=max_at_once)

    @pytest.mark.slow
    @pytest.mark.parametrize("max_at_once", max_at_once_params)
    async def test_amap(self, max_at_once: int) -> None:
        with self.assert_limit(max_at_once) as spy:
            async with aiometer.amap(
                spy.async_fn, spy.args, max_at_once=max_at_once
            ) as results:
                async for _ in results:
                    pass  # pragma: nopy38

    @pytest.mark.slow
    @pytest.mark.parametrize("max_at_once", max_at_once_params)
    async def test_run_any(self, max_at_once: int) -> None:
        with self.assert_limit(max_at_once) as spy:
            await aiometer.run_any(spy.async_fns, max_at_once=max_at_once)

    @pytest.mark.parametrize("max_at_once", (0, -1, -10))
    async def test_max_at_once_must_be_positive(self, max_at_once: int) -> None:
        async def async_fn(item: str) -> None:
            pass  # pragma: no cover

        with pytest.raises(ValueError):
            await aiometer.run_on_each(async_fn, ["test"], max_at_once=max_at_once)


@pytest.mark.anyio
class TestMaxPerSecond:
    class Spy:
        def __init__(self, num_tasks: int) -> None:
            self.tasks = [self.task for _ in range(num_tasks)]
            self.args = [None for _ in range(num_tasks)]
            self.start_times: List[float] = []

        async def task(self, *args: Any) -> None:
            time = float(anyio.current_time())
            self.start_times.append(time)

        @property
        def max_task_delta(self) -> float:
            return max(t2 - t1 for t1, t2 in pairwise(self.start_times))

    max_per_second_params = [5, 10, 20, 30, 40, 50, 70, 100]

    @classmethod
    @contextmanager
    def assert_limit(cls, max_per_second: float) -> Iterator["Spy"]:
        spy = cls.Spy(num_tasks=3)
        yield spy
        period = 1 / max_per_second
        assert spy.max_task_delta == pytest.approx(period, rel=0.75)

    @pytest.mark.slow
    @pytest.mark.parametrize("max_per_second", max_per_second_params)
    async def test_run_on_each(self, max_per_second: float) -> None:
        with self.assert_limit(max_per_second) as spy:
            await aiometer.run_on_each(
                spy.task, spy.args, max_per_second=max_per_second
            )

    @pytest.mark.slow
    @pytest.mark.parametrize("max_per_second", max_per_second_params)
    async def test_run_all(self, max_per_second: float) -> None:
        with self.assert_limit(max_per_second) as spy:
            await aiometer.run_all(spy.tasks, max_per_second=max_per_second)

    @pytest.mark.slow
    @pytest.mark.parametrize("max_per_second", max_per_second_params)
    async def test_amap(self, max_per_second: float) -> None:
        with self.assert_limit(max_per_second) as spy:
            async with aiometer.amap(
                spy.task, spy.args, max_per_second=max_per_second
            ) as results:
                async for _ in results:
                    pass  # pragma: nopy38

    @pytest.mark.slow
    @pytest.mark.parametrize("max_per_second", max_per_second_params)
    async def test_run_any(self, max_per_second: float) -> None:
        with self.assert_limit(max_per_second) as spy:
            await aiometer.run_any(spy.tasks, max_per_second=max_per_second)
