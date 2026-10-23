from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.scheduling import SchedulingPolicy


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CLINIC_",
        env_file=Path(__file__).resolve().parents[3] / ".env",
        hide_input_in_errors=True,
        extra="ignore",
    )
    database_url: SecretStr
    migration_database_url: SecretStr | None = None

    appointment_policy: SchedulingPolicy = SchedulingPolicy()

    public_origin: str = "https://clinic.local"

    @field_validator("public_origin")
    @classmethod
    def validate_origin(cls, value):
        from urllib.parse import urlsplit

        url = urlsplit(value)
        if (
            url.scheme != "https"
            or not url.hostname
            or url.username
            or url.password
            or url.path
            or url.query
            or url.fragment
        ):
            raise ValueError("A bare HTTPS origin is required")
        return value
