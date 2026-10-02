from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[3] / ".env"

class Settings(BaseSettings):
    app_name: str = "ServiceNow AI Incident Agent"
    environment: str = "development"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./incidents.db"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    confidence_auto_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    confidence_investigate_threshold: float = Field(default=0.60, ge=0.0, le=1.0)
    llm_provider: str = "mock"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    servicenow_instance_url: str | None = None
    servicenow_username: str | None = None
    servicenow_password: str | None = None
    servicenow_mode: str = "mock"
    public_demo_mode: bool = False
    dashboard_api_key: str | None = None
    dashboard_admin_key: str | None = None
    dashboard_viewer_key: str | None = None

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    @model_validator(mode="after")
    def validate_threshold_order(self):
        if self.confidence_investigate_threshold > self.confidence_auto_threshold:
            raise ValueError("Investigation threshold must not exceed autonomous threshold")
        if self.public_demo_mode:
            if self.llm_provider.lower() != "mock" or self.servicenow_mode.lower() != "mock":
                raise ValueError("Public demo mode requires mock LLM and ServiceNow providers")
            if any((self.openai_api_key, self.servicenow_instance_url, self.servicenow_username,
                    self.servicenow_password, self.dashboard_api_key, self.dashboard_admin_key,
                    self.dashboard_viewer_key)):
                raise ValueError("Public demo mode cannot be combined with provider credentials or API keys")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
