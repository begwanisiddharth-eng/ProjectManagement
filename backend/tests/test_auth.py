"""User management: registration, hashed credentials, and DB-backed login."""

from fastapi.testclient import TestClient

from backend.auth import SESSION_COOKIE, hash_password, verify_password


def test_password_hashing_roundtrip_and_rejection() -> None:
    encoded = hash_password("correct horse battery staple")

    assert encoded.startswith("pbkdf2_sha256$")
    assert "correct horse battery staple" not in encoded
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)
    assert not verify_password("anything", "not-a-valid-hash")


def test_register_creates_user_with_seeded_board_and_signs_in(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "supersecret"},
    )

    assert response.status_code == 201
    assert response.json() == {"username": "alice"}
    assert SESSION_COOKIE in response.cookies

    session = client.get("/api/auth/session")
    assert session.status_code == 200
    assert session.json() == {"username": "alice"}

    board = client.get("/api/board")
    assert board.status_code == 200
    assert [column["id"] for column in board.json()["columns"]] == [
        "col-backlog",
        "col-discovery",
        "col-progress",
        "col-review",
        "col-done",
    ]
    assert board.json()["cards"] == {}


def test_registered_user_can_log_in_after_logout(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"username": "bob", "password": "hunter2hunter2"},
    )
    client.post("/api/auth/logout")

    login = client.post(
        "/api/auth/login",
        json={"username": "bob", "password": "hunter2hunter2"},
    )

    assert login.status_code == 200
    assert login.json() == {"username": "bob"}
    assert client.get("/api/auth/session").json() == {"username": "bob"}


def test_register_rejects_duplicate_username(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"username": "carol", "password": "password-one"},
    )
    client.post("/api/auth/logout")

    duplicate = client.post(
        "/api/auth/register",
        json={"username": "carol", "password": "password-two"},
    )

    assert duplicate.status_code == 409
    assert SESSION_COOKIE not in duplicate.cookies


def test_register_validates_username_and_password_length(client: TestClient) -> None:
    short_username = client.post(
        "/api/auth/register",
        json={"username": "ab", "password": "longenough"},
    )
    short_password = client.post(
        "/api/auth/register",
        json={"username": "dave", "password": "short"},
    )

    assert short_username.status_code == 422
    assert short_password.status_code == 422


def test_login_rejects_wrong_password_for_existing_user(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"username": "erin", "password": "correctpassword"},
    )
    client.post("/api/auth/logout")

    response = client.post(
        "/api/auth/login",
        json={"username": "erin", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert SESSION_COOKIE not in response.cookies


def test_passwords_are_stored_hashed_not_in_plaintext(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"username": "frank", "password": "plaintextcheck"},
    )

    with client.app.state.database.connect() as connection:
        row = connection.execute(
            "SELECT password_hash FROM users WHERE username = ?", ("frank",)
        ).fetchone()

    assert row["password_hash"].startswith("pbkdf2_sha256$")
    assert "plaintextcheck" not in row["password_hash"]


def test_users_boards_are_isolated_from_each_other(client: TestClient) -> None:
    client.post(
        "/api/auth/register",
        json={"username": "grace", "password": "gracepassword"},
    )
    client.post(
        "/api/board/columns/col-backlog/cards",
        json={"title": "Grace private card", "details": "Only grace sees this."},
    )
    client.post("/api/auth/logout")

    client.post(
        "/api/auth/register",
        json={"username": "heidi", "password": "heidipassword"},
    )
    board = client.get("/api/board").json()

    assert board["cards"] == {}
