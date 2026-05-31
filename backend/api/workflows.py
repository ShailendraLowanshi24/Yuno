"""
Workflow API — CRUD, templates, execution, and run history.
"""

from __future__ import annotations

import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import (
    Workflow, WorkflowNode, WorkflowEdge, WorkflowRun, RunLog,
    WorkflowStatus, RunStatus, get_db
)
from ..workflows.engine import trigger_workflow, WORKFLOW_TEMPLATES

router = APIRouter(prefix="/workflows", tags=["Workflows"])


# ─────────────────────────────────────────────
#  Schemas
# ─────────────────────────────────────────────

class NodeCreate(BaseModel):
    id: Optional[str] = None
    node_type: str = "agent"
    label: str
    agent_id: Optional[str] = None
    position: dict = Field(default_factory=lambda: {"x": 0, "y": 0})
    config: dict = {}


class EdgeCreate(BaseModel):
    id: Optional[str] = None
    source: str
    target: str
    condition: Optional[str] = None
    label: Optional[str] = None


class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    nodes: List[NodeCreate] = []
    edges: List[EdgeCreate] = []
    graph_layout: dict = {}


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[NodeCreate]] = None
    edges: Optional[List[EdgeCreate]] = None
    graph_layout: Optional[dict] = None
    status: Optional[str] = None


class WorkflowRunRequest(BaseModel):
    input: str
    trigger: str = "manual"


# ─────────────────────────────────────────────
#  Workflow CRUD
# ─────────────────────────────────────────────

@router.get("/")
async def list_workflows(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .order_by(desc(Workflow.created_at))
    )
    return [w.to_dict() for w in result.unique().scalars().all()]


@router.post("/", status_code=201)
async def create_workflow(payload: WorkflowCreate, db: AsyncSession = Depends(get_db)):
    workflow = Workflow(
        id=str(uuid.uuid4()),
        name=payload.name,
        description=payload.description,
        graph_layout=payload.graph_layout,
    )
    db.add(workflow)
    await db.flush()

    # Create nodes
    for n in payload.nodes:
        node = WorkflowNode(
            id=n.id or str(uuid.uuid4()),
            workflow_id=workflow.id,
            agent_id=n.agent_id,
            node_type=n.node_type,
            label=n.label,
            position_x=n.position.get("x", 0),
            position_y=n.position.get("y", 0),
            config=n.config,
        )
        db.add(node)

    # Create edges
    for e in payload.edges:
        edge = WorkflowEdge(
            id=e.id or str(uuid.uuid4()),
            workflow_id=workflow.id,
            source_node_id=e.source,
            target_node_id=e.target,
            condition=e.condition,
            label=e.label,
        )
        db.add(edge)

    await db.commit()

    # Re-load with relationships
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .where(Workflow.id == workflow.id)
    )
    return result.unique().scalar_one().to_dict()


@router.get("/templates")
async def list_templates():
    """Return all pre-built workflow templates."""
    return [
        {
            "key": key,
            "name": tpl["name"],
            "description": tpl["description"],
            "nodes": tpl["nodes"],
            "edges": tpl["edges"],
        }
        for key, tpl in WORKFLOW_TEMPLATES.items()
    ]


@router.post("/templates/{template_key}", status_code=201)
async def create_from_template(
    template_key: str,
    db: AsyncSession = Depends(get_db),
):
    """Instantiate a workflow from a built-in template."""
    tpl = WORKFLOW_TEMPLATES.get(template_key)
    if not tpl:
        raise HTTPException(404, f"Template '{template_key}' not found")

    workflow = Workflow(
        id=str(uuid.uuid4()),
        name=tpl["name"],
        description=tpl["description"],
        is_template=True,
        template_name=template_key,
        graph_layout={},
    )
    db.add(workflow)
    await db.flush()

    node_id_map = {}
    for n in tpl["nodes"]:
        new_id = str(uuid.uuid4())
        node_id_map[n["id"]] = new_id
        node = WorkflowNode(
            id=new_id,
            workflow_id=workflow.id,
            node_type=n["node_type"],
            label=n["label"],
            position_x=n["position"]["x"],
            position_y=n["position"]["y"],
            config=n.get("config", {}),
        )
        db.add(node)

    for e in tpl["edges"]:
        edge = WorkflowEdge(
            id=str(uuid.uuid4()),
            workflow_id=workflow.id,
            source_node_id=node_id_map[e["source"]],
            target_node_id=node_id_map[e["target"]],
            condition=e.get("condition"),
            label=e.get("label"),
        )
        db.add(edge)

    await db.commit()

    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .where(Workflow.id == workflow.id)
    )
    return result.unique().scalar_one().to_dict()


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .where(Workflow.id == workflow_id)
    )
    w = result.unique().scalar_one_or_none()
    if not w:
        raise HTTPException(404, "Workflow not found")
    return w.to_dict()


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    payload: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .where(Workflow.id == workflow_id)
    )
    workflow = result.unique().scalar_one_or_none()
    if not workflow:
        raise HTTPException(404, "Workflow not found")

    if payload.name is not None:
        workflow.name = payload.name
    if payload.description is not None:
        workflow.description = payload.description
    if payload.graph_layout is not None:
        workflow.graph_layout = payload.graph_layout
    if payload.status is not None:
        workflow.status = payload.status

    # Replace nodes/edges if provided
    if payload.nodes is not None:
        for n in workflow.nodes:
            await db.delete(n)
        for e in workflow.edges:
            await db.delete(e)
        await db.flush()

        for n in payload.nodes:
            node = WorkflowNode(
                id=n.id or str(uuid.uuid4()),
                workflow_id=workflow_id,
                agent_id=n.agent_id,
                node_type=n.node_type,
                label=n.label,
                position_x=n.position.get("x", 0),
                position_y=n.position.get("y", 0),
                config=n.config,
            )
            db.add(node)

        if payload.edges:
            for e in payload.edges:
                edge = WorkflowEdge(
                    id=e.id or str(uuid.uuid4()),
                    workflow_id=workflow_id,
                    source_node_id=e.source,
                    target_node_id=e.target,
                    condition=e.condition,
                    label=e.label,
                )
                db.add(edge)

    db.add(workflow)
    await db.commit()

    result = await db.execute(
        select(Workflow)
        .options(selectinload(Workflow.nodes), selectinload(Workflow.edges))
        .where(Workflow.id == workflow_id)
    )
    return result.unique().scalar_one().to_dict()


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    w = result.scalar_one_or_none()
    if not w:
        raise HTTPException(404, "Workflow not found")
    await db.delete(w)
    await db.commit()


# ─────────────────────────────────────────────
#  Workflow Execution
# ─────────────────────────────────────────────

@router.post("/{workflow_id}/run")
async def run_workflow(
    workflow_id: str,
    payload: WorkflowRunRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Workflow not found")

    run = await trigger_workflow(workflow_id, payload.input, payload.trigger)
    return run.to_dict()


@router.get("/{workflow_id}/runs")
async def get_workflow_runs(
    workflow_id: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkflowRun)
        .where(WorkflowRun.workflow_id == workflow_id)
        .order_by(desc(WorkflowRun.started_at))
        .limit(limit)
    )
    return [r.to_dict() for r in result.scalars().all()]


@router.get("/runs/{run_id}")
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    return run.to_dict()


@router.get("/runs/{run_id}/logs")
async def get_run_logs(run_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RunLog)
        .where(RunLog.run_id == run_id)
        .order_by(RunLog.timestamp)
    )
    return [l.to_dict() for l in result.scalars().all()]
