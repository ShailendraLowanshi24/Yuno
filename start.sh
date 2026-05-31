#!/usr/bin/env bash
# ============================================================
# Yuno AI — Start backend + frontend concurrently
# ============================================================
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Activate venv if present
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Load .env
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo -e "${GREEN}Starting Yuno AI Agent Orchestration Platform...${NC}"
echo ""

cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup SIGINT SIGTERM

# Start backend
echo -e "${GREEN}[Backend]  Starting on http://localhost:8000${NC}"
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Wait for backend to be ready
echo "  Waiting for backend..."
for i in {1..20}; do
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Backend ready${NC}"
        break
    fi
    sleep 1
done

# Start frontend
echo -e "${GREEN}[Frontend] Starting on http://localhost:5173${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Yuno AI is running!                              ║${NC}"
echo -e "${GREEN}║  Frontend:  http://localhost:5173                 ║${NC}"
echo -e "${GREEN}║  Backend:   http://localhost:8000                 ║${NC}"
echo -e "${GREEN}║  API Docs:  http://localhost:8000/docs            ║${NC}"
echo -e "${GREEN}║                                                   ║${NC}"
echo -e "${GREEN}║  Press Ctrl+C to stop                             ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

wait $BACKEND_PID $FRONTEND_PID
