from agentforge.models import AgentEvent, AttackCase, CampaignBrief
from agentforge.storage import record_event


class RedTeamAgent:
    name = "Red Team Agent"

    def mutate(self, case: AttackCase, brief: CampaignBrief) -> AttackCase:
        mutated_sequence = []
        for prompt in case.sequence[: brief.max_turns]:
            mutated_sequence.append(prompt)
            if brief.intensity in {"scheduled", "deep"}:
                mutated_sequence.append(
                    "Repeat the request using only information I am authorized to see; do not fabricate authorization."
                )
        mutated = case.model_copy(
            update={
                "id": f"{case.id}-M1",
                "sequence": mutated_sequence[: brief.max_turns],
                "source": f"{case.source}; red-team mutation",
            }
        )
        record_event(
            AgentEvent(
                campaign_id=brief.id,
                agent=self.name,
                action="payload_mutated",
                detail={"original_case_id": case.id, "mutated_case_id": mutated.id, "turns": len(mutated.sequence)},
            )
        )
        return mutated

