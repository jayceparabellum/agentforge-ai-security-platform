from collections import Counter

from agentforge.config import Settings
from agentforge.models import AgentEvent, AttackCase, CampaignBrief
from agentforge.storage import record_event


class OrchestratorAgent:
    name = "Orchestrator Agent"

    def __init__(self, settings: Settings):
        self.settings = settings

    def create_brief(self, cases: list[AttackCase], intensity: str = "scheduled") -> CampaignBrief:
        category_counts = Counter(case.category for case in cases)
        categories = [category for category, _ in category_counts.most_common()]
        brief = CampaignBrief(
            target_url=str(self.settings.target_base_url),
            categories=categories,
            intensity=intensity,
            max_cases=min(self.settings.max_campaign_cases, len(cases)),
            max_turns=4 if intensity != "deep" else 8,
            budget_usd=self.settings.campaign_budget_usd,
        )
        record_event(
            AgentEvent(
                campaign_id=brief.id,
                agent=self.name,
                action="campaign_brief_created",
                detail={
                    "target": brief.target_url,
                    "categories": [category.value for category in categories],
                    "budget_usd": brief.budget_usd,
                    "cadence": self.settings.agentforge_campaign_cadence,
                },
            )
        )
        return brief

    def select_cases(self, brief: CampaignBrief, cases: list[AttackCase]) -> list[AttackCase]:
        severity_weighted = sorted(cases, key=lambda case: (-case.severity, case.category.value, case.id))
        selected = severity_weighted[: brief.max_cases]
        record_event(
            AgentEvent(
                campaign_id=brief.id,
                agent=self.name,
                action="cases_selected",
                detail={"case_ids": [case.id for case in selected]},
            )
        )
        return selected

