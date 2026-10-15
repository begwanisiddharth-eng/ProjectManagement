from secrets import token_urlsafe
from time import time

SESSION_COOKIE = "kanban_session"
SESSION_TTL_SECONDS = 8 * 60 * 60
USERNAME = "user"
PASSWORD = "password"


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, tuple[str, float]] = {}

    def create(self, username: str) -> str:
        token = token_urlsafe(32)
        self._sessions[token] = (username, time() + SESSION_TTL_SECONDS)
        return token

    def get_username(self, token: str | None) -> str | None:
        if token is None:
            return None
        session = self._sessions.get(token)
        if session is None:
            return None
        username, expires_at = session
        if expires_at <= time():
            self._sessions.pop(token)
            return None
        return username

    def delete(self, token: str | None) -> None:
        if token is not None:
            self._sessions.pop(token, None)
