from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Question = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Reply = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]
CardTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
CardDetails = Annotated[str, StringConstraints(max_length=4000)]
ColumnTitle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Priority = Literal["low", "medium", "high"]
DueDate = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$")]
RequiredCardDetails = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateCardChange(StrictModel):
    operation: Literal["create"]
    column_id: str
    title: CardTitle
    details: RequiredCardDetails
    priority: Priority = "medium"
    due_date: DueDate | None = None


class EditCardChange(StrictModel):
    operation: Literal["edit"]
    card_id: str
    title: CardTitle | None = None
    details: CardDetails | None = None
    priority: Priority | None = None
    due_date: DueDate | None = None

    @model_validator(mode="after")
    def require_an_updated_field(self) -> "EditCardChange":
        if (
            self.title is None
            and self.details is None
            and self.priority is None
            and self.due_date is None
        ):
            raise ValueError("An edit must include at least one updated field.")
        return self


class MoveCardChange(StrictModel):
    operation: Literal["move"]
    card_id: str
    column_id: str
    position: int = Field(ge=0)


class RenameColumnChange(StrictModel):
    operation: Literal["rename_column"]
    column_id: str
    title: ColumnTitle


BoardChange: TypeAlias = Annotated[
    CreateCardChange | EditCardChange | MoveCardChange | RenameColumnChange,
    Field(discriminator="operation"),
]


class AIChatMessage(StrictModel):
    role: Literal["user", "assistant"]
    content: Annotated[str, StringConstraints(min_length=1, max_length=2000)]


class AIChatRequest(StrictModel):
    question: Question
    history: list[AIChatMessage] = Field(default_factory=list, max_length=20)


class AIResult(StrictModel):
    reply: Reply
    changes: list[BoardChange] = Field(default_factory=list, max_length=10)
