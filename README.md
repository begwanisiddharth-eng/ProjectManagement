# Kanban Studio

Kanban Studio is a locally run project-management MVP. A signed-in user gets one persistent Kanban board with five fixed, renameable columns, editable cards, drag-and-drop movement, and an AI chat panel that can answer questions and make validated board changes.

This guide covers using the app, setting it up, understanding its files, and running its checks. The project intentionally has no container runtime requirement.

## Use the application

### Sign in

1. Start the local application using the instructions in [Run locally](#run-locally).
2. Open <http://127.0.0.1:8000/>.
3. Sign in with the MVP account:
   - Username: `user`
   - Password: `password`

These credentials are hardcoded for the MVP. The password is not stored in SQLite. Sessions are held by the backend in memory, expire after eight hours, and are cleared when the server restarts; sign in again after a restart.

### Work with the board

- Rename a column by editing its heading. Its stable column ID remains unchanged.
- Add a card with both a title and nonblank details. The Add card button stays disabled until both are filled in.
- Use the pencil button on a card to edit its title or details.
- Use the trash-can button to delete a card.
- Drag cards between columns or reorder them within a column.
- Board changes are saved by the backend. A rejected save is reported instead of being displayed as a successful update.

### Ask the AI assistant

On wide screens, Board chat is shown alongside the board. On narrower screens, use the Board chat button near the bottom-right corner to open the panel.

Examples:

- “What should I work on next?”
- “Move Prototype analytics view to Review.”
- “Rename the Done column to Finished.”
- “Create a card called Prepare the launch checklist in Backlog with details to confirm the owners and release date.”

The assistant can answer questions and propose card creation, card edits, card moves, and column renames. Its structured response is validated on the backend and applied as one database transaction. Invalid or incomplete changes are rejected without partially changing the board.

AI requests require a valid Groq API key on the backend. Without one, the board still works; chat reports a configuration error.

## Run locally

### Prerequisites

- Windows with PowerShell, macOS, or Linux.
- Python 3.13 or later.
- [`uv`](https://docs.astral.sh/uv/) for Python dependencies and commands.
- Node.js and npm for the Next.js static build and frontend tests.
- A Groq API key to use the AI assistant.

The app binds to `127.0.0.1:8000`. Ensure that port is available.

### Configure Groq

Create a `.env` file in the repository root for the backend-only secret:

```dotenv
GROQ_API_KEY=replace-with-your-groq-api-key
```

Do not commit `.env` or put the key in a frontend environment variable. The local start scripts load the file into the backend process; the static frontend does not receive the key. The model is `groq/openai/gpt-oss-120b`.

### Install and build

From the repository root:

```powershell
uv sync --project backend
Set-Location frontend
npm ci
npm run build
Set-Location ..
```

The frontend build creates `frontend/out/`. FastAPI serves that static export; it does not run a Next.js server in production.

On macOS or Linux, run the equivalent install and build commands from a shell:

```sh
uv sync --project backend
cd frontend
npm ci
npm run build
cd ..
```

### Start and stop

From the repository root in PowerShell:

```powershell
.\scripts\start.ps1
```

The script starts FastAPI and checks `http://127.0.0.1:8000/api/health`. Open <http://127.0.0.1:8000/> when it reports success.

To stop the server:

```powershell
.\scripts\stop.ps1
```

On macOS or Linux, use the matching shell scripts:

```sh
sh scripts/start.sh
sh scripts/stop.sh
```

The scripts refuse to start a second managed server on the same port and verify the process before stopping it. Runtime process IDs and logs are written under `.run/`, which is ignored by Git.

### Frontend development mode

For interactive Next.js development, run the backend on port 8000 in one terminal:

```powershell
uv run --project backend --env-file .env uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

If there is no root `.env`, omit `--env-file .env`; board functionality still works without the AI key. Then run the frontend from another terminal:

```powershell
Set-Location frontend
npm run dev
```

Open <http://localhost:3000/>. In development, frontend API requests go to the local backend and include the session cookie. The backend permits credentialed requests from the local development origins only.

On macOS or Linux, the backend development command is:

```sh
uv run --project backend --env-file .env uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## Tests and quality checks

Run backend tests from the repository root:

```powershell
uv run --project backend pytest
```

Run frontend checks from `frontend/`:

```powershell
npm run lint
npm run test:unit
npm run test:e2e
npm run test:all
npm run build
```

`test:all` runs unit/component tests and browser tests. The Playwright configuration builds the static frontend, starts FastAPI against a temporary SQLite database, and exercises the app in Chromium. The test database is removed during teardown.

The default backend suite mocks all Groq provider calls. The live arithmetic connectivity test is opt-in and requires both a valid key and explicit consent:

```powershell
$env:RUN_GROQ_CONNECTIVITY = "1"
uv run --env-file .env --project backend pytest backend/tests/test_ai_live.py
Remove-Item Env:RUN_GROQ_CONNECTIVITY
```

No live provider call is needed for ordinary setup, board use, or the default tests.

## How the application is organized

The browser renders the static Next.js export. It sends authenticated HTTP requests to FastAPI, which validates requests, applies ownership rules, and reads or writes SQLite. AI requests follow the same path, with the model called only by the backend:

```text
Browser (Next.js static export)
        | session-cookie API requests
        v
FastAPI (auth, board routes, AI endpoint, static file serving)
        |                                  |
        v                                  v
SQLite (.data/kanban.sqlite3)       LiteLLM -> Groq
```

The browser never receives the Groq key. The AI returns a reply plus typed proposed changes; FastAPI validates those changes and SQLite applies the batch transactionally.

### Board data shape

The frontend and API represent columns as an ordered array, with each column referring to card IDs. Card details live in a dictionary keyed by ID:

```ts
type BoardData = {
  columns: { id: string; title: string; cardIds: string[] }[];
  cards: Record<string, { id: string; title: string; details: string }>;
};
```

This makes ordering explicit while keeping references stable when cards move. Column IDs also remain stable when their displayed names are changed.

### AI change format

The AI is asked to return JSON operations rather than directly issue database commands. Supported operations include:

```json
{"operation":"rename_column","column_id":"col-done","title":"Finished"}
```

Other operations are `create`, `edit`, and `move`. Pydantic validates the response shape, while the database layer verifies that referenced cards and columns belong to the signed-in user's board. All proposed operations are applied in a single transaction.

## Project file guide

### Repository root

- `README.md` — This end-user and developer tutorial.
- `AGENTS.md` — Project requirements, technical decisions, visual design tokens, and coding rules for contributors.
- `.gitignore` — Excludes Python/Node environments and generated files, the root `.env`, runtime database directory `.data/`, and server state/logs under `.run/`.

### `backend/`

- `pyproject.toml` — Python package metadata, Python version requirement, runtime dependencies (FastAPI, LiteLLM, Uvicorn), and test dependencies.
- `uv.lock` — Resolved Python dependency versions used by `uv`.
- `.python-version` — Selects Python 3.13 for `uv`.
- `README.md` — Backend-focused setup, authentication, storage, API, and provider-test notes.
- `AGENTS.md` — Backend implementation and testing guidance.
- `src/backend/__init__.py` — Marks the Python backend package.
- `src/backend/main.py` — Assembles the FastAPI application: the `create_app` factory, SQLite initialization on startup, CORS, the health route, router registration, and serving of `frontend/out/`.
- `src/backend/schemas.py` — Pydantic request and response models for the board API, with the shared string-constraint type aliases.
- `src/backend/dependencies.py` — Shared FastAPI dependencies: database and session-store access from application state, and the signed-in-user guard.
- `src/backend/auth_routes.py` — Sign-in, session, and sign-out routes.
- `src/backend/board_routes.py` — Authenticated board read and card/column mutation routes.
- `src/backend/ai_routes.py` — The authenticated AI chat route that applies validated board changes.
- `src/backend/auth.py` — Defines the MVP credentials, session cookie name and lifetime, and in-memory session-token store.
- `src/backend/database.py` — Defines the SQLite schema/migration, seeds the first board, enforces board ownership, loads and changes board data, orders cards, and applies AI operations in transactions.
- `src/backend/ai_models.py` — Strict Pydantic request, reply, and discriminated board-operation types. Field constraints reject empty names/details and unsupported operations.
- `src/backend/ai.py` — The single LiteLLM/Groq provider boundary. Builds a prompt from the signed-in board and chat history, calls the configured model with the server key, and validates the JSON response.
- `tests/test_main.py` — FastAPI, authentication, database lifecycle, API ownership, persistence, and AI endpoint tests. Provider responses are mocked.
- `tests/test_ai.py` — Provider configuration, prompt construction, chat history, and AI response validation tests.
- `tests/test_ai_live.py` — One real-provider arithmetic check, skipped unless explicitly enabled with `RUN_GROQ_CONNECTIVITY=1` and `GROQ_API_KEY`.

### `frontend/`

- `package.json` and `package-lock.json` — JavaScript dependencies and npm scripts for development, static production build, linting, Vitest, and Playwright.
- `.gitignore` — Excludes generated Next.js output, `node_modules`, and test artifacts from normal source control.
- `next.config.ts` — Configures static export and trailing-slash routes for FastAPI hosting.
- `tsconfig.json` — TypeScript compiler settings, strict type checking, and the `@/*` source alias.
- `eslint.config.mjs` — ESLint configuration.
- `vitest.config.ts` — Vitest, jsdom, Testing Library setup, source test selection, and alias resolution.
- `playwright.config.ts` — Starts a fresh static build and FastAPI instance for Chromium browser tests, with a temporary database and teardown.
- `postcss.config.mjs` — Connects Tailwind CSS processing to the frontend build.
- `README.md` — Short frontend-specific build and test commands.
- `AGENTS.md` — Frontend state-flow, component organization, and development/test notes.
- `public/file.svg`, `public/globe.svg`, `public/next.svg`, `public/vercel.svg`, and `public/window.svg` — Static Next.js starter assets, not part of the board behavior.
- `src/app/layout.tsx` — Shared HTML document, font loading, and root layout.
- `src/app/globals.css` — Global styles and the app's yellow, blue, purple, navy, and gray design tokens.
- `src/app/page.tsx` — Checks the session API before rendering the board or redirecting to sign-in.
- `src/app/login/page.tsx` — Sign-in route that renders `LoginForm`.
- `src/app/favicon.ico` — Browser tab icon.
- `src/components/LoginForm.tsx` — Submits credentials, displays login/network errors, and navigates to the board after sign-in.
- `src/components/KanbanBoard.tsx` — Loads the board, coordinates drag/drop and card/column API requests, reflects successful saves, handles retry/error states, and lays out the board with chat.
- `src/components/KanbanColumn.tsx` — Displays and renames one column, renders its ordered cards, and hosts its add-card form.
- `src/components/KanbanCard.tsx` — Renders one card, its accessible edit/delete icon buttons, and its inline edit form.
- `src/components/KanbanCardPreview.tsx` — Compact card view displayed while dragging.
- `src/components/NewCardForm.tsx` — Validates title and required nonblank details before enabling card creation.
- `src/components/BoardChat.tsx` — Responsive chat panel/launcher, conversation history, pending/error UI, and calls to the authenticated AI endpoint. It sends the returned board to `KanbanBoard` so accepted changes show immediately.
- `src/lib/api.ts` — Shared `fetch` helper that includes credentials and directs development requests to FastAPI.
- `src/lib/kanban.ts` — TypeScript board/card/column types and the drag/drop ordering helper (`moveCard`).
- `src/lib/kanban.test.ts` — Unit tests for board ordering and movement helpers.
- `src/components/KanbanBoard.test.tsx` — Component tests for loading, saving, errors, card details validation, and chat states/updates.
- `src/test/setup.ts` and `src/test/vitest.d.ts` — Testing Library matchers and Vitest type declarations.
- `tests/auth.spec.ts` — Browser-level sign-in, session, and logout checks.
- `tests/kanban.spec.ts` — Browser-level board, card, drag/drop, chat, and persistence checks.
- `tests/test-database.ts` and `tests/global-teardown.ts` — Temporary Playwright SQLite path and cleanup.
- `test-results/.last-run.json` — Playwright's generated last-run summary; it is not application data or source code.

### `scripts/`

- `start.ps1` and `stop.ps1` — Windows PowerShell start/health-check and safe stop scripts.
- `start.sh` and `stop.sh` — macOS/Linux shell start/health-check and safe stop scripts.
- `AGENTS.md` — Script platform prerequisites and invocation notes.

### `docs/`

- `PLAN.md` — Implementation phases, verification criteria, acceptance checklist, and platform notes.
- `SQLITE_DATA_MODEL.md` — Ownership, constraints, initialization, and persistence explanation.
- `kanban-schema.json` — Machine-readable design proposal for the SQLite entities and relationships. It is not the runtime database or migration.

### Generated runtime files

- `frontend/out/` — Static site generated by `npm run build`; served by FastAPI. Do not edit it directly.
- `.data/kanban.sqlite3` — Local board data, created automatically the first time FastAPI starts. It is ignored by Git.
- `.run/` — Process ID and server logs generated by the start scripts. It is ignored by Git.

## API overview

All board and AI routes require a valid session cookie. The login and health routes are intentionally public.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Local server health check |
| `POST` | `/api/auth/login` | Create a session using the MVP credentials |
| `GET` | `/api/auth/session` | Check the current session |
| `POST` | `/api/auth/logout` | Invalidate the session |
| `GET` | `/api/board` | Read the signed-in user's board |
| `PATCH` | `/api/board/columns/{column_id}` | Rename a column |
| `POST` | `/api/board/columns/{column_id}/cards` | Add a card with title and nonblank details |
| `PATCH` | `/api/board/cards/{card_id}` | Edit a card |
| `PATCH` | `/api/board/cards/{card_id}/move` | Move or reorder a card |
| `DELETE` | `/api/board/cards/{card_id}` | Delete a card |
| `POST` | `/api/ai/chat` | Ask the assistant and optionally apply validated board changes |

FastAPI's interactive API documentation is available at <http://127.0.0.1:8000/docs> while the app is running.

## Storage and MVP boundaries

SQLite is created at `.data/kanban.sqlite3` on first startup. Set `KANBAN_DB_PATH` to use another path, especially for tests. The schema supports multiple users and enforces one board per user, although sign-in is intentionally hardcoded to one MVP account.

The five columns have stable IDs and can be renamed, but cannot be added, removed, or reordered. Sessions are in memory, so restarting the backend signs everyone out. Groq is only accessed through the backend; live connectivity tests are opt-in.
