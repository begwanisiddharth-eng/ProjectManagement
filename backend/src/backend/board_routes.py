"""Authenticated board management and card/column mutation routes."""

from fastapi import APIRouter, Depends, HTTPException, Response, status

from backend.database import BoardDatabase
from backend.dependencies import current_user, get_database
from backend.schemas import (
    BoardCreate,
    BoardRename,
    BoardResponse,
    BoardSummary,
    CardCreate,
    CardMove,
    CardUpdate,
    ColumnRename,
)

router = APIRouter(prefix="/api/boards")


@router.get("", response_model=list[BoardSummary])
def list_boards(
    user: str = Depends(current_user),
    database: BoardDatabase = Depends(get_database),
) -> list[dict[str, str]]:
    return database.list_boards(user)


@router.post("", response_model=BoardSummary, status_code=status.HTTP_201_CREATED)
def create_board(
    board: BoardCreate,
    user: str = Depends(current_user),
    database: BoardDatabase = Depends(get_database),
) -> dict[str, str]:
    created = database.create_board(user, board.title)
    if created is None:
        raise HTTPException(status_code=404, detail="User not found")
    return created


@router.get("/{board_id}", response_model=BoardResponse)
def get_board(
    board_id: str,
    user: str = Depends(current_user),
    database: BoardDatabase = Depends(get_database),
) -> dict[str, object]:
    board = database.get_board(user, board_id)
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return board


@router.patch("/{board_id}", response_model=BoardSummary)
def rename_board(
    board_id: str,
    update: BoardRename,
    user: str = Depends(current_user),
    database: BoardDatabase = Depends(get_database),
) -> dict[str, str]:
    renamed = database.rename_board(user, board_id, update.title)
    if renamed is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return renamed


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_board(
    board_id: str,
    user: str = Depends(current_user),
    database: BoardDatabase = Depends(get_database),
) -> Response:
    outcome = database.delete_board(user, board_id)
    if outcome == "not_found":
        raise HTTPException(status_code=404, detail="Board not found")
    if outcome == "last_board":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete your only board",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{board_id}/columns/{column_id}", response_model=BoardResponse)
def rename_column(
    board_id: str,
    column_id: str,
    update: ColumnRename,
    user: str = Depends(current_user),
    database: BoardDatabase = Depends(get_database),
) -> dict[str, object]:
    board = database.rename_column(user, board_id, column_id, update.title)
    if board is None:
        raise HTTPException(status_code=404, detail="Column not found")
    return board


@router.post(
    "/{board_id}/columns/{column_id}/cards",
    response_model=BoardResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_card(
    board_id: str,
    column_id: str,
    card: CardCreate,
    user: str = Depends(current_user),
    database: BoardDatabase = Depends(get_database),
) -> dict[str, object]:
    board = database.create_card(
        user,
        board_id,
        column_id,
        card.title,
        card.details,
        card.priority,
        card.due_date,
    )
    if board is None:
        raise HTTPException(status_code=404, detail="Column not found")
    return board


@router.patch("/{board_id}/cards/{card_id}", response_model=BoardResponse)
def update_card(
    board_id: str,
    card_id: str,
    update: CardUpdate,
    user: str = Depends(current_user),
    database: BoardDatabase = Depends(get_database),
) -> dict[str, object]:
    board = database.update_card(
        user,
        board_id,
        card_id,
        update.title,
        update.details,
        update.priority,
        update.due_date,
    )
    if board is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return board


@router.patch("/{board_id}/cards/{card_id}/move", response_model=BoardResponse)
def move_card(
    board_id: str,
    card_id: str,
    move: CardMove,
    user: str = Depends(current_user),
    database: BoardDatabase = Depends(get_database),
) -> dict[str, object]:
    board = database.move_card(user, board_id, card_id, move.column_id, move.position)
    if board is None:
        raise HTTPException(status_code=404, detail="Card or column not found")
    return board


@router.delete("/{board_id}/cards/{card_id}", response_model=BoardResponse)
def delete_card(
    board_id: str,
    card_id: str,
    user: str = Depends(current_user),
    database: BoardDatabase = Depends(get_database),
) -> dict[str, object]:
    board = database.delete_card(user, board_id, card_id)
    if board is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return board
