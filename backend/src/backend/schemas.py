"""Pydantic request and response models for the board API."""

from typing import Annotated, Literal

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
Priority = Literal["low", "medium", "high"]
DueDate = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$")]
ChecklistText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
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
    priority: Priority = "medium"
    due_date: DueDate | None = None


class CardUpdate(BaseModel):
    title: CardTitle
    details: CardDetails = ""
    priority: Priority = "medium"
    due_date: DueDate | None = None


class CardMove(BaseModel):
    column_id: str
    position: int = Field(ge=0)


class ChecklistItemCreate(BaseModel):
    text: ChecklistText


class ChecklistItemUpdate(BaseModel):
    done: bool


class BoardChecklistItem(BaseModel):
    id: str
    text: str
    done: bool


class BoardCard(BaseModel):
    id: str
    title: str
    details: str
    priority: Priority = "medium"
    dueDate: str | None = None
    checklist: list[BoardChecklistItem] = []


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
