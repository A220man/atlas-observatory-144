import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_full_workflow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/projects", json={"name": "Test Project", "path": "/tmp/test"})
        assert response.status_code == 200
        project = response.json()
        project_id = project["id"]
        
        response = await client.post("/sessions", json={"project_id": project_id, "title": "Test Session"})
        assert response.status_code == 200
        session = response.json()
        session_id = session["id"]
        
        response = await client.post("/observations", json={
            "session_id": session_id,
            "type": "bugfix",
            "title": "Fix login bug",
            "narrative": "Fixed the login authentication issue",
            "metadata": {"severity": "high"}
        })
        assert response.status_code == 200
        
        response = await client.post("/context", json={
            "project_id": project_id,
            "query": "login",
            "limit": 10
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert "login" in data[0]["title"].lower() or "login" in data[0]["narrative"].lower()
