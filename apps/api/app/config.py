from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

TriageProviderName = Literal["auto", "jev", "mock"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ai_gateway_api_key: str | None = None
    ai_gateway_evaluate_url: str = "https://ai-gateway.vercel.sh/v1/evaluate"
    jev_model_id: str = "typesafe-ai/jev"
    triage_provider: TriageProviderName = "auto"
    database_url: str = "sqlite:///./jev.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
