#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
RUN_DIR="$ROOT_DIR/.run"
PID_FILE="$RUN_DIR/server.pid"
LOG_FILE="$RUN_DIR/server.log"
HEALTH_URL="http://127.0.0.1:8000/api/health"

if [ ! -f "$ROOT_DIR/frontend/out/index.html" ]; then
  echo "Static frontend build not found. Run 'npm run build' from frontend/ first." >&2
  exit 1
fi

find_server_pid() {
  CANDIDATE_PID=$1
  CHILD_PIDS=$(ps -axo pid=,ppid=,command= 2>/dev/null |
    awk -v parent="$CANDIDATE_PID" '$2 == parent { print $1 }')
  for CHILD_PID in $CHILD_PIDS; do
    if CHILD_SERVER_PID=$(find_server_pid "$CHILD_PID"); then
      printf '%s\n' "$CHILD_SERVER_PID"
      return 0
    fi
  done

  CANDIDATE_COMMAND=$(ps -p "$CANDIDATE_PID" -o args= 2>/dev/null || true)
  case "$CANDIDATE_COMMAND" in
    *"uvicorn backend.main:app"*)
      printf '%s\n' "$CANDIDATE_PID"
      return 0
      ;;
  esac
  return 1
}

mkdir -p "$RUN_DIR"

if [ -f "$PID_FILE" ]; then
  EXISTING_PID=$(cat "$PID_FILE")
  if kill -0 "$EXISTING_PID" 2>/dev/null; then
    EXISTING_COMMAND=$(ps -p "$EXISTING_PID" -o args= 2>/dev/null || true)
    case "$EXISTING_COMMAND" in
      *"uvicorn backend.main:app"*)
        if curl --silent --fail "$HEALTH_URL" >/dev/null; then
          echo "Server process $EXISTING_PID is already running."
          exit 0
        fi
        echo "Server process $EXISTING_PID exists but is not healthy." >&2
        exit 1
        ;;
      *)
        echo "PID $EXISTING_PID is not the Kanban Studio server; refusing to start another." >&2
        exit 1
        ;;
    esac
  fi
  rm -f "$PID_FILE"
fi

if curl --silent --fail "$HEALTH_URL" >/dev/null; then
  echo "Health endpoint is already responding without a managed PID; refusing to start another server." >&2
  exit 1
fi

cd "$ROOT_DIR"
if [ -f "$ROOT_DIR/.env" ]; then
  nohup uv run --project "$ROOT_DIR/backend" --env-file "$ROOT_DIR/.env" uvicorn backend.main:app \
    --host 127.0.0.1 --port 8000 >"$LOG_FILE" 2>&1 </dev/null &
else
  nohup uv run --project "$ROOT_DIR/backend" uvicorn backend.main:app \
    --host 127.0.0.1 --port 8000 >"$LOG_FILE" 2>&1 </dev/null &
fi
LAUNCH_PID=$!
printf '%s\n' "$LAUNCH_PID" >"$PID_FILE"

ATTEMPT=0
while [ "$ATTEMPT" -lt 30 ]; do
  if curl --silent --fail "$HEALTH_URL" >/dev/null; then
    if ! SERVER_PID=$(find_server_pid "$LAUNCH_PID"); then
      echo "Health endpoint responded, but the server process could not be identified." >&2
      kill "$LAUNCH_PID" 2>/dev/null || true
      rm -f "$PID_FILE"
      exit 1
    fi
    printf '%s\n' "$SERVER_PID" >"$PID_FILE"
    echo "Server started at http://127.0.0.1:8000/ (PID $SERVER_PID)."
    exit 0
  fi
  if ! kill -0 "$LAUNCH_PID" 2>/dev/null; then
    echo "Server process exited during startup. See $LOG_FILE." >&2
    rm -f "$PID_FILE"
    exit 1
  fi
  ATTEMPT=$((ATTEMPT + 1))
  sleep 1
done

echo "Server did not become healthy within 30 seconds. See $LOG_FILE." >&2
if SERVER_PID=$(find_server_pid "$LAUNCH_PID"); then
  kill "$SERVER_PID" 2>/dev/null || true
fi
kill "$LAUNCH_PID" 2>/dev/null || true
rm -f "$PID_FILE"
exit 1
