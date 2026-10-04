#!/usr/bin/env bash
# Start the full app with the real local models: API on :8100, web UI on :3000.
#   make demo        (Ctrl+C stops both)
# Needs: Docker database running (make db-up) and Ollama with qwen3:8b.
# Port 8100 is used because 8000 is often taken by another project on this machine.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${API_PORT:-8100}"

if ! curl -s -m 2 localhost:11434/api/tags >/dev/null; then
  echo "Ollama is not running: open the Ollama app first (it serves qwen3:8b)." >&2
  exit 1
fi
if lsof -iTCP:"$API_PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port $API_PORT is in use (an API already running?). Stop it or set API_PORT." >&2
  exit 1
fi

export LLM_PROVIDER=openai_compatible LLM_BASE_URL=http://localhost:11434/v1 LLM_API_KEY=ollama \
  LLM_MODEL=qwen3:8b LLM_REASONING_EFFORT=none EMBEDDING_PROVIDER=local VERIFIER_METHOD=auto \
  HF_HUB_OFFLINE=1

(cd "$ROOT/backend" && .venv/bin/uvicorn app.main:app --port "$API_PORT") &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT INT TERM

for _ in $(seq 1 60); do
  curl -s -m 2 "localhost:$API_PORT/health/ready" >/dev/null && break
  sleep 2
done
echo "API ready on http://localhost:$API_PORT — starting the web UI on http://localhost:3000"
cd "$ROOT/frontend" && BACKEND_URL="http://localhost:$API_PORT" npm run dev
