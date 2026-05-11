import json
from pathlib import Path

from agentforge.models import AgentEvent, AttackCase
from agentforge.storage import record_event


class ThreatIntelAgent:
    name = "Threat Intelligence Agent"

    def load_seed_cases(self, campaign_id: str) -> list[AttackCase]:
        path = Path(__file__).resolve().parents[1] / "data" / "seed_cases.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        cases = [AttackCase.model_validate(item) for item in data]
        record_event(
            AgentEvent(
                campaign_id=campaign_id,
                agent=self.name,
                action="seed_templates_loaded",
                detail={"count": len(cases), "sources": sorted({case.source for case in cases})},
            )
        )
        return cases

