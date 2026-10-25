import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr, model_validator
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

    env: Literal["development", "production"] = "production"
    deployment: Literal["clinic_lan", "render_demo"] = "clinic_lan"
    demo_public_enabled: bool = False
    public_origin: str = "https://clinic.local"

    @model_validator(mode="after")
    def validate_origin(self):
        url = urlsplit(self.public_origin)
        if (
            url.scheme not in ("http", "https")
            or not url.hostname
            or url.username
            or url.password
            or url.path
            or url.query
            or url.fragment
            or not url.netloc
        ):
            raise ValueError("A bare public origin is required")
        try:
            _ = url.port
        except ValueError as error:
            raise ValueError("A valid public origin port is required") from error
        if url.scheme == "http" and (
            self.env != "development"
            or url.hostname not in {"127.0.0.1", "localhost", "::1"}
        ):
            raise ValueError("HTTP is allowed only for explicit loopback development")
        on_render = os.environ.get("RENDER") == "true"
        if on_render and (self.env != "production" or self.deployment != "render_demo"):
            raise ValueError("Render requires explicit production demo configuration")
        if self.deployment == "render_demo" and (
            self.env != "production" or not on_render or url.scheme != "https"
        ):
            raise ValueError("Render demo requires the Render platform and HTTPS")
        render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
        if (
            self.deployment == "render_demo"
            and render_host
            and url.netloc != render_host
        ):
            raise ValueError("The demo origin must match its Render hostname")
        if self.demo_public_enabled and self.deployment != "render_demo":
            raise ValueError("Demo exposure flag is valid only for Render demo")
        return self

    @property
    def loopback_http(self) -> bool:
        return self.env == "development" and self.public_origin.startswith("http://")
