import pytest


@pytest.fixture(
    params=[
        pytest.param("asyncio"),
        pytest.param("trio"),
    ]
)
def anyio_backend(request):
    return request.param
