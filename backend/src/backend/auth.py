import hashlib
import hmac
from secrets import token_bytes, token_urlsafe
from time import time

SESSION_COOKIE = "kanban_session"
SESSION_TTL_SECONDS = 8 * 60 * 60
USERNAME = "user"
PASSWORD = "password"

PBKDF2_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ROUNDS = 200_000


def hash_password(password: str) -> str:
    """Return a salted PBKDF2-SHA256 hash encoded as algorithm$rounds$salt$digest."""
    salt = token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS)
    return f"{PBKDF2_ALGORITHM}${PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Check a password against an encoded hash in constant time."""
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded.split("$")
    except ValueError:
        return False
    if algorithm != PBKDF2_ALGORITHM:
        return False
    expected = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds)
    )
    return hmac.compare_digest(expected.hex(), digest_hex)


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
