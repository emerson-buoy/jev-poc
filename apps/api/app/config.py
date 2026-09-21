from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

TriageProviderName = Literal["auto", "typesafe", "jev", "mock"]


class Settings(BaseSettings):
    # Later files win: apps/api/.env overrides a repo-root .env.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    typesafe_api_key: str | None = None
    typesafe_base_url: str = "https://api.typesafe.ai/v1"
    typesafe_model_id: str = "jev-latest"
    ai_gateway_api_key: str | None = None
    ai_gateway_evaluate_url: str = "https://ai-gateway.vercel.sh/v1/evaluate"
    jev_model_id: str = "typesafe-ai/jev"
    triage_provider: TriageProviderName = "auto"
    database_url: str = "sqlite:///./jev.db"
    triage_max_attempts: int = 3
    triage_deadline_seconds: float = 10.0
    triage_connect_timeout_seconds: float = 3.0
    triage_read_timeout_seconds: float = 8.0
    triage_circuit_failures: int = 5
    triage_circuit_cooldown_seconds: float = 30.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
