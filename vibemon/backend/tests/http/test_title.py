"""HTTP title-screen route tests."""

from collections.abc import AsyncGenerator

from litestar import Litestar
from litestar.testing import AsyncTestClient
import pytest

from app.http.app import create_app


@pytest.fixture
def http_app() -> Litestar:
    return create_app()


@pytest.fixture
async def client(http_app: Litestar) -> AsyncGenerator[AsyncTestClient[Litestar]]:
    async with AsyncTestClient(app=http_app) as test_client:
        yield test_client


async def test_list_title_mons_empty(client: AsyncTestClient[Litestar]) -> None:
    response = await client.get("/api/title/mons?count=4")
    assert response.status_code == 200
    assert response.json() == {"mons": []}
