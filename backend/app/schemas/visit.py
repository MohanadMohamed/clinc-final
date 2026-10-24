from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class VisitCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    patient_id: UUID
    appointment_id: UUID | None = None
    neurological_note: str = Field(default="", max_length=20000)
    psychiatric_note: str = Field(default="", max_length=20000)
    follow_up_plan: str = Field(default="", max_length=20000)


class VisitPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    expected_revision: int = Field(ge=1)
    neurological_note: str | None = Field(default=None, max_length=20000)
    psychiatric_note: str | None = Field(default=None, max_length=20000)
    follow_up_plan: str | None = Field(default=None, max_length=20000)

    @model_validator(mode="after")
    def changed_content(self):
        fields = self.model_fields_set & {
            "neurological_note",
            "psychiatric_note",
            "follow_up_plan",
        }
        if not fields or any(getattr(self, field) is None for field in fields):
            raise ValueError("At least one non-null note field is required")
        return self


class VisitFinalize(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    expected_revision: int = Field(ge=1)


class AddendumCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    body: str = Field(min_length=1, max_length=20000)

    @model_validator(mode="after")
    def not_blank(self):
        if not self.body.strip():
            raise ValueError("Addendum cannot be blank")
        return self


class VisitSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    patient_id: UUID
    appointment_id: UUID | None
    status: Literal["draft", "finalized"]
    revision: int
    created_at: datetime
    updated_at: datetime
    finalized_at: datetime | None


class VisitOut(VisitSummary):
    neurological_note: str
    psychiatric_note: str
    follow_up_plan: str


class VisitPage(BaseModel):
    items: list[VisitSummary]
    total: int
    page: int
    page_size: int


class VisitSearch(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    patient_id: UUID | None = None
    search: str = Field(min_length=1, max_length=100)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class RevisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    revision: int
    actor_id: UUID
    event: Literal["created", "updated", "finalized"]
    neurological_note: str
    psychiatric_note: str
    follow_up_plan: str
    occurred_at: datetime


class AddendumOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    actor_id: UUID
    body: str
    occurred_at: datetime


class VisitHistory(BaseModel):
    revisions: list[RevisionOut]
    addenda: list[AddendumOut]
