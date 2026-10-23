from datetime import time

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SchedulingPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_visit_minutes: int = Field(default=30, ge=5, le=240)
    follow_up_minutes: int = Field(default=15, ge=5, le=240)
    opens: time = time(9)
    closes: time = time(17)
    weekdays: list[int] = Field(default_factory=lambda: [0, 1, 2, 3, 5, 6])

    @model_validator(mode="after")
    def validate_hours(self):
        if (
            self.opens.tzinfo
            or self.closes.tzinfo
            or self.opens >= self.closes
            or self.opens.second
            or self.closes.second
            or self.opens.microsecond
            or self.closes.microsecond
            or not self.weekdays
            or any(day not in range(7) for day in self.weekdays)
        ):
            raise ValueError("Invalid local working hours")
        return self
