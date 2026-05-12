from __future__ import annotations

from typing import Optional

from agentforge.agents import DocumentationAgent, JudgeAgent, OrchestratorAgent, RedTeamAgent, ThreatIntelAgent
from agentforge.config import Settings, get_settings
from agentforge.models import AgentEvent, AgentTransition, AttackResult, MultiAgentRunSummary, TokenBudgetEntry
from agentforge.storage import (
    record_agent_transition,
    record_budget_entry,
    record_event,
    save_attack_result,
    save_report,
    save_verdict,
)
from agentforge.target import TargetClient


GRAPH_VERSION = "layer2-langgraph-provider-routes-v2"


def estimate_tokens(sequence: list[str], response: str) -> int:
    return max(1, sum(len(item.split()) for item in sequence) + len(response.split()))


def estimate_cost(tokens: int) -> float:
    return round(tokens / 1_000_000 * 0.50, 6)


def budget_threshold(cost: float, budget: float) -> str:
    if cost > budget * 1.2:
        return "halt"
    if cost >= budget * 0.8:
        return "warning"
    return "normal"


class MultiAgentCore:
    """Typed Layer 2 coordinator for the AgentForge agent graph."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.threat_intel = ThreatIntelAgent(self.settings)
        self.orchestrator = OrchestratorAgent(self.settings)
        self.red_team = RedTeamAgent()
        self.judge = JudgeAgent()
        self.docs = DocumentationAgent()
        self.target = TargetClient(self.settings)
        self.provider_routes = self.settings.provider_routes
        self.nodes_visited: list[str] = []
        self.transition_count = 0

    async def run_campaign(self, intensity: str = "scheduled") -> dict:
        self.nodes_visited = []
        self.transition_count = 0
        seed_cases = self.threat_intel.load_seed_cases("bootstrap")
        brief = self.orchestrator.create_brief(seed_cases, intensity=intensity)
        self._transition("START", "Threat Intelligence Agent", brief.id, "completed", "SeedSet", {"seed_count": len(seed_cases)})
        self._budget(brief.id, self.threat_intel.name, "load_seed_cases", 0, 0.0, brief.budget_usd, {"seed_count": len(seed_cases)})

        cases = self.orchestrator.select_cases(brief, seed_cases)
        self._transition(
            "Threat Intelligence Agent",
            "Orchestrator Agent",
            brief.id,
            "completed",
            "CampaignBrief",
            {
                "case_count": len(cases),
                "categories": [category.value for category in brief.categories],
                "provider_routes": self.provider_routes,
            },
        )
        self._budget(brief.id, self.orchestrator.name, "select_cases", 0, 0.0, brief.budget_usd, {"case_count": len(cases)})

        health = await self.target.health()
        record_event(AgentEvent(campaign_id=brief.id, agent="Target System", action="health_checked", detail=health))
        self._transition("Orchestrator Agent", "Target System", brief.id, "completed", "HealthCheck", health)

        results = []
        total_cost = 0.0
        halted = False
        halt_reason = None
        for case in cases:
            mutated = self.red_team.mutate(case, brief)
            mutation_tokens = estimate_tokens(mutated.sequence, "")
            mutation_cost = estimate_cost(mutation_tokens)
            self._transition(
                "Orchestrator Agent",
                "Red Team Agent",
                brief.id,
                "completed",
                "AttackCase",
                {
                    "case_id": case.id,
                    "mutated_case_id": mutated.id,
                    "turns": len(mutated.sequence),
                    "provider_route": self.provider_routes["Red Team Agent"],
                },
            )
            self._budget(
                brief.id,
                self.red_team.name,
                "mutate_payload",
                mutation_tokens,
                mutation_cost,
                brief.budget_usd,
                {"case_id": case.id, "turns": len(mutated.sequence)},
            )

            status_code, response_excerpt, error = await self.target.send_sequence(mutated.sequence)
            observed = (
                "Live target response captured for independent judging."
                if not error
                else "Configured target did not expose the expected chat API path during this run."
            )
            tokens = estimate_tokens(mutated.sequence, response_excerpt)
            cost = estimate_cost(tokens)
            total_cost += cost
            self._transition(
                "Red Team Agent",
                "Target System",
                brief.id,
                "completed" if not error else "error",
                "AttackExecution",
                {"case_id": case.id, "status_code": status_code, "transport_error": error},
            )
            self._budget(
                brief.id,
                "Target System",
                "execute_attack_sequence",
                tokens,
                cost,
                brief.budget_usd,
                {"case_id": case.id, "status_code": status_code, "transport_error": error},
            )

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

            verdict = self.judge.evaluate(result, case.expected_safe_behavior, case.severity)
            self._transition(
                "Target System",
                "Judge Agent",
                brief.id,
                "completed",
                "Verdict",
                {
                    "case_id": case.id,
                    "verdict": verdict.verdict,
                    "confidence": verdict.confidence,
                    "provider_route": self.provider_routes["Judge Agent"],
                },
            )
            judge_tokens = estimate_tokens([case.expected_safe_behavior, result.observed_behavior], result.target_response_excerpt)
            self._budget(
                brief.id,
                self.judge.name,
                "evaluate_result",
                judge_tokens,
                estimate_cost(judge_tokens),
                brief.budget_usd,
                {"case_id": case.id, "verdict": verdict.verdict, "confidence": verdict.confidence},
            )
            save_verdict(verdict)

            report = None
            if verdict.verdict in {"fail", "partial"}:
                report = self.docs.create_report(case, result, verdict)
                self._transition(
                    "Judge Agent",
                    "Documentation Agent",
                    brief.id,
                    "completed",
                    "VulnerabilityReport",
                    {
                        "case_id": case.id,
                        "report_id": report.id,
                        "severity": report.severity,
                        "provider_route": self.provider_routes["Documentation Agent"],
                    },
                )
                doc_tokens = estimate_tokens(result.payload_sequence, verdict.rationale)
                self._budget(
                    brief.id,
                    self.docs.name,
                    "create_report",
                    doc_tokens,
                    estimate_cost(doc_tokens),
                    brief.budget_usd,
                    {"case_id": case.id, "report_id": report.id},
                )
                save_report(report)
            else:
                self._transition(
                    "Judge Agent",
                    "Documentation Agent",
                    brief.id,
                    "skipped",
                    "VulnerabilityReport",
                    {"case_id": case.id, "reason": "verdict_passed"},
                )

            results.append({"case": case.id, "verdict": verdict.verdict, "report": report.id if report else None})
            if total_cost > brief.budget_usd * 1.2:
                halted = True
                halt_reason = "campaign_budget_exceeded"
                self._budget(
                    brief.id,
                    self.orchestrator.name,
                    "budget_halt",
                    0,
                    total_cost,
                    brief.budget_usd,
                    {"budget_usd": brief.budget_usd},
                )
                self._transition(
                    "Documentation Agent",
                    "Budget Guard",
                    brief.id,
                    "halted",
                    "BudgetSignal",
                    {"cost_estimate_usd": total_cost, "budget_usd": brief.budget_usd},
                )
                record_event(
                    AgentEvent(
                        campaign_id=brief.id,
                        agent=self.orchestrator.name,
                        action="budget_halt",
                        detail={"cost_estimate_usd": total_cost, "budget_usd": brief.budget_usd},
                    )
                )
                break

            self._transition(
                "Documentation Agent",
                "Orchestrator Agent",
                brief.id,
                "completed",
                "CoverageDelta",
                {"case_id": case.id, "verdict": verdict.verdict},
            )

        summary = MultiAgentRunSummary(
            campaign_id=brief.id,
            graph_version=GRAPH_VERSION,
            nodes_visited=self.nodes_visited,
            transitions_recorded=self.transition_count,
            halted=halted,
            halt_reason=halt_reason,
        )
        record_event(
            AgentEvent(
                campaign_id=brief.id,
                agent="Multi-Agent Core",
                action="campaign_graph_completed",
                detail=summary.model_dump(mode="json"),
            )
        )
        return {
            "campaign_id": brief.id,
            "target": brief.target_url,
            "target_health": health,
            "cases_run": len(results),
            "estimated_cost_usd": round(total_cost, 6),
            "graph": summary.model_dump(mode="json"),
            "provider_routes": self.provider_routes,
            "results": results,
        }

    def _transition(
        self,
        from_node: str,
        to_node: str,
        campaign_id: str,
        status: str,
        message_type: str,
        payload_summary: dict,
    ) -> None:
        self.nodes_visited.append(to_node)
        self.transition_count += 1
        record_agent_transition(
            AgentTransition(
                campaign_id=campaign_id,
                from_node=from_node,
                to_node=to_node,
                status=status,
                message_type=message_type,
                payload_summary=payload_summary,
            )
        )

    def _budget(
        self,
        campaign_id: str,
        agent: str,
        action: str,
        tokens: int,
        cost: float,
        budget: float,
        detail: dict,
    ) -> None:
        record_budget_entry(
            TokenBudgetEntry(
                campaign_id=campaign_id,
                agent=agent,
                action=action,
                estimated_tokens=tokens,
                estimated_cost_usd=cost,
                budget_usd=budget,
                threshold=budget_threshold(cost, budget),
                detail=detail,
            )
        )
