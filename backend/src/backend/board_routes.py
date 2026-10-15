"""Authenticated board read and card/column mutation routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.database import BoardDatabase
from backend.dependencies import current_user, get_database
from backend.schemas import BoardResponse, CardCreate, CardMove, CardUpdate, ColumnRename

router = APIRouter(prefix="/api/board")


@router.get("", response_model=BoardResponse)
def get_board(
    user: str = Depends(current_user),
    database: BoardDatabase = Depends(get_database),
) -> dict[str, object]:
    board = database.get_board(user)
    if board is None:
        raise HTTPException(status_code=404, detail="Board not found")
    return board


@router.patch("/columns/{column_id}", response_model=BoardResponse)
def rename_column(
    column_id: str,
    update: ColumnRename,
    user: str = Depends(current_user),
    database: BoardDatabase = Depends(get_database),
) -> dict[str, object]:
    board = database.rename_column(user, column_id, update.title)
    if board is None:
        raise HTTPException(status_code=404, detail="Column not found")
    return board


@router.post(
    "/columns/{column_id}/cards",
    response_model=BoardResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_card(
    column_id: str,
    card: CardCreate,
    user: str = Depends(current_user),
    database: BoardDatabase = Depends(get_database),
) -> dict[str, object]:
    board = database.create_card(user, column_id, card.title, card.details)
    if board is None:
        raise HTTPException(status_code=404, detail="Column not found")
    return board


@router.patch("/cards/{card_id}", response_model=BoardResponse)
def update_card(
    card_id: str,
    update: CardUpdate,
    user: str = Depends(current_user),
    database: BoardDatabase = Depends(get_database),
) -> dict[str, object]:
    board = database.update_card(user, card_id, update.title, update.details)
    if board is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return board


@router.patch("/cards/{card_id}/move", response_model=BoardResponse)
def move_card(
    card_id: str,
    move: CardMove,
    user: str = Depends(current_user),
    database: BoardDatabase = Depends(get_database),
) -> dict[str, object]:
    board = database.move_card(user, card_id, move.column_id, move.position)
    if board is None:
        raise HTTPException(status_code=404, detail="Card or column not found")
    return board


@router.delete("/cards/{card_id}", response_model=BoardResponse)
def delete_card(
    card_id: str,
    user: str = Depends(current_user),
    database: BoardDatabase = Depends(get_database),
) -> dict[str, object]:
    board = database.delete_card(user, card_id)
    if board is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return board
