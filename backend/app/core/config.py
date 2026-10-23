from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CLINIC_",
        env_file=Path(__file__).resolve().parents[3] / ".env",
        hide_input_in_errors=True,
        extra="ignore",
    )
    database_url: SecretStr
    migration_database_url: SecretStr | None = None
