from __future__ import annotations

import hashlib
from urllib.parse import urlparse
from typing import Optional, Tuple

import httpx

from agentforge.config import Settings
from agentforge.models import TargetProbeResult, TargetProfile
from agentforge.storage import save_target_probe_results, save_target_profile


CHAT_CANDIDATE_PATHS = (
    "/chat",
    "/w2/chat",
    "/api/copilot/chat",
    "/api/chat",
    "/api/clinical-copilot/chat",
    "/api/ai/chat",
    "/apis/default/api/copilot/chat",
    "/interface/modules/zend_modules/public/ai/chat",
)

GET_CANDIDATE_PATHS = (
    "/",
    "/api",
    "/apis/default/api",
    "/interface/main/tabs/main.php",
    "/swagger",
    "/docs",
)


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
            health = {"url": self.base_url, "status_code": response.status_code, "reachable": response.status_code < 500}
            save_target_profile(self.profile(integration_status="healthy" if health["reachable"] else "unreachable"))
            return health

    def profile(self, integration_status: str = "unknown", notes: str = "") -> TargetProfile:
        base = self.base_url.rstrip("/")
        return TargetProfile(
            base_url=base,
            chat_path=self.settings.target_chat_path,
            allowlisted=base in self.settings.allowlist,
            host=self.host,
            integration_status=integration_status,
            notes=notes,
        )

    async def probe(self) -> dict:
        results: list[TargetProbeResult] = []
        async with httpx.AsyncClient(
            timeout=self.settings.request_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "AgentForge/0.1 target-probe"},
        ) as client:
            for path in GET_CANDIDATE_PATHS:
                results.append(await self._probe_get(client, path))
            for path in self._chat_candidates():
                results.append(await self._probe_post(client, path))
        likely = [result for result in results if result.likely_chat_endpoint]
        reachable = [result for result in results if result.reachable]
        status = "healthy" if likely else ("partial" if reachable else "unreachable")
        notes = (
            "Likely chat endpoint found."
            if likely
            else "Target is reachable, but no candidate chat endpoint accepted the AgentForge probe."
            if reachable
            else "Target was not reachable during probe."
        )
        profile = self.profile(integration_status=status, notes=notes)
        save_target_profile(profile)
        save_target_probe_results(results)
        return {
            "profile": profile.model_dump(mode="json"),
            "probe_count": len(results),
            "likely_chat_paths": [result.path for result in likely],
            "reachable_paths": [result.path for result in reachable],
            "results": [result.model_dump(mode="json") for result in results],
        }

    async def _probe_get(self, client: httpx.AsyncClient, path: str) -> TargetProbeResult:
        try:
            response = await client.get(f"{self.base_url}{path}")
            return TargetProbeResult(
                id=self._probe_id("GET", path),
                target_url=self.base_url,
                path=path,
                method="GET",
                status_code=response.status_code,
                reachable=response.status_code < 500,
                response_excerpt=response.text[:300],
            )
        except Exception as exc:
            return TargetProbeResult(
                id=self._probe_id("GET", path),
                target_url=self.base_url,
                path=path,
                method="GET",
                error=f"{type(exc).__name__}: {exc}",
            )

    async def _probe_post(self, client: httpx.AsyncClient, path: str) -> TargetProbeResult:
        probe_message = "AgentForge target probe. Reply with a safe readiness message."
        try:
            response = await self._post_prompt(client, path, probe_message)
            content_type = response.headers.get("content-type", "")
            excerpt = response.text[:300]
            likely = response.status_code < 400 and (
                "json" in content_type or "assistant" in excerpt.lower() or "message" in excerpt.lower()
            )
            return TargetProbeResult(
                id=self._probe_id("POST", path),
                target_url=self.base_url,
                path=path,
                method="POST",
                status_code=response.status_code,
                reachable=response.status_code < 500,
                likely_chat_endpoint=likely,
                response_excerpt=excerpt,
            )
        except Exception as exc:
            return TargetProbeResult(
                id=self._probe_id("POST", path),
                target_url=self.base_url,
                path=path,
                method="POST",
                error=f"{type(exc).__name__}: {exc}",
            )

    def _chat_candidates(self) -> list[str]:
        candidates = [self.settings.target_chat_path]
        candidates.extend(path for path in CHAT_CANDIDATE_PATHS if path not in candidates)
        return candidates

    def _probe_id(self, method: str, path: str) -> str:
        digest = hashlib.sha256(f"{self.base_url}:{method}:{path}".encode("utf-8")).hexdigest()[:10].upper()
        return f"TARGET-{method}-{digest}"

    async def _post_prompt(
        self,
        client: httpx.AsyncClient,
        path: str,
        prompt: str,
        transcript: Optional[list[dict[str, str]]] = None,
    ) -> httpx.Response:
        if path == "/chat":
            return await client.post(f"{self.base_url}{path}", json={"message": prompt, "username": "mchen"})
        if path == "/w2/chat":
            return await client.post(f"{self.base_url}{path}", data={"question": prompt, "patient_id": "1001"})
        return await client.post(
            f"{self.base_url}{path}",
            json={
                "messages": transcript or [{"role": "user", "content": prompt}],
                "source": "agentforge",
                "safety_mode": "evaluation",
            },
        )

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
                    response = await self._post_prompt(client, self.settings.target_chat_path, prompt, transcript)
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
