from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from backend.ai_routes import router as ai_router
from backend.auth import SESSION_COOKIE, SessionStore
from backend.auth_routes import router as auth_router
from backend.board_routes import router as board_router
from backend.database import BoardDatabase

FRONTEND_BUILD_DIR = Path(__file__).resolve().parents[3] / "frontend" / "out"


def create_app(
    frontend_dir: Path = FRONTEND_BUILD_DIR,
    database_path: Path | None = None,
) -> FastAPI:
    database = BoardDatabase(database_path)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        database.initialize()
        yield

    app = FastAPI(title="Kanban Studio API", lifespan=lifespan)
    app.state.database = database
    app.state.sessions = SessionStore()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(board_router)
    app.include_router(ai_router)

    @app.get("/", include_in_schema=False)
    def root(request: Request) -> Response:
        if app.state.sessions.get_username(request.cookies.get(SESSION_COOKIE)) is None:
            return RedirectResponse("/login/", status_code=status.HTTP_303_SEE_OTHER)
        return FileResponse(frontend_dir / "index.html")

    app.mount(
        "/",
        StaticFiles(directory=frontend_dir, html=True, check_dir=False),
        name="frontend",
    )
    return app


app = create_app()
