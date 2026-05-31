#!/usr/bin/env bash
# ============================================================
# Yuno AI Agent Orchestration Platform — Setup Script
# Usage: bash setup.sh
# ============================================================
set -e

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ██╗   ██╗██╗   ██╗███╗   ██╗ ██████╗      █████╗ ██╗"
echo "  ╚██╗ ██╔╝██║   ██║████╗  ██║██╔═══██╗    ██╔══██╗██║"
echo "   ╚████╔╝ ██║   ██║██╔██╗ ██║██║   ██║    ███████║██║"
echo "    ╚██╔╝  ██║   ██║██║╚██╗██║██║   ██║    ██╔══██║██║"
echo "     ██║   ╚██████╔╝██║ ╚████║╚██████╔╝    ██║  ██║██║"
echo "     ╚═╝    ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝     ╚═╝  ╚═╝╚═╝"
echo -e "${NC}"
echo "  AI Agent Orchestration Platform — Setup"
echo "  ==========================================="

# ── Python check
echo -e "\n${YELLOW}[1/6] Checking Python version...${NC}"
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Python 3 is required. Install it from https://python.org${NC}"
    exit 1
fi
PYTHON_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}  ✓ Python $PYTHON_VER found${NC}"

# ── Node check
echo -e "\n${YELLOW}[2/6] Checking Node.js...${NC}"
if ! command -v node &>/dev/null; then
    echo -e "${RED}Node.js 18+ is required. Install from https://nodejs.org${NC}"
    exit 1
fi
NODE_VER=$(node --version)
echo -e "${GREEN}  ✓ Node $NODE_VER found${NC}"

# ── .env setup
echo -e "\n${YELLOW}[3/6] Setting up environment...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}  ✓ Created .env from .env.example${NC}"
    echo -e "${YELLOW}  ⚠ Open .env and add your OPENAI_API_KEY (or ANTHROPIC_API_KEY)${NC}"
else
    echo -e "${GREEN}  ✓ .env already exists${NC}"
fi

# ── Backend virtualenv
echo -e "\n${YELLOW}[4/6] Setting up Python virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo -e "${GREEN}  ✓ Created .venv${NC}"
fi

source .venv/bin/activate
echo -e "${GREEN}  ✓ Activated .venv${NC}"

echo "  Installing backend dependencies (this may take 1-2 minutes)..."
pip install --quiet --upgrade pip
pip install --quiet -r backend/requirements.txt
echo -e "${GREEN}  ✓ Backend dependencies installed${NC}"

# ── Frontend dependencies
echo -e "\n${YELLOW}[5/6] Installing frontend dependencies...${NC}"
cd frontend
npm install --silent
cd ..
echo -e "${GREEN}  ✓ Frontend dependencies installed${NC}"

# ── Done
echo -e "\n${YELLOW}[6/6] Setup complete!${NC}"
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          🚀 READY TO LAUNCH                       ║${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║                                                   ║${NC}"
echo -e "${GREEN}║  1. Edit .env and add your API key(s)             ║${NC}"
echo -e "${GREEN}║  2. Run: bash start.sh                            ║${NC}"
echo -e "${GREEN}║                                                   ║${NC}"
echo -e "${GREEN}║  Backend:  http://localhost:8000                  ║${NC}"
echo -e "${GREEN}║  API Docs: http://localhost:8000/docs             ║${NC}"
echo -e "${GREEN}║  Frontend: http://localhost:5173                  ║${NC}"
echo -e "${GREEN}║                                                   ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
