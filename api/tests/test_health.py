import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["checks"]["redis"] == "ok"


@pytest.mark.asyncio
async def test_root(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "notion-resume-api"
    assert data["docs"] == "/docs"


@pytest.mark.asyncio
async def test_list_templates(client: AsyncClient) -> None:
    response = await client.get("/api/v1/resumes/templates")
    assert response.status_code == 200
    templates = response.json()
    assert len(templates) == 7
    template_ids = {t["id"] for t in templates}
    assert template_ids == {
        "enhance",
        "ats-meridian",
        "minimal",
        "modern",
        "classic",
        "developer",
        "modern-canva",
    }
