"""
Workflow Orchestration Engine.

Converts a persisted Workflow (nodes + edges) into a LangGraph
StateGraph where each node is an AgentRunner invocation.

Supports:
- Sequential chains
- Conditional edges (Python expression evaluated against state)
- Feedback loops (cycles in the graph)
- Pre-built templates (Research Pipeline, Content Creation)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import (
    Workflow, WorkflowNode, WorkflowEdge, WorkflowRun,
    RunLog, Agent, WorkflowStatus, RunStatus, ChannelType
)
from ..db.session import AsyncSessionLocal
from .runtime import AgentRunner

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Template Definitions
# ─────────────────────────────────────────────

WORKFLOW_TEMPLATES = {
    "research_pipeline": {
        "name": "Research & Summary Pipeline",
        "description": "A Researcher agent gathers information, then a Writer agent summarizes it into a polished report.",
        "nodes": [
            {
                "id": "input",
                "node_type": "input",
                "label": "User Query",
                "position": {"x": 100, "y": 200},
                "config": {},
            },
            {
                "id": "researcher",
                "node_type": "agent_template",
                "label": "Researcher Agent",
                "position": {"x": 350, "y": 200},
                "config": {
                    "name": "Researcher",
                    "role": "Research Specialist",
                    "system_prompt": (
                        "You are an expert research assistant. When given a topic, "
                        "search the web thoroughly and compile a comprehensive list of key facts, "
                        "statistics, and findings. Format your output as structured notes."
                    ),
                    "tools": ["web_search", "http_get"],
                    "model": "gpt-4o-mini",
                },
            },
            {
                "id": "writer",
                "node_type": "agent_template",
                "label": "Writer Agent",
                "position": {"x": 650, "y": 200},
                "config": {
                    "name": "Writer",
                    "role": "Content Writer",
                    "system_prompt": (
                        "You are a professional content writer. Given research notes, "
                        "write a clear, engaging, well-structured report suitable for "
                        "a general audience. Include an executive summary at the top."
                    ),
                    "tools": [],
                    "model": "gpt-4o-mini",
                },
            },
            {
                "id": "output",
                "node_type": "output",
                "label": "Final Report",
                "position": {"x": 900, "y": 200},
                "config": {},
            },
        ],
        "edges": [
            {"source": "input", "target": "researcher", "label": "query"},
            {"source": "researcher", "target": "writer", "label": "research notes"},
            {"source": "writer", "target": "output", "label": "report"},
        ],
    },

    "content_review_loop": {
        "name": "Content Creation & Review Loop",
        "description": "A Creator agent drafts content; a Critic agent reviews it. If quality score < 8, loops back to Creator for revision (max 3 loops).",
        "nodes": [
            {
                "id": "input",
                "node_type": "input",
                "label": "Content Brief",
                "position": {"x": 50, "y": 200},
                "config": {},
            },
            {
                "id": "creator",
                "node_type": "agent_template",
                "label": "Creator Agent",
                "position": {"x": 300, "y": 200},
                "config": {
                    "name": "Creator",
                    "role": "Content Creator",
                    "system_prompt": (
                        "You are a creative content writer. Write engaging, original content "
                        "based on the brief provided. If you are given feedback from a critic, "
                        "incorporate it to improve the content. Return ONLY the content text."
                    ),
                    "tools": [],
                    "model": "gpt-4o-mini",
                },
            },
            {
                "id": "critic",
                "node_type": "agent_template",
                "label": "Critic Agent",
                "position": {"x": 600, "y": 200},
                "config": {
                    "name": "Critic",
                    "role": "Quality Reviewer",
                    "system_prompt": (
                        "You are a strict content quality critic. Review the content provided. "
                        "Respond in JSON with exactly this format: "
                        '{"score": <1-10>, "feedback": "<what to improve>", "approved": <true/false>}. '
                        "Approve (true) only if score >= 8."
                    ),
                    "tools": [],
                    "model": "gpt-4o-mini",
                },
            },
            {
                "id": "output",
                "node_type": "output",
                "label": "Approved Content",
                "position": {"x": 900, "y": 200},
                "config": {},
            },
        ],
        "edges": [
            {"source": "input", "target": "creator", "label": "brief"},
            {"source": "creator", "target": "critic", "label": "draft"},
            {
                "source": "critic",
                "target": "creator",
                "label": "needs revision",
                "condition": 'not state.get("approved", False) and state.get("iterations", 0) < 3',
            },
            {
                "source": "critic",
                "target": "output",
                "label": "approved",
                "condition": 'state.get("approved", False) or state.get("iterations", 0) >= 3',
            },
        ],
    },
}


# ─────────────────────────────────────────────
#  Workflow Engine
# ─────────────────────────────────────────────

class WorkflowEngine:
    """
    Executes a Workflow by traversing its node/edge graph.
    Each agent node is run via AgentRunner.
    Conditions on edges are evaluated as Python expressions.
    """

    def __init__(self, workflow: Workflow, run: WorkflowRun):
        self.workflow = workflow
        self.run = run

    async def execute(self, input_text: str) -> str:
        """Execute workflow and return final output."""
        # Build node map
        nodes = {n.id: n for n in self.workflow.nodes}
        edges = self.workflow.edges

        # Find entry point (node with no incoming edges OR type=="input")
        all_targets = {e.target_node_id for e in edges}
        entry_nodes = [n for n in nodes.values() if n.id not in all_targets]
        if not entry_nodes:
            entry_nodes = [n for n in nodes.values() if n.node_type == "input"]
        if not entry_nodes:
            entry_nodes = [list(nodes.values())[0]]

        current_node_id = entry_nodes[0].id
        state = {
            "input": input_text,
            "last_output": input_text,
            "iterations": 0,
            "approved": False,
            "visited": [],
        }

        max_steps = 20  # Safety cap

        async with AsyncSessionLocal() as db:
            for step in range(max_steps):
                node = nodes.get(current_node_id)
                if not node:
                    break

                state["visited"].append(current_node_id)

                # Log step
                await self._log(db, f"Entering node: {node.label} (type={node.node_type})")

                if node.node_type in ("input",):
                    # Pass-through
                    pass
                elif node.node_type == "output":
                    # Terminal node
                    await self._complete(db, state["last_output"])
                    return state["last_output"]
                elif node.node_type in ("agent", "agent_template"):
                    # Run agent
                    output = await self._run_agent_node(db, node, state)
                    state["last_output"] = output
                    state["iterations"] += 1

                    # Try to parse critic JSON
                    try:
                        import json
                        parsed = json.loads(output)
                        if "approved" in parsed:
                            state["approved"] = parsed["approved"]
                            state["critic_feedback"] = parsed.get("feedback", "")
                            state["critic_score"] = parsed.get("score", 0)
                    except Exception:
                        pass
                elif node.node_type == "condition":
                    # Condition node — evaluate and route
                    pass

                # Find next node
                next_node_id = self._resolve_next(edges, current_node_id, state)
                if next_node_id is None:
                    # No outgoing edge — end
                    await self._complete(db, state["last_output"])
                    return state["last_output"]

                current_node_id = next_node_id

            await self._complete(db, state["last_output"])
        return state["last_output"]

    async def _run_agent_node(self, db: AsyncSession, node: WorkflowNode, state: dict) -> str:
        """Run the agent associated with a node."""
        agent = None
        if node.agent_id:
            result = await db.execute(select(Agent).where(Agent.id == node.agent_id))
            agent = result.scalar_one_or_none()

        if agent is None:
            # Build ephemeral agent from node config
            cfg = node.config or {}
            agent = Agent(
                id=f"ephemeral-{node.id}",
                name=cfg.get("name", node.label),
                role=cfg.get("role", "Assistant"),
                system_prompt=cfg.get("system_prompt", "You are a helpful assistant."),
                model=cfg.get("model", "gpt-4o-mini"),
                provider=cfg.get("provider", "openai"),
                tools=cfg.get("tools", []),
                temperature=cfg.get("temperature", 0.7),
                max_tokens=cfg.get("max_tokens", 2048),
                max_iterations=cfg.get("max_iterations", 5),
                memory_enabled=False,
            )

        # Build input with context
        user_input = state["last_output"]
        if state.get("critic_feedback"):
            user_input = (
                f"Original task: {state['input']}\n\n"
                f"Previous draft:\n{state['last_output']}\n\n"
                f"Critic feedback: {state['critic_feedback']}\n\n"
                "Please revise accordingly."
            )

        runner = AgentRunner(agent, db, run_id=self.run.id)
        session_id = f"workflow-{self.workflow.id}-{self.run.id}"
        output = await runner.run(user_input, session_id=session_id, channel=ChannelType.UI)
        return output

    def _resolve_next(self, edges: list, current_id: str, state: dict) -> Optional[str]:
        """Find the next node to execute based on outgoing edges and conditions."""
        outgoing = [e for e in edges if e.source_node_id == current_id]
        if not outgoing:
            return None

        # Evaluate conditions; pick first matching edge
        for edge in outgoing:
            if edge.condition:
                try:
                    result = eval(edge.condition, {"state": state, "__builtins__": {}})  # noqa
                    if result:
                        return edge.target_node_id
                except Exception as ex:
                    logger.warning(f"Edge condition eval failed: {ex}")
            else:
                return edge.target_node_id

        return None

    async def _log(self, db: AsyncSession, message: str, level: str = "info"):
        log = RunLog(
            run_id=self.run.id,
            level=level,
            event="workflow_step",
            message=message,
        )
        db.add(log)
        await db.flush()

    async def _complete(self, db: AsyncSession, output: str):
        self.run.status = RunStatus.COMPLETED
        self.run.output_data = {"result": output}
        self.run.completed_at = datetime.utcnow()
        db.add(self.run)
        await db.commit()


async def trigger_workflow(workflow_id: str, input_text: str, trigger: str = "manual") -> WorkflowRun:
    """
    Public API: trigger a workflow run.
    Returns the WorkflowRun immediately (execution is async).
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Workflow)
            .where(Workflow.id == workflow_id)
            .join(Workflow.nodes, isouter=True)
        )
        workflow = result.unique().scalar_one_or_none()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        # Re-load with relationships
        from sqlalchemy.orm import selectinload
        result2 = await db.execute(
            select(Workflow)
            .options(
                selectinload(Workflow.nodes),
                selectinload(Workflow.edges),
            )
            .where(Workflow.id == workflow_id)
        )
        workflow = result2.unique().scalar_one_or_none()

        run = WorkflowRun(
            workflow_id=workflow_id,
            status=RunStatus.RUNNING,
            trigger=trigger,
            input_data={"input": input_text},
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        run_id = run.id

    # Execute in background
    asyncio.create_task(_run_workflow_task(workflow_id, run_id, input_text))
    return run


async def _run_workflow_task(workflow_id: str, run_id: str, input_text: str):
    """Background task for workflow execution."""
    from sqlalchemy.orm import selectinload

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Workflow)
            .options(
                selectinload(Workflow.nodes),
                selectinload(Workflow.edges),
            )
            .where(Workflow.id == workflow_id)
        )
        workflow = result.unique().scalar_one_or_none()

        result2 = await db.execute(select(WorkflowRun).where(WorkflowRun.id == run_id))
        run = result2.scalar_one_or_none()

        if not workflow or not run:
            return

        try:
            engine = WorkflowEngine(workflow, run)
            await engine.execute(input_text)
        except Exception as e:
            logger.exception(f"Workflow run {run_id} failed")
            run.status = RunStatus.FAILED
            run.error = str(e)
            run.completed_at = datetime.utcnow()
            db.add(run)
            await db.commit()
