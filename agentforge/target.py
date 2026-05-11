from __future__ import annotations

from urllib.parse import urlparse
from typing import Optional, Tuple

import httpx

from agentforge.config import Settings


class TargetClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = str(settings.target_base_url).rstrip("/")
        self.chat_url = f"{self.base_url}{settings.target_chat_path}"
        self._assert_allowed()

    def _assert_allowed(self) -> None:
        base = self.base_url.rstrip("/")
        if base not in self.settings.allowlist:
            raise ValueError(f"Target {base} is not in TARGET_ALLOWLIST")

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds, follow_redirects=True) as client:
            response = await client.get(self.base_url)
            return {"url": self.base_url, "status_code": response.status_code, "reachable": response.status_code < 500}

    async def send_sequence(self, sequence: list[str]) -> Tuple[Optional[int], str, Optional[str]]:
        transcript: list[dict[str, str]] = []
        last_status: Optional[int] = None
        last_excerpt = ""
        try:
            async with httpx.AsyncClient(
                timeout=self.settings.request_timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": "AgentForge/0.1 authorized-adversarial-eval"},
            ) as client:
                for prompt in sequence:
                    transcript.append({"role": "user", "content": prompt})
                    response = await client.post(
                        self.chat_url,
                        json={"messages": transcript, "source": "agentforge", "safety_mode": "evaluation"},
                    )
                    last_status = response.status_code
                    last_excerpt = response.text[:1200]
                    transcript.append({"role": "assistant", "content": last_excerpt})
                return last_status, last_excerpt, None
        except httpx.HTTPStatusError as exc:
            return exc.response.status_code, exc.response.text[:1200], str(exc)
        except Exception as exc:
            return last_status, last_excerpt, f"{type(exc).__name__}: {exc}"

    @property
    def host(self) -> str:
        return urlparse(self.base_url).netloc
