"""
Tests for critical paths:
- Agent creation / CRUD
- Workflow execution
- Message delivery
"""

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Use in-memory SQLite for tests
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

import os
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["OPENAI_API_KEY"] = "sk-test-dummy"  # Will be mocked

from backend.db.models import Base
from backend.db.session import AsyncSessionLocal
from backend.main import app


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    """Create all tables in the test database."""
    from backend.db.session import engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# ─────────────────────────────────────────────
#  Agent CRUD Tests
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_agent(client):
    """Test agent creation with all required fields."""
    payload = {
        "name": "Test Researcher",
        "role": "Research Specialist",
        "system_prompt": "You are an expert research assistant.",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "tools": ["web_search"],
        "memory_enabled": True,
        "memory_window": 20,
        "max_tokens": 2048,
        "temperature": 0.7,
        "max_iterations": 5,
    }
    response = await client.post("/api/agents/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Researcher"
    assert data["role"] == "Research Specialist"
    assert data["tools"] == ["web_search"]
    assert "id" in data
    assert "created_at" in data
    return data["id"]


@pytest.mark.asyncio
async def test_list_agents(client):
    """Test listing agents returns array."""
    response = await client.get("/api/agents/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_agent(client):
    """Test fetching a specific agent."""
    # Create first
    create_resp = await client.post("/api/agents/", json={
        "name": "Get Test Agent",
        "role": "Assistant",
        "system_prompt": "You are helpful.",
        "tools": [],
    })
    agent_id = create_resp.json()["id"]

    response = await client.get(f"/api/agents/{agent_id}")
    assert response.status_code == 200
    assert response.json()["id"] == agent_id


@pytest.mark.asyncio
async def test_update_agent(client):
    """Test updating agent fields."""
    create_resp = await client.post("/api/agents/", json={
        "name": "Update Test Agent",
        "role": "Writer",
        "system_prompt": "You write content.",
        "tools": [],
    })
    agent_id = create_resp.json()["id"]

    update_resp = await client.put(f"/api/agents/{agent_id}", json={
        "name": "Updated Writer",
        "temperature": 0.9,
    })
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Updated Writer"
    assert update_resp.json()["temperature"] == 0.9


@pytest.mark.asyncio
async def test_delete_agent(client):
    """Test agent deletion."""
    create_resp = await client.post("/api/agents/", json={
        "name": "Delete Me",
        "role": "Temp",
        "system_prompt": "Temporary agent.",
        "tools": [],
    })
    agent_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/agents/{agent_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/agents/{agent_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_agent(client):
    """Test 404 for missing agent."""
    response = await client.get("/api/agents/nonexistent-id-xyz")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_tools(client):
    """Test tool registry endpoint."""
    response = await client.get("/api/agents/tools")
    assert response.status_code == 200
    tools = response.json()
    assert isinstance(tools, list)
    assert len(tools) > 0
    # All tools must have name and description
    for tool in tools:
        assert "name" in tool
        assert "description" in tool


# ─────────────────────────────────────────────
#  Workflow Tests
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_workflow(client):
    """Test workflow creation with nodes and edges."""
    payload = {
        "name": "Test Workflow",
        "description": "A test pipeline",
        "nodes": [
            {"id": "n1", "node_type": "input", "label": "Input", "position": {"x": 0, "y": 0}},
            {"id": "n2", "node_type": "output", "label": "Output", "position": {"x": 300, "y": 0}},
        ],
        "edges": [
            {"source": "n1", "target": "n2", "label": "pass-through"},
        ],
    }
    response = await client.post("/api/workflows/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Workflow"
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1


@pytest.mark.asyncio
async def test_list_workflow_templates(client):
    """Test that built-in templates are returned."""
    response = await client.get("/api/workflows/templates")
    assert response.status_code == 200
    templates = response.json()
    assert isinstance(templates, list)
    assert len(templates) >= 2  # Research Pipeline + Content Review Loop
    keys = [t["key"] for t in templates]
    assert "research_pipeline" in keys
    assert "content_review_loop" in keys


@pytest.mark.asyncio
async def test_create_workflow_from_template(client):
    """Test instantiating a workflow from a template."""
    response = await client.post("/api/workflows/templates/research_pipeline")
    assert response.status_code == 201
    data = response.json()
    assert "Research" in data["name"]
    assert len(data["nodes"]) >= 3


@pytest.mark.asyncio
async def test_workflow_run_created(client):
    """Test that a workflow run is created (execution is async)."""
    # Create a simple workflow
    wf_resp = await client.post("/api/workflows/", json={
        "name": "Run Test Workflow",
        "nodes": [
            {"id": "in", "node_type": "input", "label": "In", "position": {"x": 0, "y": 0}},
            {"id": "out", "node_type": "output", "label": "Out", "position": {"x": 200, "y": 0}},
        ],
        "edges": [{"source": "in", "target": "out"}],
    })
    wf_id = wf_resp.json()["id"]

    run_resp = await client.post(f"/api/workflows/{wf_id}/run", json={
        "input": "test input",
        "trigger": "manual",
    })
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["workflow_id"] == wf_id
    assert run_data["status"] in ("pending", "running", "completed")


@pytest.mark.asyncio
async def test_get_workflow_runs(client):
    """Test listing workflow runs."""
    wf_resp = await client.post("/api/workflows/", json={
        "name": "Runs List Test",
        "nodes": [],
        "edges": [],
    })
    wf_id = wf_resp.json()["id"]

    response = await client.get(f"/api/workflows/{wf_id}/runs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ─────────────────────────────────────────────
#  Monitor Tests
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_monitor_stats(client):
    """Test monitor stats endpoint returns expected fields."""
    response = await client.get("/api/monitor/stats")
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    assert "total_runs" in data
    assert "total_tokens" in data
    assert "total_cost_usd" in data


@pytest.mark.asyncio
async def test_monitor_logs(client):
    """Test log retrieval."""
    response = await client.get("/api/monitor/logs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test health check."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


# ─────────────────────────────────────────────
#  Message Delivery Tests
# ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_message_history_empty_new_session(client):
    """Test message history returns empty list for new session."""
    # Create an agent
    agent_resp = await client.post("/api/agents/", json={
        "name": "History Test Agent",
        "role": "Assistant",
        "system_prompt": "You are helpful.",
        "tools": [],
    })
    agent_id = agent_resp.json()["id"]

    response = await client.get(f"/api/agents/{agent_id}/messages/brand-new-session-xyz")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_sessions_list_empty(client):
    """Test sessions list is empty for new agent."""
    agent_resp = await client.post("/api/agents/", json={
        "name": "Sessions Test Agent",
        "role": "Assistant",
        "system_prompt": "You are helpful.",
        "tools": [],
    })
    agent_id = agent_resp.json()["id"]

    response = await client.get(f"/api/agents/{agent_id}/sessions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
