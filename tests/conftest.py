import pytest
from httpx import AsyncClient

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "admin123"


@pytest.fixture
async def client():
    async with AsyncClient(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {API_KEY}"},
        timeout=60,
    ) as ac:
        yield ac
