"""Authenticated AI chat route that can apply validated board changes."""

from fastapi import APIRouter, Depends, HTTPException

from backend.ai import (
    AIConfigurationError,
    AIProviderError,
    AIResponseError,
    generate_board_assistance,
)
from backend.ai_models import AIChatRequest
from backend.database import BoardDatabase
from backend.dependencies import current_user, get_database
from backend.schemas import AIChatResponse

router = APIRouter(prefix="/api/boards")


@router.post("/{board_id}/chat", response_model=AIChatResponse)
def chat_with_board(
    board_id: str,
    chat: AIChatRequest,
    user: str = Depends(current_user),
    database: BoardDatabase = Depends(get_database),
) -> dict[str, object]:
    board = database.get_board(user, board_id)
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    try:
        result = generate_board_assistance(chat.question, board, chat.history)
    except AIConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (AIProviderError, AIResponseError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    try:
        updated_board = database.apply_ai_changes(user, board_id, result.changes)
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail="The AI proposed invalid board changes; no changes were applied.",
        ) from exc
    if updated_board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return {
        "reply": result.reply,
        "changed": updated_board != board,
        "board": updated_board,
    }
