# Backend

Install dependencies from the repository root with `uv sync --project backend`.

Build the static frontend from `frontend/` with `npm ci` and `npm run build`. Run the combined app with `scripts/start.sh` on macOS or Linux, or `scripts/start.ps1` on Windows. FastAPI serves the generated `frontend/out/` site at `/`. When present, the root `.env` is loaded into the backend process by `uv`; its values are not served to the browser.

Authentication uses the MVP credentials `user` and `password`, an HTTP-only session cookie, and in-memory server-side sessions. Sessions expire after eight hours and are cleared on server restart. The health and authentication endpoints are public as required for sign-in; application API routes require a valid session.

The SQLite database is created and seeded on startup at `.data/kanban.sqlite3`. Set `KANBAN_DB_PATH` to use another database location, including a temporary path in tests.

The authenticated `POST /api/ai/chat` endpoint uses `litellm` with the Groq model `groq/openai/gpt-oss-120b`. It reads `GROQ_API_KEY` from the backend environment; the root `.env` is loaded by the local start scripts. The request accepts a `question` and optional conversation `history` (up to 20 user/assistant messages). The response contains the assistant `reply`, whether the board `changed`, and the updated `board`. AI-generated create, edit, and move operations are validated and applied together; invalid operations are rejected without changing the board.

Run backend tests with `uv run --project backend pytest`.

The offline tests mock the provider. To explicitly run the live arithmetic connectivity check when the root `.env` contains a valid key, set `RUN_GROQ_CONNECTIVITY=1` and run `uv run --env-file .env --project backend pytest backend/tests/test_ai_live.py`.