from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, AsyncIterator

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, StringConstraints
from starlette.middleware.cors import CORSMiddleware

from backend.ai import (
    AIConfigurationError,
    AIProviderError,
    AIResponseError,
    generate_board_assistance,
)
from backend.ai_models import AIChatRequest
from backend.auth import (
    PASSWORD,
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    USERNAME,
    SessionStore,
)
from backend.database import BoardDatabase

FRONTEND_BUILD_DIR = Path(__file__).resolve().parents[3] / "frontend" / "out"
BoardTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
CardTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
CardDetails = Annotated[str, StringConstraints(max_length=4000)]


class LoginRequest(BaseModel):
    username: str
    password: str


class ColumnRename(BaseModel):
    title: BoardTitle


class CardCreate(BaseModel):
    title: CardTitle
    details: CardDetails = ""


class CardUpdate(BaseModel):
    title: CardTitle
    details: CardDetails = ""


class CardMove(BaseModel):
    column_id: str
    position: int = Field(ge=0)


class BoardCard(BaseModel):
    id: str
    title: str
    details: str


class BoardColumn(BaseModel):
    id: str
    title: str
    cardIds: list[str]


class BoardResponse(BaseModel):
    columns: list[BoardColumn]
    cards: dict[str, BoardCard]


class AIChatResponse(BaseModel):
    reply: str
    changed: bool
    board: BoardResponse


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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )
    sessions = SessionStore()

    def current_user(request: Request) -> str:
        username = sessions.get_username(request.cookies.get(SESSION_COOKIE))
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        return username

    @app.post("/api/auth/login")
    def login(credentials: LoginRequest, response: Response) -> dict[str, str]:
        if credentials.username != USERNAME or credentials.password != PASSWORD:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        token = sessions.create(USERNAME)
        response.set_cookie(
            key=SESSION_COOKIE,
            value=token,
            max_age=SESSION_TTL_SECONDS,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return {"username": USERNAME}

    @app.get("/api/auth/session")
    def get_session(request: Request) -> dict[str, str]:
        return {"username": current_user(request)}

    @app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
    def logout(request: Request, response: Response) -> None:
        sessions.delete(request.cookies.get(SESSION_COOKIE))
        response.delete_cookie(
            key=SESSION_COOKIE,
            httponly=True,
            samesite="lax",
            path="/",
        )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/hello")
    def hello(request: Request) -> dict[str, str]:
        current_user(request)
        return {"message": "Hello, world!"}

    @app.get("/api/board", response_model=BoardResponse)
    def get_board(request: Request) -> dict[str, object]:
        board = database.get_board(current_user(request))
        if board is None:
            raise HTTPException(status_code=404, detail="Board not found")
        return board

    @app.patch("/api/board/columns/{column_id}", response_model=BoardResponse)
    def rename_column(
        column_id: str, update: ColumnRename, request: Request
    ) -> dict[str, object]:
        board = database.rename_column(
            current_user(request), column_id, update.title
        )
        if board is None:
            raise HTTPException(status_code=404, detail="Column not found")
        return board

    @app.post(
        "/api/board/columns/{column_id}/cards",
        response_model=BoardResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_card(
        column_id: str, card: CardCreate, request: Request
    ) -> dict[str, object]:
        board = database.create_card(
            current_user(request), column_id, card.title, card.details
        )
        if board is None:
            raise HTTPException(status_code=404, detail="Column not found")
        return board

    @app.patch("/api/board/cards/{card_id}", response_model=BoardResponse)
    def update_card(
        card_id: str, update: CardUpdate, request: Request
    ) -> dict[str, object]:
        board = database.update_card(
            current_user(request), card_id, update.title, update.details
        )
        if board is None:
            raise HTTPException(status_code=404, detail="Card not found")
        return board

    @app.patch("/api/board/cards/{card_id}/move", response_model=BoardResponse)
    def move_card(
        card_id: str, move: CardMove, request: Request
    ) -> dict[str, object]:
        board = database.move_card(
            current_user(request), card_id, move.column_id, move.position
        )
        if board is None:
            raise HTTPException(status_code=404, detail="Card or column not found")
        return board

    @app.delete("/api/board/cards/{card_id}", response_model=BoardResponse)
    def delete_card(card_id: str, request: Request) -> dict[str, object]:
        board = database.delete_card(current_user(request), card_id)
        if board is None:
            raise HTTPException(status_code=404, detail="Card not found")
        return board

    @app.post("/api/ai/chat", response_model=AIChatResponse)
    def chat_with_board(
        chat: AIChatRequest, request: Request
    ) -> dict[str, object]:
        username = current_user(request)
        board = database.get_board(username)
        if board is None:
            raise HTTPException(status_code=404, detail="Board not found")
        try:
            result = generate_board_assistance(
                chat.question,
                board,
                chat.history,
            )
        except AIConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except (AIProviderError, AIResponseError) as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        try:
            updated_board = database.apply_ai_changes(username, result.changes)
        except ValueError as exc:
            raise HTTPException(
                status_code=502,
                detail="The AI proposed invalid board changes; no changes were applied.",
            ) from exc
        if updated_board is None:
            raise HTTPException(status_code=404, detail="Board not found")
        return {
            "reply": result.reply,
            "changed": updated_board != board,
            "board": updated_board,
        }

    @app.get("/", include_in_schema=False)
    def root(request: Request) -> Response:
        if sessions.get_username(request.cookies.get(SESSION_COOKIE)) is None:
            return RedirectResponse("/login/", status_code=status.HTTP_303_SEE_OTHER)
        return FileResponse(frontend_dir / "index.html")

    app.mount(
        "/",
        StaticFiles(directory=frontend_dir, html=True, check_dir=False),
        name="frontend",
    )
    return app


app = create_app()
