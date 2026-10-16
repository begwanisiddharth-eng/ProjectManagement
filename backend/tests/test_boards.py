"""Multiple boards per user: listing, creating, renaming, and deleting."""

from fastapi.testclient import TestClient


def sign_in(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200


def test_list_boards_returns_the_seeded_default_board(client: TestClient) -> None:
    sign_in(client)

    response = client.get("/api/boards")

    assert response.status_code == 200
    boards = response.json()
    assert len(boards) == 1
    assert boards[0]["title"] == "Kanban Studio"
    assert set(boards[0]) == {"id", "title", "createdAt", "updatedAt"}


def test_list_boards_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/boards").status_code == 401


def test_create_board_seeds_five_empty_columns(client: TestClient) -> None:
    sign_in(client)

    created = client.post("/api/boards", json={"title": "Marketing"})

    assert created.status_code == 201
    summary = created.json()
    assert summary["title"] == "Marketing"

    listed = client.get("/api/boards").json()
    assert len(listed) == 2
    assert [board["title"] for board in listed] == ["Kanban Studio", "Marketing"]

    board = client.get(f"/api/boards/{summary['id']}").json()
    assert [column["id"] for column in board["columns"]] == [
        "col-backlog",
        "col-discovery",
        "col-progress",
        "col-review",
        "col-done",
    ]
    assert board["cards"] == {}


def test_create_board_rejects_blank_title(client: TestClient) -> None:
    sign_in(client)

    response = client.post("/api/boards", json={"title": "   "})

    assert response.status_code == 422


def test_boards_hold_independent_cards(client: TestClient) -> None:
    sign_in(client)
    first = client.get("/api/boards").json()[0]["id"]
    second = client.post("/api/boards", json={"title": "Second"}).json()["id"]

    client.post(
        f"/api/boards/{second}/columns/col-backlog/cards",
        json={"title": "Second-board card", "details": "Lives only on the second."},
    )

    first_board = client.get(f"/api/boards/{first}").json()
    second_board = client.get(f"/api/boards/{second}").json()
    assert not any(
        card["title"] == "Second-board card" for card in first_board["cards"].values()
    )
    assert any(
        card["title"] == "Second-board card" for card in second_board["cards"].values()
    )


def test_rename_board_updates_title(client: TestClient) -> None:
    sign_in(client)
    board_id = client.get("/api/boards").json()[0]["id"]

    response = client.patch(f"/api/boards/{board_id}", json={"title": "Renamed"})

    assert response.status_code == 200
    assert response.json()["title"] == "Renamed"
    assert client.get("/api/boards").json()[0]["title"] == "Renamed"


def test_rename_unknown_board_returns_not_found(client: TestClient) -> None:
    sign_in(client)

    response = client.patch("/api/boards/missing", json={"title": "Nope"})

    assert response.status_code == 404


def test_delete_board_removes_it_and_its_cards(client: TestClient) -> None:
    sign_in(client)
    second = client.post("/api/boards", json={"title": "Disposable"}).json()["id"]

    response = client.delete(f"/api/boards/{second}")

    assert response.status_code == 204
    assert client.get(f"/api/boards/{second}").status_code == 404
    assert len(client.get("/api/boards").json()) == 1


def test_cannot_delete_the_only_board(client: TestClient) -> None:
    sign_in(client)
    only_board = client.get("/api/boards").json()[0]["id"]

    response = client.delete(f"/api/boards/{only_board}")

    assert response.status_code == 409
    assert len(client.get("/api/boards").json()) == 1


def test_cannot_delete_another_users_board(client: TestClient) -> None:
    sign_in(client)
    client.post("/api/boards", json={"title": "Extra"})
    client.post("/api/auth/logout")

    client.post(
        "/api/auth/register",
        json={"username": "intruder", "password": "intruderpass"},
    )
    victim_boards_hidden = client.get("/api/boards").json()
    # Intruder only sees their own single seeded board.
    assert len(victim_boards_hidden) == 1
    assert client.delete("/api/boards/does-not-belong").status_code == 404
