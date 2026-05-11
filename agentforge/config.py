from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    target_base_url: AnyHttpUrl = "https://openemr-js46.onrender.com"
    target_chat_path: str = "/api/copilot/chat"
    target_allowlist: str = "https://openemr-js46.onrender.com"
    campaign_budget_usd: float = 2.50
    agentforge_campaign_cadence: str = "weekly"
    database_path: str = "agentforge.db"
    openrouter_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    red_team_model: str = "meta-llama/llama-3.3-70b-instruct"
    judge_model: str = "claude-haiku-4-5"
    doc_model: str = "meta-llama/llama-3.3-70b-instruct"
    request_timeout_seconds: float = 12.0
    max_campaign_cases: int = Field(default=9, ge=1, le=100)

    @property
    def allowlist(self) -> List[str]:
        return [item.strip().rstrip("/") for item in self.target_allowlist.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
