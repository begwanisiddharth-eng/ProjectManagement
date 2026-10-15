"""Shared FastAPI dependencies for database access and the signed-in user."""

from fastapi import Depends, HTTPException, Request, status

from backend.auth import SESSION_COOKIE, SessionStore
from backend.database import BoardDatabase


def get_database(request: Request) -> BoardDatabase:
    return request.app.state.database


def get_sessions(request: Request) -> SessionStore:
    return request.app.state.sessions


def current_user(
    request: Request, sessions: SessionStore = Depends(get_sessions)
) -> str:
    """Return the signed-in username or raise 401 when the session is missing."""
    username = sessions.get_username(request.cookies.get(SESSION_COOKIE))
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return username
