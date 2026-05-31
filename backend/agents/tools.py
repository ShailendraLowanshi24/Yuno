"""
Tool registry — all built-in tools agents can use.
Each tool is a LangChain-compatible structured tool.
"""

from __future__ import annotations
import httpx
import json
from datetime import datetime
from typing import Optional
from langchain.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun


# ─────────────────────────────────────────────
#  Web / Search
# ─────────────────────────────────────────────

@tool
def web_search(query: str) -> str:
    """Search the web for current information using DuckDuckGo."""
    try:
        search = DuckDuckGoSearchRun()
        return search.run(query)
    except Exception as e:
        return f"Search failed: {e}"


@tool
def http_get(url: str, headers_json: Optional[str] = None) -> str:
    """Make an HTTP GET request and return the response body (truncated at 2000 chars)."""
    try:
        headers = json.loads(headers_json) if headers_json else {}
        with httpx.Client(timeout=15) as client:
            resp = client.get(url, headers=headers)
            return resp.text[:2000]
    except Exception as e:
        return f"HTTP GET failed: {e}"


@tool
def http_post(url: str, body_json: str, headers_json: Optional[str] = None) -> str:
    """Make an HTTP POST request with a JSON body and return the response."""
    try:
        headers = json.loads(headers_json) if headers_json else {}
        body = json.loads(body_json)
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, json=body, headers=headers)
            return resp.text[:2000]
    except Exception as e:
        return f"HTTP POST failed: {e}"


# ─────────────────────────────────────────────
#  Utility
# ─────────────────────────────────────────────

@tool
def get_current_datetime(timezone: Optional[str] = "UTC") -> str:
    """Return the current date and time in ISO-8601 format."""
    return datetime.utcnow().isoformat() + "Z"


@tool
def calculate(expression: str) -> str:
    """Safely evaluate a mathematical expression and return the result."""
    try:
        # Restrict to safe builtins
        allowed = {
            "__builtins__": {},
            "abs": abs, "round": round, "min": min, "max": max,
            "sum": sum, "pow": pow, "int": int, "float": float,
        }
        result = eval(expression, allowed)  # noqa: S307
        return str(result)
    except Exception as e:
        return f"Calculation error: {e}"


@tool
def json_parse(json_string: str) -> str:
    """Parse a JSON string and return a pretty-printed version."""
    try:
        data = json.loads(json_string)
        return json.dumps(data, indent=2)
    except Exception as e:
        return f"JSON parse error: {e}"


@tool
def summarize_text(text: str, max_words: int = 100) -> str:
    """Summarize text by returning the first N words as a basic summary placeholder."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "..."


# ─────────────────────────────────────────────
#  Registry
# ─────────────────────────────────────────────

TOOL_REGISTRY: dict[str, object] = {
    "web_search": web_search,
    "http_get": http_get,
    "http_post": http_post,
    "get_current_datetime": get_current_datetime,
    "calculate": calculate,
    "json_parse": json_parse,
    "summarize_text": summarize_text,
}

TOOL_DESCRIPTIONS = {
    name: (tool_fn.description or "")
    for name, tool_fn in TOOL_REGISTRY.items()
}


def get_tools_for_agent(tool_names: list[str]) -> list:
    """Return LangChain tool objects for the given tool names."""
    return [TOOL_REGISTRY[name] for name in tool_names if name in TOOL_REGISTRY]


def get_all_tool_names() -> list[str]:
    return list(TOOL_REGISTRY.keys())
