"""Card priority and due-date fields across the API and AI operations."""

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from backend import ai


def sign_in(client: TestClient) -> str:
    assert (
        client.post(
            "/api/auth/login", json={"username": "user", "password": "password"}
        ).status_code
        == 200
    )
    return client.get("/api/boards").json()[0]["id"]


def mock_ai_completion(monkeypatch: pytest.MonkeyPatch, content: str) -> None:
    def fake_completion(**_: object) -> SimpleNamespace:
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )

    monkeypatch.setenv("GROQ_API_KEY", "test-secret")
    monkeypatch.setattr(ai.litellm, "completion", fake_completion)


def test_seeded_cards_default_to_medium_priority_and_no_due_date(
    client: TestClient,
) -> None:
    bid = sign_in(client)

    card = client.get(f"/api/boards/{bid}").json()["cards"]["card-1"]

    assert card["priority"] == "medium"
    assert card["dueDate"] is None


def test_create_card_with_priority_and_due_date(client: TestClient) -> None:
    bid = sign_in(client)

    response = client.post(
        f"/api/boards/{bid}/columns/col-backlog/cards",
        json={
            "title": "Urgent task",
            "details": "Do this soon.",
            "priority": "high",
            "due_date": "2026-12-31",
        },
    )

    assert response.status_code == 201
    created_id = response.json()["columns"][0]["cardIds"][-1]
    created = response.json()["cards"][created_id]
    assert created["priority"] == "high"
    assert created["dueDate"] == "2026-12-31"


def test_update_card_changes_priority_and_clears_due_date(client: TestClient) -> None:
    bid = sign_in(client)
    created_id = (
        client.post(
            f"/api/boards/{bid}/columns/col-backlog/cards",
            json={
                "title": "Task",
                "details": "Details.",
                "priority": "high",
                "due_date": "2026-01-01",
            },
        )
        .json()["columns"][0]["cardIds"][-1]
    )

    response = client.patch(
        f"/api/boards/{bid}/cards/{created_id}",
        json={"title": "Task", "details": "Details.", "priority": "low"},
    )

    assert response.status_code == 200
    updated = response.json()["cards"][created_id]
    assert updated["priority"] == "low"
    assert updated["dueDate"] is None


def test_api_rejects_invalid_priority_and_due_date(client: TestClient) -> None:
    bid = sign_in(client)

    bad_priority = client.post(
        f"/api/boards/{bid}/columns/col-backlog/cards",
        json={"title": "Task", "details": "Details.", "priority": "urgent"},
    )
    bad_due_date = client.post(
        f"/api/boards/{bid}/columns/col-backlog/cards",
        json={"title": "Task", "details": "Details.", "due_date": "31-12-2026"},
    )

    assert bad_priority.status_code == 422
    assert bad_due_date.status_code == 422


def test_ai_can_create_a_card_with_priority_and_due_date(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bid = sign_in(client)
    mock_ai_completion(
        monkeypatch,
        json.dumps(
            {
                "reply": "Added a high priority launch task.",
                "changes": [
                    {
                        "operation": "create",
                        "column_id": "col-discovery",
                        "title": "Launch prep",
                        "details": "Coordinate the launch.",
                        "priority": "high",
                        "due_date": "2026-11-01",
                    }
                ],
            }
        ),
    )

    response = client.post(
        f"/api/boards/{bid}/chat",
        json={"question": "Add a high priority launch task due 2026-11-01."},
    )

    assert response.status_code == 200
    cards = response.json()["board"]["cards"].values()
    launch = next(card for card in cards if card["title"] == "Launch prep")
    assert launch["priority"] == "high"
    assert launch["dueDate"] == "2026-11-01"


def test_ai_can_edit_only_the_priority_of_a_card(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bid = sign_in(client)
    mock_ai_completion(
        monkeypatch,
        json.dumps(
            {
                "reply": "Bumped the roadmap card to high priority.",
                "changes": [
                    {"operation": "edit", "card_id": "card-1", "priority": "high"}
                ],
            }
        ),
    )

    response = client.post(
        f"/api/boards/{bid}/chat",
        json={"question": "Make the roadmap card high priority."},
    )

    assert response.status_code == 200
    assert response.json()["changed"] is True
    card = response.json()["board"]["cards"]["card-1"]
    assert card["priority"] == "high"
    # The title and details are preserved.
    assert card["title"] == "Align roadmap themes"
    assert card["details"].startswith("Draft quarterly themes")
