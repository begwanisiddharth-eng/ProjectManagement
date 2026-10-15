"""Sign-in, session, and sign-out routes."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from backend.auth import (
    PASSWORD,
    SESSION_COOKIE,
    SESSION_TTL_SECONDS,
    USERNAME,
    SessionStore,
)
from backend.dependencies import current_user, get_sessions
from backend.schemas import LoginRequest

router = APIRouter(prefix="/api/auth")


@router.post("/login")
def login(
    credentials: LoginRequest,
    response: Response,
    sessions: SessionStore = Depends(get_sessions),
) -> dict[str, str]:
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
