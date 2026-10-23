from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, BaseModel, ConfigDict, field_validator

CAIRO = ZoneInfo("Africa/Cairo")


class Slot(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    start_at: AwareDatetime
    end_at: AwareDatetime

    @field_validator("start_at", "end_at")
    @classmethod
    def explicit_instant(cls, value):
        # Accept UTC, or an explicit valid Cairo wall time/offset. Never guess a fold.
        local = value.astimezone(CAIRO)
        if value.utcoffset() != timedelta(0) and (
            local.replace(tzinfo=None) != value.replace(tzinfo=None)
            or local.utcoffset() != value.utcoffset()
        ):
            raise ValueError("Use UTC or a valid explicit Cairo offset")
        return value.astimezone(UTC)


class AppointmentCreate(Slot):
    patient_id: UUID
    kind: Literal["first_visit", "follow_up"]


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    patient_id: UUID
    kind: Literal["first_visit", "follow_up"]
    status: Literal["scheduled", "cancelled"]
    start_at: datetime
    end_at: datetime
    created_at: datetime
    updated_at: datetime


class AppointmentPage(BaseModel):
    items: list[AppointmentOut]
    total: int
    page: int
    page_size: int
