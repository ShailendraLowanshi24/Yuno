"""
Agent Runtime — powered by LangGraph.

Why LangGraph?
- Provides a stateful, graph-based agent execution model
- Native support for tool calling, conditional edges, and feedback loops
- Async-first design matches our FastAPI stack
- Checkpointing maps cleanly to our message-history persistence
- Easy to extend with custom node types (exactly what we need for
  multi-agent orchestration with conditions and cycles)
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, AsyncIterator, Optional, Sequence, TypedDict, Annotated

from langchain_core.messages import (
    AIMessage, HumanMessage, SystemMessage, ToolMessage, BaseMessage
)
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import Agent, Message, MessageRole, ChannelType, RunLog
from .tools import get_tools_for_agent

logger = logging.getLogger(__name__)

# Token cost table (USD per 1K tokens) — approximate
COST_TABLE = {
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "claude-3-5-sonnet-20241022": {"input": 0.003, "output": 0.015},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = COST_TABLE.get(model, {"input": 0.001, "output": 0.002})
    return (prompt_tokens / 1000 * rates["input"]) + (completion_tokens / 1000 * rates["output"])


# ─────────────────────────────────────────────
#  LangGraph State
# ─────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    agent_config: dict
    iteration: int
    run_id: Optional[str]
    output: Optional[str]


# ─────────────────────────────────────────────
#  LLM Factory
# ─────────────────────────────────────────────

def build_llm(agent: Agent, tools: list = None):
    """Instantiate the correct LLM based on agent configuration."""
    kwargs = {
        "model": agent.model,
        "temperature": agent.temperature,
        "max_tokens": agent.max_tokens,
    }
    if agent.provider == "anthropic":
        llm = ChatAnthropic(**kwargs)
    else:
        llm = ChatOpenAI(**kwargs)

    if tools:
        llm = llm.bind_tools(tools)
    return llm


# ─────────────────────────────────────────────
#  Agent Graph Builder
# ─────────────────────────────────────────────

def build_agent_graph(agent_config: dict, tools: list):
    """
    Build a LangGraph ReAct-style agent graph.

    Graph structure:
        [START] → agent_node → (has_tool_calls?) → tool_node → agent_node
                                       ↓ (no tool calls or max iterations)
                                     [END]
    """
    llm = _make_llm_from_config(agent_config, tools)

    def agent_node(state: AgentState) -> AgentState:
        """Call the LLM with current message history."""
        messages = state["messages"]

        # Enforce iteration limit
        iteration = state.get("iteration", 0)
        max_iter = agent_config.get("max_iterations", 10)
        if iteration >= max_iter:
            return {**state, "output": "Max iterations reached."}

        # Prepend system prompt if not already present
        if not messages or not isinstance(messages[0], SystemMessage):
            system = SystemMessage(content=agent_config.get("system_prompt", "You are a helpful assistant."))
            messages = [system] + list(messages)

        # Apply guardrails
        guardrails = agent_config.get("guardrails", {})
        if guardrails.get("max_response_length"):
            # Inject instruction into system prompt
            messages[0] = SystemMessage(
                content=messages[0].content + f"\n\nIMPORTANT: Keep your response under {guardrails['max_response_length']} words."
            )

        response = llm.invoke(messages)
        return {
            **state,
            "messages": [response],
            "iteration": iteration + 1,
            "output": response.content if not response.tool_calls else None,
        }

    def tool_node(state: AgentState) -> AgentState:
        """Execute any tool calls from the last AI message."""
        last_msg = state["messages"][-1]
        tool_map = {t.name: t for t in tools}
        tool_results = []

        for tc in last_msg.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_call_id = tc["id"]

            if tool_name in tool_map:
                try:
                    result = tool_map[tool_name].invoke(tool_args)
                    result_str = str(result)
                except Exception as e:
                    result_str = f"Tool error: {e}"
            else:
                result_str = f"Unknown tool: {tool_name}"

            tool_results.append(
                ToolMessage(content=result_str, tool_call_id=tool_call_id)
            )

        return {**state, "messages": tool_results}

    def should_continue(state: AgentState) -> str:
        """Decide whether to call tools or end."""
        last_msg = state["messages"][-1]
        iteration = state.get("iteration", 0)
        max_iter = state["agent_config"].get("max_iterations", 10)

        if iteration >= max_iter:
            return "end"
        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            return "tools"
        return "end"

    # Build graph
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    if tools:
        graph.add_node("tools", tool_node)
        graph.add_conditional_edges("agent", should_continue, {"tools": "tools", "end": END})
        graph.add_edge("tools", "agent")
    else:
        graph.add_edge("agent", END)

    graph.set_entry_point("agent")
    return graph.compile()


def _make_llm_from_config(config: dict, tools: list):
    kwargs = {
        "model": config.get("model", "gpt-4o-mini"),
        "temperature": config.get("temperature", 0.7),
        "max_tokens": config.get("max_tokens", 2048),
    }
    if config.get("provider") == "anthropic":
        llm = ChatAnthropic(**kwargs)
    else:
        llm = ChatOpenAI(**kwargs)
    if tools:
        llm = llm.bind_tools(tools)
    return llm


# ─────────────────────────────────────────────
#  AgentRunner
# ─────────────────────────────────────────────

class AgentRunner:
    """
    High-level interface for running an agent.
    Handles message persistence, token counting, and real-time event streaming.
    """

    def __init__(self, agent: Agent, db: AsyncSession, run_id: Optional[str] = None):
        self.agent = agent
        self.db = db
        self.run_id = run_id
        self.tools = get_tools_for_agent(agent.tools or [])
        self.graph = build_agent_graph(agent.to_dict(), self.tools)

    async def run(
        self,
        user_input: str,
        session_id: str,
        channel: ChannelType = ChannelType.UI,
        channel_user_id: Optional[str] = None,
        history: Optional[list[BaseMessage]] = None,
        stream_callback=None,
    ) -> str:
        """
        Execute the agent for a single user input.
        Returns the final text response.
        """
        # Persist user message
        user_msg = Message(
            agent_id=self.agent.id,
            session_id=session_id,
            role=MessageRole.USER,
            content=user_input,
            channel=channel,
            channel_user_id=channel_user_id,
        )
        self.db.add(user_msg)
        await self.db.flush()

        # Build message list
        lc_messages: list[BaseMessage] = list(history or [])
        lc_messages.append(HumanMessage(content=user_input))

        # Apply memory window
        if self.agent.memory_enabled and self.agent.memory_window:
            lc_messages = lc_messages[-self.agent.memory_window:]

        initial_state: AgentState = {
            "messages": lc_messages,
            "agent_config": self.agent.to_dict(),
            "iteration": 0,
            "run_id": self.run_id,
            "output": None,
        }

        # Run graph
        try:
            final_state = await asyncio.get_event_loop().run_in_executor(
                None, self.graph.invoke, initial_state
            )
            output = final_state.get("output") or ""
            if not output:
                # Fallback: get content of last AI message
                for msg in reversed(final_state["messages"]):
                    if isinstance(msg, AIMessage) and msg.content:
                        output = msg.content
                        break

        except Exception as e:
            logger.exception("Agent run failed")
            output = f"I encountered an error: {e}"
            await self._log(event="agent_error", message=str(e), level="error")

        # Persist assistant message
        asst_msg = Message(
            agent_id=self.agent.id,
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=output,
            channel=channel,
            channel_user_id=channel_user_id,
        )
        self.db.add(asst_msg)

        # Log
        await self._log(
            event="agent_response",
            message=f"Agent '{self.agent.name}' responded",
            metadata={"session_id": session_id, "response_length": len(output)},
        )

        if stream_callback:
            await stream_callback(output)

        await self.db.commit()
        return output

    async def _log(
        self,
        event: str,
        message: str,
        level: str = "info",
        metadata: dict = None,
        tokens: int = 0,
        cost: float = 0.0,
    ):
        log = RunLog(
            run_id=self.run_id,
            agent_id=self.agent.id,
            level=level,
            event=event,
            message=message,
            metadata=metadata or {},
            tokens_used=tokens,
            cost=cost,
        )
        self.db.add(log)
        await self.db.flush()
