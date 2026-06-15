#!/bin/bash
# CU Quiz App — portable startup
# Set these env vars to override defaults:
#   CATSOOP_ENV, CU_QUIZ_HOST, CU_QUIZ_PORT
# Required for auth:
#   CU_QUIZ_SECRET     — HMAC signing secret for JWTs (required in non-dev mode)
#   CU_QUIZ_ADMINS     — comma-separated admin usernames (default: admin)
#   CU_QUIZ_ADMIN_PASSWORD — password for POST /admin/login (required)

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
CATSOOP_ENV="${CATSOOP_ENV:-/home/alex/catsoop-env}"
HOST="${CU_QUIZ_HOST:-0.0.0.0}"
PORT="${CU_QUIZ_PORT:-8000}"

# Load tunnel/production URL overrides (sets CS_URL_ROOT, CU_QUIZ_BASE_URL, etc.)
if [[ -f "$APP_DIR/.env.tunnel" ]]; then
  source "$APP_DIR/.env.tunnel"
  echo "Loaded tunnel config: CU_QUIZ_BASE_URL=$CU_QUIZ_BASE_URL"
fi

# Fail fast if CU_QUIZ_SECRET is not set (required for JWT signing)
if [[ -z "$CU_QUIZ_SECRET" ]]; then
  echo "ERROR: CU_QUIZ_SECRET is not set. Generate one with: openssl rand -hex 32" >&2
  exit 1
fi

export CU_QUIZ_ADMINS="${CU_QUIZ_ADMINS:-admin}"

# Auto-derive browser-facing API URL if not already set
if [[ -z "$CU_QUIZ_BASE_URL" ]]; then
  if [[ "$HOST" == "0.0.0.0" ]]; then
    export CU_QUIZ_BASE_URL="http://localhost:${PORT}"
  else
    export CU_QUIZ_BASE_URL="http://${HOST}:${PORT}"
  fi
fi

# Activate venv — supports both relative and absolute CATSOOP_ENV
if [[ "$CATSOOP_ENV" = /* ]]; then
    source "$CATSOOP_ENV/bin/activate"
else
    source "$APP_DIR/$CATSOOP_ENV/bin/activate"
fi
cd "$APP_DIR"

# Use locally cached HuggingFace models — avoids slow remote checks on WSL2
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

# Start Ollama if not already running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
  echo "Starting Ollama..."
  ollama serve > /tmp/ollama.log 2>&1 &
  sleep 2
fi

echo "Starting FastAPI on $HOST:$PORT..."
uvicorn api.main:app --host "$HOST" --port "$PORT" --reload --proxy-headers --forwarded-allow-ips='*' &
FASTAPI_PID=$!

# Wait for FastAPI to be ready
sleep 3

# Start Catsoop (local engine)
echo "Starting Catsoop (catsoop_engine)..."
PYTHONPATH="$(pwd)" python3 -m catsoop_engine start

# Cleanup
kill $FASTAPI_PID 2>/dev/null || true
