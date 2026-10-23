from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PatientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    full_name: str = Field(min_length=2, max_length=200)
    phone: str = Field(min_length=5, max_length=32, pattern=r"^\+?[0-9 ()-]+$")
    birth_date: date | None = None
    confirm_duplicate: bool = False

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, value):
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("A name is required")
        return value

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, value):
        return value.strip()

    @field_validator("birth_date")
    @classmethod
    def valid_birth_date(cls, value):
        if value and value > date.today():
            raise ValueError("Future birth date is invalid")
        return value


class PatientPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    full_name: str | None = Field(default=None, min_length=2, max_length=200)
    phone: str | None = Field(
        default=None, min_length=5, max_length=32, pattern=r"^\+?[0-9 ()-]+$"
    )
    birth_date: date | None = None

    @model_validator(mode="after")
    def check(self):
        if (
            not self.model_fields_set
            or ("full_name" in self.model_fields_set and self.full_name is None)
            or ("phone" in self.model_fields_set and self.phone is None)
        ):
            raise ValueError("At least one valid field is required")
        if self.full_name is not None:
            self.full_name = " ".join(self.full_name.split())
            if len(self.full_name) < 2:
                raise ValueError("A name is required")
        if self.phone is not None:
            self.phone = self.phone.strip()
        if self.birth_date and self.birth_date > date.today():
            raise ValueError("Future birth date is invalid")
        return self


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    full_name: str
    phone: str
    birth_date: date | None
    active: bool
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class PatientPage(BaseModel):
    items: list[PatientOut]
    total: int
    page: int
    page_size: int
