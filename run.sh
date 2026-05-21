#!/bin/bash
# CU Quiz App — portable startup
# Set these env vars to override defaults:
#   CATSOOP_ENV, CU_QUIZ_HOST, CU_QUIZ_PORT

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
CATSOOP_ENV="${CATSOOP_ENV:-/home/alex/catsoop-env}"
HOST="${CU_QUIZ_HOST:-0.0.0.0}"
PORT="${CU_QUIZ_PORT:-8000}"

# Activate venv — supports both relative and absolute CATSOOP_ENV
if [[ "$CATSOOP_ENV" = /* ]]; then
    source "$CATSOOP_ENV/bin/activate"
else
    source "$APP_DIR/$CATSOOP_ENV/bin/activate"
fi
cd "$APP_DIR"

echo "Starting FastAPI on $HOST:$PORT..."
uvicorn api.main:app --host "$HOST" --port "$PORT" --reload &
FASTAPI_PID=$!

# Wait for FastAPI to be ready
sleep 3

# Start Catsoop (local engine)
echo "Starting Catsoop (catsoop_engine)..."
PYTHONPATH="$(pwd)" python3 -m catsoop_engine start

# Cleanup
kill $FASTAPI_PID 2>/dev/null || true
