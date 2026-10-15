import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend import ai
from backend.ai_models import AIChatMessage, AIChatRequest


def completion_response(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def test_request_completion_uses_the_configured_model_and_server_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_completion(**kwargs: object) -> SimpleNamespace:
        calls.append(kwargs)
        return completion_response("42")

    monkeypatch.setenv("GROQ_API_KEY", "test-secret")
    monkeypatch.setattr(ai.litellm, "completion", fake_completion)

    content = ai.request_completion(
        [{"role": "user", "content": "What is 6 times 7?"}],
        json_response=True,
    )

    assert content == "42"
    assert calls == [
        {
            "model": "groq/openai/gpt-oss-120b",
            "messages": [{"role": "user", "content": "What is 6 times 7?"}],
            "api_key": "test-secret",
            "response_format": {"type": "json_object"},
        }
    ]


def test_request_completion_requires_a_server_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(ai.AIConfigurationError, match="GROQ_API_KEY"):
        ai.request_completion([{"role": "user", "content": "Hi"}])


def test_request_completion_reports_provider_failures_without_leaking_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_completion(**_: object) -> None:
        raise RuntimeError("provider echoed test-secret")

    monkeypatch.setenv("GROQ_API_KEY", "test-secret")
    monkeypatch.setattr(ai.litellm, "completion", fail_completion)

    with pytest.raises(ai.AIProviderError) as error:
        ai.request_completion([{"role": "user", "content": "Hi"}])

    assert str(error.value) == "The Groq provider request failed."
    assert "test-secret" not in str(error.value)


def test_generate_board_assistance_sends_board_and_recent_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_completion(**kwargs: object) -> SimpleNamespace:
        calls.append(kwargs)
        return completion_response('{"reply":"I can help.","changes":[]}')

    monkeypatch.setenv("GROQ_API_KEY", "test-secret")
    monkeypatch.setattr(ai.litellm, "completion", fake_completion)
    history = [
        AIChatMessage(role="user", content="Please review this card."),
        AIChatMessage(role="assistant", content="I will review it."),
    ]
    board = {
        "columns": [{"id": "todo", "title": "To do", "cardIds": ["card-1"]}],
        "cards": {
            "card-1": {
                "id": "card-1",
                "title": "Prepare launch",
                "details": "Finalize the release checklist.",
            }
        },
    }

    result = ai.generate_board_assistance(
        "Move the launch card to done.",
        board,
        history,
    )

    messages = calls[0]["messages"]
    assert isinstance(messages, list)
    assert messages[0]["role"] == "system"
    assert "Prepare launch" in messages[0]["content"]
    assert messages[1:] == [
        {"role": "user", "content": "Please review this card."},
        {"role": "assistant", "content": "I will review it."},
        {"role": "user", "content": "Move the launch card to done."},
    ]
    assert "test-secret" not in json.dumps(messages)
    assert result.reply == "I can help."
    assert result.changes == []


@pytest.mark.parametrize(
    "content",
    [
        "not JSON",
        '{"changes":[]}',
        '{"reply":"No changes.","changes":[{"operation":"delete","card_id":"card-1"}]}',
        '{"reply":"No changes.","changes":[{"operation":"edit","card_id":"card-1"}]}',
        '{"reply":"No changes.","changes":[{"operation":"create","column_id":"todo","title":"  "}]}',
        '{"reply":"No changes.","changes":[{"operation":"move","card_id":"card-1","column_id":"todo","position":-1}]}',
    ],
)
def test_generate_board_assistance_rejects_malformed_or_unsupported_responses(
    monkeypatch: pytest.MonkeyPatch,
    content: str,
) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-secret")
    monkeypatch.setattr(
        ai.litellm,
        "completion",
        lambda **_: completion_response(content),
    )

    with pytest.raises(ai.AIResponseError):
        ai.generate_board_assistance(
            "Please help.",
            {"columns": [], "cards": {}},
            [],
        )


def test_chat_request_rejects_blank_or_excess_history() -> None:
    with pytest.raises(ValidationError):
        AIChatRequest(question="  ")
    with pytest.raises(ValidationError):
        AIChatRequest(
            question="Help",
            history=[
                {"role": "user", "content": str(index)}
                for index in range(21)
            ],
        )
