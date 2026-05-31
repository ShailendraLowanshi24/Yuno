# 🤖 Yuno AI — Agent Orchestration Platform

A production-grade platform to **create AI agents**, configure their behavior, connect them into **multi-agent workflows**, and reach them via **Telegram / Slack** — all from a visual web UI.

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         React + Vite Frontend                           │
│   Dashboard │ Agents CRUD │ Visual Workflow Builder │ Live Monitor      │
│             │             │   (React Flow)          │ (WebSocket logs)  │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │  REST + WebSocket (/api/*)
┌──────────────────────────────▼──────────────────────────────────────────┐
│                        FastAPI Backend                                  │
│                                                                         │
│   /api/agents/*          /api/workflows/*          /api/monitor/*       │
│   Agent CRUD             Workflow CRUD             Real-time logs       │
│   Chat (REST+WS)         Template engine           Stats + metrics      │
│   Channel config         Run execution             Message history      │
│                                                                         │
│  ┌──────────────────┐  ┌─────────────────────┐  ┌────────────────────┐ │
│  │  Agent Runtime   │  │  Workflow Engine     │  │  Channel Manager   │ │
│  │  (LangGraph)     │  │  (Multi-agent DAG)   │  │  Telegram / Slack  │ │
│  │                  │  │                      │  │                    │ │
│  │ StateGraph +     │  │ Node traversal +     │  │ python-telegram-   │ │
│  │ Tool calling +   │  │ Conditional edges +  │  │ bot (polling)      │ │
│  │ Memory window    │  │ Feedback loops       │  │ slack-sdk Socket   │ │
│  └──────────────────┘  └─────────────────────┘  └────────────────────┘ │
│                                                                         │
│  ┌──────────────────┐  ┌─────────────────────┐                         │
│  │   APScheduler    │  │   SQLAlchemy Async   │                         │
│  │   Cron triggers  │  │   SQLite (dev)       │                         │
│  └──────────────────┘  └─────────────────────┘                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 🧠 Why LangGraph?

| Criterion | LangGraph | CrewAI | AutoGen |
|-----------|-----------|--------|---------|
| Graph model matches UI | ✅ 1:1 | ❌ Role-based | ❌ |
| Async-native | ✅ | ⚠️ | ❌ |
| Conditional edges / loops | ✅ Built-in | ❌ | ❌ |
| Full execution control | ✅ | ❌ black-box | ⚠️ |
| Custom tool binding | ✅ Standard | ✅ | ✅ |

LangGraph's `StateGraph` maps directly to our visual workflow builder — every node is an agent invocation, every edge is a message passing step. Conditional edges (e.g. `critic → creator` if `score < 8`) are expressed as Python expressions on the edge, which LangGraph evaluates natively.

---

## 🗂️ Project Structure

```
yuno-agent-platform/
├── .env.example              # Environment variable template
├── .env                      # Your config (git-ignored)
├── setup.sh                  # One-command setup (Linux/macOS)
├── start.sh                  # Start both services
├── setup_windows.bat         # Windows setup
├── start_windows.bat         # Windows start
├── pytest.ini                # Test configuration
│
├── backend/
│   ├── main.py               # FastAPI app + lifespan
│   ├── requirements.txt      # Python dependencies
│   │
│   ├── db/
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   └── session.py        # Async session + init_db
│   │
│   ├── agents/
│   │   ├── runtime.py        # LangGraph ReAct agent engine
│   │   ├── tools.py          # Built-in tool registry
│   │   └── scheduler.py      # APScheduler cron jobs
│   │
│   ├── workflows/
│   │   └── engine.py         # Multi-agent DAG executor + templates
│   │
│   ├── channels/
│   │   ├── __init__.py       # Channel manager
│   │   ├── telegram.py       # Telegram bot (python-telegram-bot)
│   │   └── slack.py          # Slack Socket Mode bot
│   │
│   ├── api/
│   │   ├── agents.py         # Agent CRUD + chat + channel endpoints
│   │   ├── workflows.py      # Workflow CRUD + run endpoints
│   │   └── monitor.py        # Stats + logs + WebSocket stream
│   │
│   └── tests/
│       └── test_main.py      # Pytest async tests
│
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    └── src/
        ├── App.jsx            # Router
        ├── main.jsx           # Entry point
        ├── index.css          # Tailwind + custom styles
        ├── api.js             # Axios API client
        ├── store/index.js     # Zustand global state
        ├── hooks/
        │   └── useLiveLogs.js # WebSocket live log hook
        ├── components/
        │   ├── Sidebar.jsx
        │   ├── ui.jsx         # Shared UI components
        │   ├── AgentForm.jsx  # Create/edit agent modal
        │   ├── ChatPanel.jsx  # Real-time chat interface
        │   └── WorkflowBuilder.jsx  # React Flow graph editor
        └── pages/
            ├── Dashboard.jsx
            ├── Agents.jsx
            ├── AgentDetail.jsx
            ├── Workflows.jsx
            ├── WorkflowDetail.jsx
            └── Monitor.jsx
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- An OpenAI API key (or Anthropic)

### 1. Clone & Setup
```bash
git clone <repo-url>
cd yuno-agent-platform

# Linux/macOS:
bash setup.sh

# Windows:
setup_windows.bat
```

### 2. Configure API Keys
```bash
# Edit .env:
OPENAI_API_KEY=sk-...          # Required for OpenAI models
ANTHROPIC_API_KEY=sk-ant-...   # Required for Claude models
```

### 3. Start
```bash
# Linux/macOS:
bash start.sh

# Windows:
start_windows.bat
```

- **Frontend:** http://localhost:5173
- **Backend:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

---

## ✅ Feature Checklist

### Agent Configuration
- [x] Name, role, system prompt, model, provider (OpenAI/Anthropic)
- [x] Tool selection (web_search, http_get, http_post, calculate, etc.)
- [x] Memory (enable/disable, sliding window size)
- [x] Temperature, max tokens, max iterations
- [x] Cron schedule + scheduled prompt
- [x] Guardrails (max response length, content blocking)
- [x] Channels (Telegram, Slack)

### Workflows
- [x] Visual graph builder with React Flow (drag/drop nodes + connect edges)
- [x] Node types: agent, input, output, condition
- [x] Conditional edges (Python expression evaluation)
- [x] Feedback loops (critic → creator revision cycle)
- [x] 2 pre-built templates (Research Pipeline, Content Creation & Review)
- [x] Async background execution
- [x] Run history with output and logs

### Messaging Channels
- [x] Telegram bot (polling mode, no public URL needed)
- [x] Slack bot (Socket Mode, no public URL needed)
- [x] Channel configs persisted and auto-restored on restart

### Monitoring
- [x] Real-time log streaming via WebSocket
- [x] Token usage and cost tracking per run
- [x] Inter-agent message history
- [x] Platform-wide stats (agents, runs, tokens, cost)

### Code Quality
- [x] Clear layer separation: UI → API → Runtime → DB
- [x] Async throughout (FastAPI + SQLAlchemy async + async channel bots)
- [x] Tests for agent CRUD, workflow execution, message delivery
- [x] Pydantic v2 request validation on all endpoints

---

## 🔌 Messaging Channel Setup

### Telegram
1. Message `@BotFather` on Telegram
2. Run `/newbot` and follow prompts
3. Copy the bot token
4. In the UI: Agents → [Agent] → Channels → Telegram → paste token → Connect
5. Start chatting with your bot on Telegram!

### Slack (Socket Mode — no webhook URL needed)
1. Go to [api.slack.com/apps](https://api.slack.com/apps) → Create New App → From Scratch
2. **Socket Mode** tab → Enable Socket Mode → Generate App-Level Token (scope: `connections:write`) → save as `App Token (xapp-...)`
3. **OAuth & Permissions** → Bot Token Scopes: `chat:write`, `im:history`, `im:read`, `channels:history`, `channels:read`
4. **Install to Workspace** → copy Bot Token (`xoxb-...`)
5. **Event Subscriptions** → Enable → Subscribe to Bot Events: `message.im`, `message.channels`
6. In the UI: Agents → [Agent] → Channels → Slack → paste both tokens → Connect

---

## 📋 Pre-built Workflow Templates

### 1. Research & Summary Pipeline
```
[User Query] → [Researcher Agent] → [Writer Agent] → [Final Report]
```
- **Researcher** uses `web_search` + `http_get` to gather information
- **Writer** receives research notes and produces a polished report
- Linear chain, no conditions

### 2. Content Creation & Review Loop
```
[Brief] → [Creator] → [Critic] → (score < 8?) → [Creator] (revision)
                                ↓ (score >= 8 OR 3 iterations)
                           [Approved Content]
```
- **Creator** drafts content based on the brief
- **Critic** scores it 1–10 and gives structured feedback (JSON)
- Loops back to Creator with feedback if score < 8 (max 3 iterations)
- Demonstrates conditional edges + feedback loops

### Adding a New Template
In `backend/workflows/engine.py`, add an entry to `WORKFLOW_TEMPLATES`:
```python
WORKFLOW_TEMPLATES["my_template"] = {
    "name": "My Custom Pipeline",
    "description": "...",
    "nodes": [...],
    "edges": [...],
}
```

---

## 🧪 Running Tests

```bash
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pytest -v
```

Tests cover:
- Agent CRUD (create, read, update, delete, 404 handling)
- Tool registry listing
- Workflow creation with nodes/edges
- Template listing and instantiation
- Workflow run creation
- Monitor stats and log endpoints
- Message history for new sessions
- Health endpoint

---

## ⚙️ Adding a New Messaging Channel

1. Create `backend/channels/myservice.py`:
```python
async def start_myservice_bot(agent_id: str, config: dict): ...
async def stop_myservice_bot(agent_id: str): ...
async def restart_all_myservice_bots(): ...
```

2. Register in `backend/channels/__init__.py`:
```python
elif channel_type == "myservice":
    from .myservice import start_myservice_bot
    await start_myservice_bot(agent_id, config)
```

3. Add `ChannelType.MYSERVICE = "myservice"` in `backend/db/models.py`

4. Add the channel option to `AgentDetail.jsx` channel config modal

---

## 🔧 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | One of these | OpenAI API key |
| `ANTHROPIC_API_KEY` | One of these | Anthropic API key |
| `DATABASE_URL` | No | Default: SQLite `./yuno.db` |
| `TELEGRAM_BOT_TOKEN` | No | Global default Telegram token |
| `SLACK_BOT_TOKEN` | No | Global default Slack bot token |
| `SLACK_APP_TOKEN` | No | Global default Slack app token |
| `DEBUG` | No | Enable SQL query logging |
| `CORS_ORIGINS` | No | Allowed frontend origins |

---

## 📊 Impact Metrics (from brief)

| Metric | Achievement |
|--------|-------------|
| Configurable dimensions per agent | 12+ (prompt, model, tools, memory, guardrails, schedule, temperature, iterations, ...) |
| Time to working multi-agent workflow | < 2 minutes using templates |
| End-to-end task completion | Tracked per run with status + output |
| Agent-to-agent message reliability | Fully persisted in DB, visible in Monitor |

---

## 🏗️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Agent Runtime | LangGraph 0.1 | Native graph model, async, tool calling, cycles |
| API | FastAPI 0.111 | Async, auto-docs, WebSocket support |
| DB ORM | SQLAlchemy 2.0 async | Modern async API, works with SQLite/Postgres |
| DB | SQLite (dev) | Zero-config local setup |
| Scheduler | APScheduler | Mature, works with asyncio |
| Telegram | python-telegram-bot 21 | Async, no webhook needed |
| Slack | slack-sdk Socket Mode | No webhook needed, works locally |
| Frontend | React 18 + Vite | Fast HMR, modern |
| Graph UI | @xyflow/react | Best-in-class flow editor |
| State | Zustand | Minimal, no boilerplate |
| Styling | Tailwind CSS | Utility-first, dark theme |
