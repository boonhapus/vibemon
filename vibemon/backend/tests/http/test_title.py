"""HTTP title-screen route tests."""

from litestar.testing import AsyncTestClient
import pytest

from app.http.app import create_app


@pytest.fixture
def http_app():
    return create_app()


@pytest.fixture
async def client(http_app):
    async with AsyncTestClient(app=http_app) as test_client:
        yield test_client


async def test_list_title_mons_empty(client: AsyncTestClient) -> None:
    response = await client.get("/api/title/mons?count=4")
    assert response.status_code == 200
    assert response.json() == {"mons": []}
