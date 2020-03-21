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
