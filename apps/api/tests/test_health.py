import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "notion-resume-api"


@pytest.mark.asyncio
async def test_root(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert "version" in response.json()


@pytest.mark.asyncio
async def test_list_templates(client: AsyncClient) -> None:
    response = await client.get("/api/v1/resumes/templates")
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) == 4
    assert templates[0]["id"] in ("minimal", "modern", "classic", "developer")
