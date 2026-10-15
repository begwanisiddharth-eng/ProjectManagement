#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
PID_FILE="$ROOT_DIR/.run/server.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "No server PID file found; server is not running."
  exit 0
fi

SERVER_PID=$(cat "$PID_FILE")
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
  rm -f "$PID_FILE"
  echo "Removed stale server PID file."
  exit 0
fi

COMMAND=$(ps -p "$SERVER_PID" -o args= 2>/dev/null || true)
case "$COMMAND" in
  *"uvicorn backend.main:app"*) ;;
  *)
    echo "PID $SERVER_PID is not the Kanban Studio server; refusing to stop it." >&2
    exit 1
    ;;
esac

kill "$SERVER_PID"
ATTEMPT=0
while kill -0 "$SERVER_PID" 2>/dev/null && [ "$ATTEMPT" -lt 30 ]; do
  ATTEMPT=$((ATTEMPT + 1))
  sleep 1
done

if kill -0 "$SERVER_PID" 2>/dev/null; then
  echo "Server process $SERVER_PID did not stop within 30 seconds." >&2
  exit 1
fi

rm -f "$PID_FILE"
echo "Server stopped."
