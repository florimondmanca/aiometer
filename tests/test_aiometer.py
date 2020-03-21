import pytest

import aiometer

pytestmark = pytest.mark.asyncio


async def test_run_each() -> None:
    output = set()

    async def process(item: str) -> None:
        output.add(item)

    items = ["apple", "banana", "cherry", "apple"]

    result = await aiometer.run_each(process, items)
    assert result is None

    assert output == {"apple", "banana", "cherry"}


async def test_amap() -> None:
    async def process(item: str) -> str:
        return item.capitalize()

    items = ["apple", "banana", "cherry", "apple"]

    async with aiometer.amap(process, items) as results:
        output = {result async for result in results}

    assert output == {"Apple", "Banana", "Cherry"}


async def test_amap_ignore_results() -> None:
    called = 0

    async def process(item: str) -> None:
        nonlocal called
        called += 1

    items = ["apple", "banana", "cherry", "apple"]

    async with aiometer.amap(process, items):
        # NOTE: will exit when all tasks have completed.
        pass

    assert called == 4


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
