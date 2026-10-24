from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class FeeSet(Input):
    kind: Literal["first_visit", "follow_up"]
    amount_minor: int = Field(gt=0, le=2_000_000_000)
    reason: str = Field(min_length=3, max_length=200)


class FeeOut(Input):
    model_config = ConfigDict(from_attributes=True)
    kind: Literal["first_visit", "follow_up"]
    amount_minor: int
    occurred_at: datetime


class InvoiceCreate(Input):
    idempotency_key: UUID
    patient_id: UUID
    appointment_id: UUID | None = None
    visit_id: UUID | None = None
    kind: Literal["first_visit", "follow_up"]


class Key(Input):
    idempotency_key: UUID


class PaymentCreate(Key):
    amount_minor: int = Field(gt=0, le=2_000_000_000)


class Adjustment(Input):
    idempotency_key: UUID
    amount_minor: int = Field(ge=-2_000_000_000, le=2_000_000_000)
    reason: str = Field(min_length=3, max_length=200)


class Reason(Input):
    reason: str = Field(min_length=3, max_length=200)


class InvoiceOut(Input):
    id: UUID
    patient_id: UUID
    appointment_id: UUID | None
    visit_id: UUID | None
    kind: Literal["first_visit", "follow_up"]
    status: Literal["draft", "issued", "void"]
    currency: Literal["EGP"] = "EGP"
    base_minor: int
    adjustment_minor: int
    total_minor: int
    paid_minor: int
    balance_minor: int
    created_at: datetime


class PaymentOut(Input):
    id: UUID
    invoice_id: UUID
    amount_minor: int
    currency: Literal["EGP"] = "EGP"
    occurred_at: datetime


class DailySummary(Input):
    day: str
    currency: Literal["EGP"] = "EGP"
    received_minor: int
    reversed_minor: int
    net_minor: int
