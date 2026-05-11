import asyncio

from agentforge.agents import DocumentationAgent, JudgeAgent, OrchestratorAgent, RedTeamAgent, ThreatIntelAgent
from agentforge.config import get_settings
from agentforge.models import AgentEvent, AttackResult
from agentforge.storage import record_event, save_attack_result, save_report, save_verdict
from agentforge.target import TargetClient


def estimate_tokens(sequence: list[str], response: str) -> int:
    return max(1, sum(len(item.split()) for item in sequence) + len(response.split()))


def estimate_cost(tokens: int) -> float:
    return round(tokens / 1_000_000 * 0.50, 6)


async def run_campaign(intensity: str = "scheduled") -> dict:
    settings = get_settings()
    threat_intel = ThreatIntelAgent()
    orchestrator = OrchestratorAgent(settings)
    red_team = RedTeamAgent()
    judge = JudgeAgent()
    docs = DocumentationAgent()
    target = TargetClient(settings)

    seed_cases = threat_intel.load_seed_cases("bootstrap")
    brief = orchestrator.create_brief(seed_cases, intensity=intensity)
    cases = orchestrator.select_cases(brief, seed_cases)
    health = await target.health()
    record_event(AgentEvent(campaign_id=brief.id, agent="Target System", action="health_checked", detail=health))

    results = []
    total_cost = 0.0
    for case in cases:
        mutated = red_team.mutate(case, brief)
        status_code, response_excerpt, error = await target.send_sequence(mutated.sequence)
        observed = (
            "Live target response captured for independent judging."
            if not error
            else "Configured target did not expose the expected chat API path during this run."
        )
        tokens = estimate_tokens(mutated.sequence, response_excerpt)
        cost = estimate_cost(tokens)
        total_cost += cost
        result = AttackResult(
            case_id=case.id,
            campaign_id=brief.id,
            category=case.category,
            payload_sequence=mutated.sequence,
            target_status_code=status_code,
            target_response_excerpt=response_excerpt,
            transport_error=error,
            observed_behavior=observed,
            token_estimate=tokens,
            cost_estimate_usd=cost,
        )
        save_attack_result(result)
        verdict = judge.evaluate(result, case.expected_safe_behavior, case.severity)
        save_verdict(verdict)
        report = None
        if verdict.verdict in {"fail", "partial"}:
            report = docs.create_report(case, result, verdict)
            save_report(report)
        results.append({"case": case.id, "verdict": verdict.verdict, "report": report.id if report else None})
        if total_cost > settings.campaign_budget_usd * 1.2:
            record_event(
                AgentEvent(
                    campaign_id=brief.id,
                    agent=orchestrator.name,
                    action="budget_halt",
                    detail={"cost_estimate_usd": total_cost, "budget_usd": settings.campaign_budget_usd},
                )
            )
            break

    return {
        "campaign_id": brief.id,
        "target": brief.target_url,
        "target_health": health,
        "cases_run": len(results),
        "estimated_cost_usd": round(total_cost, 6),
        "results": results,
    }


def run_campaign_sync(intensity: str = "scheduled") -> dict:
    return asyncio.run(run_campaign(intensity=intensity))

