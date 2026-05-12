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
    threat_intel_max_generated_cases: int = Field(default=12, ge=1, le=100)
    nvd_keyword_query: str = "LLM AI machine learning"
    openrouter_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    red_team_provider: str = "OpenRouter"
    red_team_model: str = "meta-llama/llama-3.3-70b-instruct"
    judge_provider: str = "Anthropic direct"
    judge_model: str = "claude-haiku-4-5"
    documentation_provider: str = "OpenRouter or direct"
    doc_model: str = "meta-llama/llama-3.3-70b-instruct"
    local_fallback_provider: str = "Ollama + Dolphin-Llama3"
    request_timeout_seconds: float = 12.0
    max_campaign_cases: int = Field(default=9, ge=1, le=100)

    @property
    def allowlist(self) -> List[str]:
        return [item.strip().rstrip("/") for item in self.target_allowlist.split(",") if item.strip()]

    @property
    def provider_routes(self) -> dict:
        return {
            "Red Team Agent": {
                "provider": self.red_team_provider,
                "model": self.red_team_model,
                "data_path": "synthetic attack payloads only; no PHI expected",
                "rationale": "OpenRouter enables model swapping on the offensive side, which is exactly the Red Team workflow.",
            },
            "Judge Agent": {
                "provider": self.judge_provider,
                "model": self.judge_model,
                "data_path": "target responses; may contain PHI if an attack succeeds",
                "rationale": "Direct Anthropic path avoids an aggregator hop for potentially sensitive target responses.",
            },
            "Documentation Agent": {
                "provider": self.documentation_provider,
                "model": self.doc_model,
                "data_path": "already-flagged exploit metadata and structured verdicts",
                "rationale": "Documentation can use OpenRouter for cost/flexibility or a direct provider if compliance requirements tighten.",
            },
            "Local fallback": {
                "provider": self.local_fallback_provider,
                "model": "Dolphin-Llama3",
                "data_path": "offline/local smoke and development runs",
                "rationale": "Keeps low-cost and air-gapped testing available without changing the agent graph.",
            },
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
