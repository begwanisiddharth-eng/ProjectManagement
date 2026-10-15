# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Kanban Studio is a locally run project-management MVP: one signed-in user, one persistent Kanban board (five fixed, renameable columns), and an AI chat panel that proposes validated board changes. Next.js frontend, FastAPI backend, SQLite. See `README.md` for the end-to-end tutorial and the file-by-file guide, `docs/PLAN.md` for phase history, and `AGENTS.md` for requirements, color tokens, and coding rules.

## Commands

Backend (run from repo root; `uv`, never `pip`/bare `python`):

```powershell
uv sync --project backend                        # install deps
uv run --project backend pytest                  # all backend tests (Groq mocked)
uv run --project backend pytest backend/tests/test_main.py::test_name   # single test
uv run --project backend --env-file .env uvicorn backend.main:app --host 127.0.0.1 --port 8000   # dev server
```

Frontend (run from `frontend/`):

```powershell
npm ci
npm run build          # static export to frontend/out/ (this is what FastAPI serves)
npm run lint
npm run test:unit      # Vitest unit/component (*.test.ts[x] colocated with source)
npm run test:e2e       # Playwright; builds the static site and serves it via FastAPI on a temp DB
npm run test:all       # unit then e2e
npx vitest run src/lib/kanban.test.ts   # single unit file
npx playwright test tests/auth.spec.ts  # single browser spec
```

Combined local run from repo root: `.\scripts\start.ps1` (Windows) / `sh scripts/start.sh` (macOS/Linux) starts FastAPI, health-checks `/api/health`, then serve at <http://127.0.0.1:8000/>. Stop with the matching `stop` script. Scripts write PID/logs to `.run/` and refuse to double-start or stop an unrelated process.

The live Groq connectivity test is opt-in only: set `RUN_GROQ_CONNECTIVITY=1` with a valid `GROQ_API_KEY`, then run `backend/tests/test_ai_live.py`. The default suite never makes network calls.

## Architecture

**Single-server model.** There is no Next.js runtime in production. `npm run build` produces a static export in `frontend/out/`, which FastAPI serves at `/` while also hosting the `/api/*` routes. Dev mode is the only time Next.js runs its own server (port 3000), and in that mode the frontend's `src/lib/api.ts` directs API calls to the backend on 8000 with credentialed CORS. Any change to routing, trailing slashes, or served assets involves both `frontend/next.config.ts` (static export config) and the static-serving logic in the backend.

**Backend uses a src layout.** Code lives in `backend/src/backend/`, and the app is imported as `backend.main:app`. Routes are split into `APIRouter` modules by concern rather than living in `main.py`. The pieces:
- `main.py` — app assembly only: the `create_app` factory, lifespan (SQLite init on startup), CORS, the `/api/health` route, `include_router` for the three routers, and static serving of `frontend/out/` (the `/` route + mount). ~64 lines.
- `schemas.py` — the Pydantic request/response DTOs (`LoginRequest`, `CardCreate`, `BoardResponse`, …) plus the shared `StringConstraints` type aliases.
- `dependencies.py` — FastAPI `Depends` providers: `get_database` and `get_sessions` (both read `app.state`), and `current_user` (raises 401 when no valid session). Routes depend on these, so the database and `SessionStore` live on `app.state` and each `create_app()` is independently testable.
- `auth_routes.py` / `board_routes.py` / `ai_routes.py` — the `APIRouter`s for `/api/auth/*`, `/api/board/*`, and `/api/ai/chat`.
- `auth.py` — hardcoded MVP credentials (`user`/`password`) and an **in-memory** session-token store (8-hour expiry). Restarting the backend signs everyone out; the password is never stored in SQLite.
- `database.py` — schema/migration, first-board seeding, ownership enforcement, board read/write, card ordering, and transactional application of AI operations.
- `ai_models.py` — strict Pydantic request/reply types and a **discriminated union** of board operations (`create`, `edit`, `move`, `rename_column`); field constraints reject empty titles/details and unknown operations.
- `ai.py` — the single LiteLLM→Groq boundary (model `groq/openai/gpt-oss-120b`). Builds the prompt from the signed-in user's board + chat history, calls the model with the server-side key, and validates the JSON response.

**AI change flow.** The model returns a user-facing reply plus typed proposed operations — never direct DB commands. `ai_models.py` validates shape; `database.py` verifies referenced cards/columns belong to the signed-in user's board and applies all operations in one transaction. Invalid or incomplete output is rejected without partially mutating the board. The Groq key is backend-only and must never reach frontend assets or API responses.

**Board data shape** (shared mental model across `frontend/src/lib/kanban.ts` and the API; `kanban.ts` holds only the `BoardData`/`Column`/`Card` types and the `moveCard` drag/reorder helper — IDs are generated server-side): columns are an ordered array of `{id, title, cardIds[]}`; card bodies live in a `cards` dict keyed by ID. Ordering is explicit via `cardIds`; references stay stable on move. The five columns have **stable IDs**, can be renamed, but cannot be added, removed, or reordered. Column renames change `title` only, never `id`.

**Persistence boundaries.** SQLite is created at `.data/kanban.sqlite3` on first startup (override with `KANBAN_DB_PATH`, which tests use for isolated temp databases). The schema is multi-user-capable and enforces one board per user even though sign-in is hardcoded to the single MVP account. `.data/`, `.run/`, `.env`, and `frontend/out/` are git-ignored and generated — do not edit `frontend/out/` by hand.

## Conventions

- Keep it simple; do not over-engineer or add defensive code/exception handlers unless genuinely needed. No emojis anywhere (code, logs, output).
- Diagnose root cause with evidence before fixing; work in small, validated increments.
- Use latest library APIs. TypeScript config is strict with `@/*` mapped to `frontend/src/*`.
- Visual design tokens (yellow `#ecad0a`, blue `#209dd7`, purple `#753991`, navy `#032147`, gray `#888888`) are defined in `frontend/src/app/globals.css`; preserve them.
