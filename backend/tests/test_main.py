import json
import sqlite3
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend import ai
from backend.auth import SESSION_COOKIE, USERNAME
from backend.database import SCHEMA_VERSION, timestamp
from backend.main import create_app


def sign_in(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200


def board_id(client: TestClient) -> str:
    response = client.get("/api/boards")
    assert response.status_code == 200
    return response.json()[0]["id"]


def mock_ai_completion(
    monkeypatch: pytest.MonkeyPatch,
    content: str,
    captured_calls: list[dict[str, object]] | None = None,
) -> None:
    def fake_completion(**kwargs: object) -> SimpleNamespace:
        if captured_calls is not None:
            captured_calls.append(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )

    monkeypatch.setenv("GROQ_API_KEY", "test-secret")
    monkeypatch.setattr(ai.litellm, "completion", fake_completion)


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_logged_out_root_redirects_to_sign_in(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.url.path == "/login/"
    assert response.history[0].status_code == 303
    assert "<h1>Sign in</h1>" in response.text


def test_signed_in_root_serves_static_frontend(client: TestClient) -> None:
    sign_in(client)

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<h1>Kanban Studio</h1>" in response.text


def test_serves_exported_route_and_asset(client: TestClient) -> None:
    frontend_dir = client.app.state.database.path.parent.parent / "frontend"
    nested_dir = frontend_dir / "guide"
    nested_dir.mkdir()
    (nested_dir / "index.html").write_text("<h1>Guide</h1>", encoding="utf-8")
    asset_dir = frontend_dir / "_next" / "static"
    asset_dir.mkdir(parents=True)
    (asset_dir / "app.css").write_text("body { color: navy; }", encoding="utf-8")
    sign_in(client)

    page_response = client.get("/guide/")
    asset_response = client.get("/_next/static/app.css")

    assert page_response.status_code == 200
    assert "<h1>Guide</h1>" in page_response.text
    assert asset_response.status_code == 200
    assert asset_response.text == "body { color: navy; }"


def test_unexported_route_returns_not_found(client: TestClient) -> None:
    sign_in(client)

    response = client.get("/not-exported")

    assert response.status_code == 404


def test_login_rejects_invalid_credentials_without_cookie(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "wrong"},
    )

    assert response.status_code == 401
    assert SESSION_COOKIE not in response.cookies


def test_login_sets_httponly_session_and_session_endpoint_reads_it(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    session_response = client.get("/api/auth/session")

    assert response.status_code == 200
    assert response.json() == {"username": USERNAME}
    assert SESSION_COOKIE in response.cookies
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "samesite=lax" in response.headers["set-cookie"].lower()
    assert session_response.status_code == 200
    assert session_response.json() == {"username": USERNAME}


def test_session_endpoint_rejects_logged_out_user(client: TestClient) -> None:
    response = client.get("/api/auth/session")

    assert response.status_code == 401


def test_logout_invalidates_session_and_deletes_cookie(client: TestClient) -> None:
    sign_in(client)

    logout_response = client.post("/api/auth/logout")
    session_response = client.get("/api/auth/session")
    root_response = client.get("/")

    assert logout_response.status_code == 204
    assert SESSION_COOKIE in logout_response.headers["set-cookie"]
    assert "max-age=0" in logout_response.headers["set-cookie"].lower()
    assert session_response.status_code == 401
    assert root_response.url.path == "/login/"


def test_development_frontend_origin_can_use_cookie_auth(
    client: TestClient,
) -> None:
    for method in ("POST", "PATCH", "DELETE"):
        response = client.options(
            "/api/auth/login",
            headers={
                "Origin": "http://127.0.0.1:3000",
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": "content-type",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
        assert response.headers["access-control-allow-credentials"] == "true"
        assert method in response.headers["access-control-allow-methods"]


def test_startup_creates_and_seeds_database_without_overwriting_data(
    client: TestClient,
) -> None:
    database = client.app.state.database
    assert database.path.exists()

    bid = database.list_boards(USERNAME)[0]["id"]
    board = database.get_board(USERNAME, bid)
    assert board is not None
    assert len(board["columns"]) == 5
    assert len(board["cards"]) == 8

    with database.connect() as connection:
        connection.execute(
            "UPDATE boards SET title = ?",
            ("Changed board",),
        )
        connection.execute("DELETE FROM cards WHERE id = ?", ("card-8",))
    database.initialize()

    preserved_board = database.get_board(USERNAME, bid)
    assert preserved_board is not None
    assert len(preserved_board["cards"]) == 7
    with database.connect() as connection:
        title = connection.execute("SELECT title FROM boards").fetchone()["title"]
        versions = connection.execute(
            "SELECT COUNT(*) AS count FROM schema_migrations"
        ).fetchone()["count"]
    assert title == "Changed board"
    assert versions == SCHEMA_VERSION


def test_board_updates_survive_a_new_application_instance(
    client: TestClient,
) -> None:
    sign_in(client)
    bid = board_id(client)
    database_path = client.app.state.database.path
    frontend_dir = database_path.parent.parent / "frontend"
    created = client.post(
        f"/api/boards/{bid}/columns/col-backlog/cards",
        json={"title": "Persist across restart", "details": "Saved to SQLite."},
    )
    assert created.status_code == 201
    client.patch(
        f"/api/boards/{bid}/columns/col-backlog",
        json={"title": "Priorities"},
    )

    restarted_app = create_app(
        frontend_dir=frontend_dir,
        database_path=database_path,
    )
    with TestClient(restarted_app) as restarted_client:
        sign_in(restarted_client)
        response = restarted_client.get(f"/api/boards/{bid}")

    assert response.status_code == 200
    board = response.json()
    assert board["columns"][0]["title"] == "Priorities"
    assert any(
        card["title"] == "Persist across restart"
        for card in board["cards"].values()
    )


def test_get_board_returns_seeded_board_for_authenticated_user(
    client: TestClient,
) -> None:
    sign_in(client)
    bid = board_id(client)

    response = client.get(f"/api/boards/{bid}")

    assert response.status_code == 200
    board = response.json()
    assert [column["id"] for column in board["columns"]] == [
        "col-backlog",
        "col-discovery",
        "col-progress",
        "col-review",
        "col-done",
    ]
    assert len(board["cards"]) == 8
    assert board["columns"][0]["cardIds"] == ["card-1", "card-2"]


def test_get_board_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/boards/any-board")

    assert response.status_code == 401


def test_rename_column_persists_title_but_keeps_fixed_id(
    client: TestClient,
) -> None:
    sign_in(client)
    bid = board_id(client)

    response = client.patch(
        f"/api/boards/{bid}/columns/col-backlog",
        json={"title": "Priorities"},
    )

    assert response.status_code == 200
    assert response.json()["columns"][0]["id"] == "col-backlog"
    assert response.json()["columns"][0]["title"] == "Priorities"


def test_rename_column_rejects_blank_or_unknown_column(
    client: TestClient,
) -> None:
    sign_in(client)
    bid = board_id(client)

    blank_response = client.patch(
        f"/api/boards/{bid}/columns/col-backlog",
        json={"title": "  "},
    )
    unknown_response = client.patch(
        f"/api/boards/{bid}/columns/other",
        json={"title": "Other"},
    )

    assert blank_response.status_code == 422
    assert unknown_response.status_code == 404


def test_create_update_move_and_delete_card(client: TestClient) -> None:
    sign_in(client)
    bid = board_id(client)
    create_response = client.post(
        f"/api/boards/{bid}/columns/col-backlog/cards",
        json={"title": "Follow up", "details": "Contact the client."},
    )

    assert create_response.status_code == 201
    board = create_response.json()
    created_id = board["columns"][0]["cardIds"][-1]
    assert board["cards"][created_id]["title"] == "Follow up"

    update_response = client.patch(
        f"/api/boards/{bid}/cards/{created_id}",
        json={"title": "Client follow-up", "details": "Send a summary."},
    )
    assert update_response.status_code == 200
    assert update_response.json()["cards"][created_id] == {
        "id": created_id,
        "title": "Client follow-up",
        "details": "Send a summary.",
    }

    move_response = client.patch(
        f"/api/boards/{bid}/cards/{created_id}/move",
        json={"column_id": "col-review", "position": 0},
    )
    moved_board = move_response.json()
    assert move_response.status_code == 200
    assert moved_board["columns"][0]["cardIds"] == ["card-1", "card-2"]
    assert moved_board["columns"][3]["cardIds"] == [
        created_id,
        "card-6",
    ]

    delete_response = client.delete(f"/api/boards/{bid}/cards/{created_id}")
    deleted_board = delete_response.json()
    assert delete_response.status_code == 200
    assert created_id not in deleted_board["cards"]
    assert deleted_board["columns"][3]["cardIds"] == ["card-6"]


def test_move_card_reorders_within_a_column(client: TestClient) -> None:
    sign_in(client)
    bid = board_id(client)

    response = client.patch(
        f"/api/boards/{bid}/cards/card-2/move",
        json={"column_id": "col-backlog", "position": 0},
    )

    assert response.status_code == 200
    assert response.json()["columns"][0]["cardIds"] == ["card-2", "card-1"]


def test_create_card_requires_nonblank_details(client: TestClient) -> None:
    sign_in(client)
    bid = board_id(client)

    missing_details = client.post(
        f"/api/boards/{bid}/columns/col-backlog/cards",
        json={"title": "Card"},
    )
    blank_details = client.post(
        f"/api/boards/{bid}/columns/col-backlog/cards",
        json={"title": "Card", "details": "   "},
    )

    assert missing_details.status_code == 422
    assert blank_details.status_code == 422


def test_move_card_to_first_position_when_source_and_target_positions_match(
    client: TestClient,
) -> None:
    sign_in(client)
    bid = board_id(client)

    response = client.patch(
        f"/api/boards/{bid}/cards/card-1/move",
        json={"column_id": "col-review", "position": 0},
    )

    assert response.status_code == 200
    board = response.json()
    assert board["columns"][0]["cardIds"] == ["card-2"]
    assert board["columns"][3]["cardIds"] == ["card-1", "card-6"]


def test_board_api_rejects_invalid_and_missing_records(client: TestClient) -> None:
    sign_in(client)
    bid = board_id(client)

    invalid_card = client.post(
        f"/api/boards/{bid}/columns/col-backlog/cards",
        json={"title": "  ", "details": ""},
    )
    missing_column = client.post(
        f"/api/boards/{bid}/columns/missing/cards",
        json={"title": "Card", "details": "Card details."},
    )
    missing_card = client.patch(
        f"/api/boards/{bid}/cards/missing",
        json={"title": "Card"},
    )
    invalid_move = client.patch(
        f"/api/boards/{bid}/cards/card-1/move",
        json={"column_id": "missing", "position": 0},
    )
    negative_position = client.patch(
        f"/api/boards/{bid}/cards/card-1/move",
        json={"column_id": "col-review", "position": -1},
    )

    assert invalid_card.status_code == 422
    assert missing_column.status_code == 404
    assert missing_card.status_code == 404
    assert invalid_move.status_code == 404
    assert negative_position.status_code == 422


def test_board_api_cannot_access_another_users_records(client: TestClient) -> None:
    sign_in(client)
    bid = board_id(client)
    database = client.app.state.database
    now = timestamp()
    with database.connect() as connection:
        connection.execute(
            """INSERT INTO users (id, username, password_hash, created_at)
            VALUES (?, ?, ?, ?)""",
            ("other-user", "other", "", now),
        )
        connection.execute(
            """INSERT INTO boards (id, user_id, title, position, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            ("other-board", "other-user", "Other", 0, now, now),
        )
        connection.execute(
            "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            ("other-column", "other-board", "Other", 0),
        )
        connection.execute(
            """INSERT INTO cards
            (id, board_id, column_id, title, details, position, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "other-card",
                "other-board",
                "other-column",
                "Private",
                "",
                0,
                now,
                now,
            ),
        )

    # Signed in as "user", attempts to reach another user's board are rejected.
    via_own_board = client.patch(
        f"/api/boards/{bid}/cards/other-card",
        json={"title": "Changed", "details": ""},
    )
    via_other_board = client.patch(
        "/api/boards/other-board/cards/other-card",
        json={"title": "Changed", "details": ""},
    )

    assert via_own_board.status_code == 404
    assert via_other_board.status_code == 404
    with database.connect() as connection:
        title = connection.execute(
            "SELECT title FROM cards WHERE id = ?", ("other-card",)
        ).fetchone()["title"]
    assert title == "Private"


def test_database_enforces_board_column_ownership(client: TestClient) -> None:
    database = client.app.state.database
    now = timestamp()
    with database.connect() as connection:
        connection.execute(
            """INSERT INTO users (id, username, password_hash, created_at)
            VALUES (?, ?, ?, ?)""",
            ("other-user", "other", "", now),
        )
        connection.execute(
            """INSERT INTO boards (id, user_id, title, position, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            ("other-board", "other-user", "Other", 0, now, now),
        )
        connection.execute(
            "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            ("other-column", "other-board", "Other", 0),
        )
    with pytest.raises(sqlite3.IntegrityError):
        with database.connect() as connection:
            connection.execute(
                """INSERT INTO cards
                (id, board_id, column_id, title, details, position, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "invalid-card",
                    "other-board",
                    "col-backlog",
                    "Invalid",
                    "",
                    0,
                    now,
                    now,
                ),
            )


def test_ai_chat_requires_authentication(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    response = client.post(
        "/api/boards/any-board/chat",
        json={"question": "Create a launch card."},
    )

    assert response.status_code == 401


def test_ai_chat_sends_only_the_signed_in_board_and_applies_changes(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sign_in(client)
    bid = board_id(client)
    database = client.app.state.database
    now = timestamp()
    with database.connect() as connection:
        connection.execute(
            """INSERT INTO users (id, username, password_hash, created_at)
            VALUES (?, ?, ?, ?)""",
            ("other-user", "other", "", now),
        )
        connection.execute(
            """INSERT INTO boards (id, user_id, title, position, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            ("other-board", "other-user", "Other Board", 0, now, now),
        )
        connection.execute(
            "INSERT INTO columns (id, board_id, title, position) VALUES (?, ?, ?, ?)",
            ("other-column", "other-board", "Other", 0),
        )
        connection.execute(
            """INSERT INTO cards
            (id, board_id, column_id, title, details, position, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "other-card",
                "other-board",
                "other-column",
                "Confidential other-user item",
                "",
                0,
                now,
                now,
            ),
        )

    calls: list[dict[str, object]] = []
    mock_ai_completion(
        monkeypatch,
        json.dumps(
            {
                "reply": "I created a task, updated the roadmap, and moved the signals card.",
                "changes": [
                    {
                        "operation": "create",
                        "column_id": "col-discovery",
                        "title": "Coordinate launch",
                        "details": "Align the launch owners.",
                    },
                    {
                        "operation": "edit",
                        "card_id": "card-1",
                        "title": "Align launch roadmap",
                        "details": "Confirm launch themes.",
                    },
                    {
                        "operation": "move",
                        "card_id": "card-2",
                        "column_id": "col-review",
                        "position": 0,
                    },
                ],
            }
        ),
        calls,
    )

    response = client.post(
        f"/api/boards/{bid}/chat",
        json={
            "question": "Prepare these launch updates.",
            "history": [
                {"role": "user", "content": "The launch is next week."},
                {"role": "assistant", "content": "I will take that into account."},
            ],
        },
    )

    assert response.status_code == 200
    result = response.json()
    assert result["reply"].startswith("I created")
    assert result["changed"] is True
    board = result["board"]
    assert board["cards"]["card-1"]["title"] == "Align launch roadmap"
    assert any(
        card["title"] == "Coordinate launch" for card in board["cards"].values()
    )
    assert board["columns"][3]["cardIds"][0] == "card-2"
    messages = calls[0]["messages"]
    serialized_messages = json.dumps(messages)
    assert "Align roadmap themes" in serialized_messages
    assert "The launch is next week." in serialized_messages
    assert "Prepare these launch updates." in serialized_messages
    assert "Confidential other-user item" not in serialized_messages
    assert "test-secret" not in serialized_messages
    assert "test-secret" not in response.text


def test_ai_chat_without_changes_leaves_the_board_unchanged(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sign_in(client)
    bid = board_id(client)
    original_board = client.get(f"/api/boards/{bid}").json()
    mock_ai_completion(
        monkeypatch,
        json.dumps({"reply": "No board changes are needed.", "changes": []}),
    )

    response = client.post(
        f"/api/boards/{bid}/chat",
        json={"question": "What should I work on next?"},
    )

    assert response.status_code == 200
    assert response.json()["changed"] is False
    assert response.json()["board"] == original_board


def test_ai_edit_of_one_field_preserves_the_other_field(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sign_in(client)
    bid = board_id(client)
    mock_ai_completion(
        monkeypatch,
        json.dumps(
            {
                "reply": "I updated the card title.",
                "changes": [
                    {
                        "operation": "edit",
                        "card_id": "card-1",
                        "title": "Updated roadmap",
                    }
                ],
            }
        ),
    )

    response = client.post(
        f"/api/boards/{bid}/chat",
        json={"question": "Rename the roadmap card."},
    )

    assert response.status_code == 200
    updated_card = response.json()["board"]["cards"]["card-1"]
    assert updated_card["title"] == "Updated roadmap"
    assert updated_card["details"] == (
        "Draft quarterly themes with impact statements and metrics."
    )


def test_ai_chat_can_rename_a_column(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sign_in(client)
    bid = board_id(client)
    mock_ai_completion(
        monkeypatch,
        json.dumps(
            {
                "reply": "I renamed Done to Finished.",
                "changes": [
                    {
                        "operation": "rename_column",
                        "column_id": "col-done",
                        "title": "Finished",
                    }
                ],
            }
        ),
    )

    response = client.post(
        f"/api/boards/{bid}/chat",
        json={"question": "Rename the Done column to Finished."},
    )

    assert response.status_code == 200
    assert response.json()["changed"] is True
    renamed_column = next(
        column
        for column in response.json()["board"]["columns"]
        if column["id"] == "col-done"
    )
    assert renamed_column["title"] == "Finished"
    assert client.get(f"/api/boards/{bid}").json()["columns"][4]["title"] == "Finished"


def test_ai_chat_reports_idempotent_move_as_no_change(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sign_in(client)
    bid = board_id(client)
    original_board = client.get(f"/api/boards/{bid}").json()
    mock_ai_completion(
        monkeypatch,
        json.dumps(
            {
                "reply": "The card is already at the top of the backlog.",
                "changes": [
                    {
                        "operation": "move",
                        "card_id": "card-1",
                        "column_id": "col-backlog",
                        "position": 0,
                    }
                ],
            }
        ),
    )

    response = client.post(
        f"/api/boards/{bid}/chat",
        json={"question": "Move the first backlog card to the top."},
    )

    assert response.status_code == 200
    assert response.json()["changed"] is False
    assert response.json()["board"] == original_board


def test_ai_chat_rejects_invalid_changes_without_partial_updates(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sign_in(client)
    bid = board_id(client)
    original_board = client.get(f"/api/boards/{bid}").json()
    mock_ai_completion(
        monkeypatch,
        json.dumps(
            {
                "reply": "I made the requested changes.",
                "changes": [
                    {
                        "operation": "create",
                        "column_id": "col-backlog",
                        "title": "Temporary accepted item",
                        "details": "This should roll back.",
                    },
                    {
                        "operation": "rename_column",
                        "column_id": "col-done",
                        "title": "Temporary Finished",
                    },
                    {
                        "operation": "move",
                        "card_id": "missing-card",
                        "column_id": "col-review",
                        "position": 0,
                    },
                ],
            }
        ),
    )

    response = client.post(
        f"/api/boards/{bid}/chat",
        json={"question": "Create a task and move a missing task."},
    )

    assert response.status_code == 502
    assert "no changes were applied" in response.json()["detail"]
    assert client.get(f"/api/boards/{bid}").json() == original_board


@pytest.mark.parametrize(
    "content",
    [
        '{"reply":"Unsupported operation","changes":[{"operation":"delete","card_id":"card-1"}]}',
        '{"reply":"Unknown column","changes":[{"operation":"create","column_id":"not-a-column","title":"Invalid"}]}',
        '{"reply":"Unknown column","changes":[{"operation":"rename_column","column_id":"not-a-column","title":"Invalid"}]}',
    ],
)
def test_ai_chat_rejects_invalid_model_output(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    content: str,
) -> None:
    sign_in(client)
    bid = board_id(client)
    original_board = client.get(f"/api/boards/{bid}").json()
    mock_ai_completion(monkeypatch, content)

    response = client.post(
        f"/api/boards/{bid}/chat",
        json={"question": "Change the board."},
    )

    assert response.status_code == 502
    assert client.get(f"/api/boards/{bid}").json() == original_board


def test_ai_chat_reports_missing_key_and_provider_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sign_in(client)
    bid = board_id(client)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    missing_key = client.post(
        f"/api/boards/{bid}/chat",
        json={"question": "Can you help?"},
    )
    assert missing_key.status_code == 503
    assert "GROQ_API_KEY" in missing_key.json()["detail"]

    def fail_completion(**_: object) -> None:
        raise RuntimeError("test-secret")

    monkeypatch.setenv("GROQ_API_KEY", "test-secret")
    monkeypatch.setattr(ai.litellm, "completion", fail_completion)
    provider_failure = client.post(
        f"/api/boards/{bid}/chat",
        json={"question": "Can you help?"},
    )
    assert provider_failure.status_code == 502
    assert "test-secret" not in provider_failure.text
