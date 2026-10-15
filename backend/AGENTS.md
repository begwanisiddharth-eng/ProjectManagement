# Backend guide

The FastAPI application is assembled in `src/backend/main.py` (the `create_app` factory, lifespan, CORS, health route, static serving of `frontend/out/`). Routes live in `APIRouter` modules by concern: `auth_routes.py`, `board_routes.py`, and `ai_routes.py`. Request/response models are in `src/backend/schemas.py`, and shared `Depends` providers (database access, session store, signed-in-user guard) are in `src/backend/dependencies.py`; the database and session store live on `app.state`. SQLite initialization and board operations are in `src/backend/database.py`; the default database is `.data/kanban.sqlite3`, overridable with `KANBAN_DB_PATH`. Build the frontend with `npm ci` and `npm run build` from `frontend/`, then start the combined app from the repository root with `scripts/start.sh` on macOS or Linux, or `scripts/start.ps1` on Windows. When present, the root `.env` is loaded into the backend process by `uv`.

Backend tests are in `backend/tests/`. Run them with:

```bash
uv run --project backend pytest
```

The authenticated `POST /api/ai/chat` route is implemented in `src/backend/ai_routes.py`; request/response validation is in `src/backend/ai_models.py`, and the LiteLLM/Groq provider boundary is in `src/backend/ai.py`. Board changes from AI are validated and applied transactionally by `src/backend/database.py`. The normal tests mock the provider. The live arithmetic check runs only when explicitly enabled with `RUN_GROQ_CONNECTIVITY=1` and a configured `GROQ_API_KEY`.

Python dependencies and project metadata are managed in `pyproject.toml` with `uv`. Keep credentials server-side; never return them from an API route or include them in frontend assets.