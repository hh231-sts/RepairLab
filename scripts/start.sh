#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export MODEL_CALLS_ENABLED=false EMBEDDING_ENABLED=false LANGSMITH_TRACING=false
case "${1:-}" in
  --enable-model-calls) export MODEL_CALLS_ENABLED=true ;;
  "") ;;
  *) echo 'Usage: bash scripts/start.sh [--enable-model-calls]' >&2; exit 2 ;;
esac
export UV_CACHE_DIR="$PWD/.cache/uv"
test -f .env || cp .env.example .env
mkdir -p data
uv sync --frozen --extra dev
uv run repairlab check-config
docker compose up -d --wait db
docker build -f docker/sandbox.Dockerfile -t repairlab-sandbox:local .
uv run python -c 'from repairlab.config import Settings; Settings().prepare()'
uv run alembic upgrade head
(cd frontend && npm ci && npm run build)
uv run uvicorn repairlab.api:create_app --factory --host 127.0.0.1 --port 8000 &
api_pid=$!
uv run repairlab worker &
worker_pid=$!
(cd frontend && npm run dev -- --host 127.0.0.1 --port 5173) &
ui_pid=$!
trap 'kill "$api_pid" "$worker_pid" "$ui_pid" 2>/dev/null || true' EXIT INT TERM
echo "RepairLab: http://localhost:5173 — model calls=$MODEL_CALLS_ENABLED; embedding OFF"
wait
