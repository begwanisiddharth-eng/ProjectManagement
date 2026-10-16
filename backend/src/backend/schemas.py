"""Pydantic request and response models for the board API."""

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

Username = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=3, max_length=50)
]
Password = Annotated[str, StringConstraints(min_length=8, max_length=200)]
BoardTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
CardTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
CardDetails = Annotated[str, StringConstraints(max_length=4000)]
RequiredCardDetails = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: Username
    password: Password


class BoardCreate(BaseModel):
    title: BoardTitle


class BoardRename(BaseModel):
    title: BoardTitle


class BoardSummary(BaseModel):
    id: str
    title: str
    createdAt: str
    updatedAt: str


class ColumnRename(BaseModel):
    title: BoardTitle


class CardCreate(BaseModel):
    title: CardTitle
    details: RequiredCardDetails


class CardUpdate(BaseModel):
    title: CardTitle
    details: CardDetails = ""


class CardMove(BaseModel):
    column_id: str
    position: int = Field(ge=0)


class BoardCard(BaseModel):
    id: str
    title: str
    details: str


class BoardColumn(BaseModel):
    id: str
    title: str
    cardIds: list[str]


class BoardResponse(BaseModel):
    columns: list[BoardColumn]
    cards: dict[str, BoardCard]


class AIChatResponse(BaseModel):
    reply: str
    changed: bool
    board: BoardResponse
