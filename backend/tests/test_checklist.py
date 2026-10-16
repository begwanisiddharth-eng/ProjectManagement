"""Card checklist items across the board API."""

from fastapi.testclient import TestClient


def sign_in(client: TestClient) -> str:
    assert (
        client.post(
            "/api/auth/login", json={"username": "user", "password": "password"}
        ).status_code
        == 200
    )
    return client.get("/api/boards").json()[0]["id"]


def test_seeded_cards_start_with_an_empty_checklist(client: TestClient) -> None:
    bid = sign_in(client)

    card = client.get(f"/api/boards/{bid}").json()["cards"]["card-1"]

    assert card["checklist"] == []


def test_add_checklist_item_appends_in_order(client: TestClient) -> None:
    bid = sign_in(client)

    client.post(
        f"/api/boards/{bid}/cards/card-1/checklist", json={"text": "First step"}
    )
    response = client.post(
        f"/api/boards/{bid}/cards/card-1/checklist", json={"text": "Second step"}
    )

    assert response.status_code == 201
    checklist = response.json()["cards"]["card-1"]["checklist"]
    assert [item["text"] for item in checklist] == ["First step", "Second step"]
    assert all(item["done"] is False for item in checklist)


def test_toggle_checklist_item_marks_it_done(client: TestClient) -> None:
    bid = sign_in(client)
    item_id = (
        client.post(
            f"/api/boards/{bid}/cards/card-1/checklist", json={"text": "Do it"}
        )
        .json()["cards"]["card-1"]["checklist"][0]["id"]
    )

    response = client.patch(
        f"/api/boards/{bid}/cards/card-1/checklist/{item_id}", json={"done": True}
    )

    assert response.status_code == 200
    assert response.json()["cards"]["card-1"]["checklist"][0]["done"] is True


def test_delete_checklist_item_removes_it(client: TestClient) -> None:
    bid = sign_in(client)
    item_id = (
        client.post(
            f"/api/boards/{bid}/cards/card-1/checklist", json={"text": "Remove me"}
        )
        .json()["cards"]["card-1"]["checklist"][0]["id"]
    )

    response = client.delete(
        f"/api/boards/{bid}/cards/card-1/checklist/{item_id}"
    )

    assert response.status_code == 200
    assert response.json()["cards"]["card-1"]["checklist"] == []


def test_checklist_rejects_blank_text(client: TestClient) -> None:
    bid = sign_in(client)

    response = client.post(
        f"/api/boards/{bid}/cards/card-1/checklist", json={"text": "   "}
    )

    assert response.status_code == 422


def test_checklist_add_on_unknown_card_is_404(client: TestClient) -> None:
    bid = sign_in(client)

    response = client.post(
        f"/api/boards/{bid}/cards/missing-card/checklist", json={"text": "Step"}
    )

    assert response.status_code == 404


def test_checklist_toggle_on_unknown_item_is_404(client: TestClient) -> None:
    bid = sign_in(client)

    response = client.patch(
        f"/api/boards/{bid}/cards/card-1/checklist/missing-item",
        json={"done": True},
    )

    assert response.status_code == 404


def test_deleting_a_card_removes_its_checklist(client: TestClient) -> None:
    bid = sign_in(client)
    client.post(
        f"/api/boards/{bid}/cards/card-1/checklist", json={"text": "Cascade me"}
    )

    client.delete(f"/api/boards/{bid}/cards/card-1")
    board = client.get(f"/api/boards/{bid}").json()

    assert "card-1" not in board["cards"]
    with_items = [
        card for card in board["cards"].values() if card["checklist"]
    ]
    assert with_items == []


def test_checklist_is_scoped_to_its_owner(client: TestClient) -> None:
    bid = sign_in(client)

    # Another user cannot touch this board's cards.
    assert (
        client.post(
            "/api/auth/register",
            json={"username": "mallory", "password": "password123"},
        ).status_code
        == 201
    )
    response = client.post(
        f"/api/boards/{bid}/cards/card-1/checklist", json={"text": "Sneaky"}
    )

    assert response.status_code == 404
