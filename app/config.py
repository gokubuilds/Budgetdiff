from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "BudgetDiff"
    environment: str = "local"  # local | ci | production | test
    database_url: str = "sqlite:///./data/usage.db"

    # LLM Settings
    gemini_api_key: str = ""
    primary_model: str = Field(
        default="gemini-1.5-pro",
        validation_alias=AliasChoices("PRIMARY_MODEL", "primary_model"),
    )
    fallback_model: str = Field(
        default="gemini-1.5-flash",
        validation_alias=AliasChoices(
            "LLM_FALLBACK_MODEL", "FALLBACK_MODEL", "fallback_model", "llm_fallback_model"
        ),
    )
    llm_timeout_seconds: float = 10.0
    llm_max_retries: int = 2

    @property
    def llm_fallback_model(self) -> str:
        return self.fallback_model


@lru_cache
def get_settings() -> Settings:
    return Settings()

