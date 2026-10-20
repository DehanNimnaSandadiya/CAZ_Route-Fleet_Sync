#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3.12 not found. Please install it first with: brew install python@3.12"
  exit 1
fi

if [ ! -d "$BACKEND_DIR/.venv" ]; then
  echo "Creating backend virtual environment..."
  cd "$BACKEND_DIR"
  "$PYTHON_BIN" -m venv .venv
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "Installing frontend dependencies..."
  cd "$FRONTEND_DIR"
  npm install
fi

cd "$BACKEND_DIR"
source .venv/bin/activate
if [ ! -f .venv/bin/uvicorn ]; then
  echo "Installing backend dependencies..."
  pip install -r requirements.txt
else
  echo "Backend dependencies already installed."
fi

if ! python - <<'PY'
import importlib.util
mods = ['fastapi', 'uvicorn', 'httpx', 'pytest']
missing = [m for m in mods if importlib.util.find_spec(m) is None]
if missing:
    raise SystemExit(f'Missing modules: {missing}')
PY
then
  echo "Installing backend dependencies..."
  pip install -r requirements.txt
fi

BACKEND_LOG="$ROOT_DIR/.backend.log"
FRONTEND_LOG="$ROOT_DIR/.frontend.log"

for port in 8000 3000 3001 3002 3003; do
  if command -v lsof >/dev/null 2>&1; then
    pids=$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)
    if [ -n "$pids" ]; then
      echo "Clearing stale process on port $port"
      kill -9 $pids 2>/dev/null || true
    fi
  fi
done

if curl -fsS http://localhost:8000/docs >/dev/null 2>&1; then
  echo "Backend already running on http://localhost:8000/docs"
  BACKEND_PID=""
else
  cd "$BACKEND_DIR"
  source .venv/bin/activate
  uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$BACKEND_LOG" 2>&1 &
  BACKEND_PID=$!
  echo "Backend is starting on http://localhost:8000/docs"
fi

if curl -fsS http://localhost:3000 >/dev/null 2>&1; then
  echo "Frontend already running on http://localhost:3000"
  FRONTEND_PID=""
else
  cd "$FRONTEND_DIR"
  npm run dev > "$FRONTEND_LOG" 2>&1 &
  FRONTEND_PID=$!
  echo "Frontend is starting on http://localhost:3000"
fi

cleanup() {
  if [ -n "${BACKEND_PID:-}" ]; then
    echo "Stopping backend..."
    kill "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "${FRONTEND_PID:-}" ]; then
    echo "Stopping frontend..."
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
  exit 0
}
trap cleanup EXIT INT TERM

echo "Logs:"
echo "  Backend: $BACKEND_LOG"
echo "  Frontend: $FRONTEND_LOG"

if [ -n "${BACKEND_PID:-}" ] && [ -n "${FRONTEND_PID:-}" ]; then
  echo "Press Ctrl+C to stop the services started by this script."
  wait "$BACKEND_PID" "$FRONTEND_PID"
elif [ -n "${BACKEND_PID:-}" ]; then
  echo "Press Ctrl+C to stop the backend started by this script."
  wait "$BACKEND_PID"
elif [ -n "${FRONTEND_PID:-}" ]; then
  echo "Press Ctrl+C to stop the frontend started by this script."
  wait "$FRONTEND_PID"
else
  echo "Everything is already running. Press Ctrl+C to exit this wrapper."
  tail -f /dev/null
fi
