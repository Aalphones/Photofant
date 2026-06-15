from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from photofant.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.mark.asyncio
async def test_health_ok(app) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
