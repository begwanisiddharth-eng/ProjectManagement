"""Sign-in, registration, session, and sign-out routes."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from backend.auth import (
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    SessionStore,
)
from backend.database import BoardDatabase
from backend.dependencies import current_user, get_database, get_sessions
from backend.schemas import LoginRequest, RegisterRequest

router = APIRouter(prefix="/api/auth")


def _start_session(response: Response, sessions: SessionStore, username: str) -> None:
    token = sessions.create(username)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        path="/",
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    credentials: RegisterRequest,
    response: Response,
    sessions: SessionStore = Depends(get_sessions),
    database: BoardDatabase = Depends(get_database),
) -> dict[str, str]:
    user_id = database.create_user(credentials.username, credentials.password)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already taken",
        )
    _start_session(response, sessions, credentials.username)
    return {"username": credentials.username}


@router.post("/login")
def login(
    credentials: LoginRequest,
    response: Response,
    sessions: SessionStore = Depends(get_sessions),
    database: BoardDatabase = Depends(get_database),
) -> dict[str, str]:
    if not database.authenticate(credentials.username, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    _start_session(response, sessions, credentials.username)
    return {"username": credentials.username}


@router.get("/session")
def get_session(user: str = Depends(current_user)) -> dict[str, str]:
    return {"username": user}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    sessions: SessionStore = Depends(get_sessions),
) -> None:
    sessions.delete(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        samesite="lax",
        path="/",
    )
