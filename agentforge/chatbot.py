from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from agentforge.agents.threat_intel import ThreatIntelAgent
from agentforge.campaign import run_campaign
from agentforge.config import get_settings
from agentforge.deterministic import run_fuzzer, run_regression_replay
from agentforge.evaluation import evaluate_golden_cases
from agentforge.storage import (
    fetch_agent_transitions,
    fetch_approval_queue,
    fetch_dashboard,
    fetch_layer4_state,
    fetch_observability,
    fetch_target_state,
    fetch_threat_intel_state,
    fetch_token_budget_ledger,
    fetch_vulnerability_db,
)
from agentforge.target import TargetClient


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=800)


class ChatResponse(BaseModel):
    intent: str
    answer: str
    data: Dict[str, Any] = Field(default_factory=dict)
    actions: List[str] = Field(default_factory=list)


HELP_TEXT = (
    "I can run approved architecture operations and retrieve platform state. Try: "
    "`refresh threat intel`, `run smoke campaign`, `probe target`, `run fuzzer`, "
    "`replay regressions`, `show reports`, `show budget`, `show observability`, "
    "`show approvals`, `show evals`, or `explain architecture`."
)


async def handle_chat(request: ChatRequest) -> ChatResponse:
    message = request.message.strip()
    normalized = " ".join(message.lower().split())

    if any(term in normalized for term in ["help", "what can you do", "commands"]):
        return ChatResponse(intent="help", answer=HELP_TEXT, actions=_actions())

    if any(term in normalized for term in ["explain architecture", "architecture", "layers"]):
        return ChatResponse(
            intent="explain_architecture",
            answer=(
                "The platform runs as a standalone adversarial harness: threat intelligence feeds create attack seeds; "
                "the multi-agent core orchestrates red-team, target, judge, and documentation steps; shared state stores "
                "coverage, reports, budget, traces, and approvals; deterministic tooling handles fuzzing and replay; "
                "the target layer is allowlisted; observability records traces; and human review gates critical findings."
            ),
            data={"provider_routes": get_settings().provider_routes},
            actions=_actions(),
        )

    if "refresh" in normalized and ("intel" in normalized or "threat" in normalized):
        result = ThreatIntelAgent().refresh()
        return ChatResponse(
            intent="refresh_threat_intel",
            answer=(
                f"Threat intelligence refresh complete. Generated {result.generated_case_count} cases from "
                f"{len(result.source_counts)} source families."
            ),
            data=result.model_dump(mode="json"),
            actions=_actions(),
        )

    if ("run" in normalized or "start" in normalized) and ("campaign" in normalized or "agent workflow" in normalized or "smoke" in normalized):
        result = await run_campaign(intensity="smoke")
        return ChatResponse(
            intent="run_smoke_campaign",
            answer=(
                f"Smoke campaign `{result['campaign_id']}` finished against the allowlisted target. "
                f"Cases run: {result['cases_run']}; graph transitions: {result['graph']['transitions_recorded']}."
            ),
            data=result,
            actions=_actions(),
        )

    if "probe" in normalized and "target" in normalized:
        result = await TargetClient(get_settings()).probe()
        return ChatResponse(
            intent="probe_target",
            answer=f"Target probe complete. Integration status: {result['profile']['integration_status']}.",
            data=result,
            actions=_actions(),
        )

    if "fuzz" in normalized or "fuzzer" in normalized:
        result = run_fuzzer(max_cases=12)
        return ChatResponse(
            intent="run_fuzzer",
            answer=f"Fuzzer complete. Generated {result['generated_variants']} variants from {result['seed_cases']} seed cases.",
            data=result,
            actions=_actions(),
        )

    if "replay" in normalized or "regression" in normalized:
        result = await run_regression_replay(intensity="smoke")
        return ChatResponse(
            intent="replay_regressions",
            answer=f"Regression replay `{result['campaign_id']}` complete. Replayed {result['replayed']} cases.",
            data=result,
            actions=_actions(),
        )

    if "threat" in normalized or "shared state" in normalized or "coverage map" in normalized:
        data = fetch_threat_intel_state()
        return ChatResponse(
            intent="retrieve_threat_intel_state",
            answer=f"Threat-intel shared state loaded. Sources: {len(data['sources'])}; generated cases shown: {len(data['generated_cases'])}.",
            data=data,
            actions=_actions(),
        )

    if "report" in normalized or "review queue" in normalized or "vulnerab" in normalized or "finding" in normalized:
        data = fetch_vulnerability_db()
        return ChatResponse(
            intent="retrieve_reports",
            answer=f"Report state loaded. Findings available: {len(data['findings'])}.",
            data=data,
            actions=_actions(),
        )

    if "budget" in normalized or "cost" in normalized or "token" in normalized:
        data = fetch_token_budget_ledger()
        dashboard = fetch_dashboard()
        return ChatResponse(
            intent="retrieve_budget",
            answer=(
                f"Lifetime coverage cost is ${dashboard['lifetime_coverage_cost_usd']} across "
                f"{dashboard['lifetime_coverage_tokens']} estimated tokens."
            ),
            data={"ledger": data, "dashboard": dashboard},
            actions=_actions(),
        )

    if "transition" in normalized or "multi-agent" in normalized or "graph" in normalized:
        data = fetch_agent_transitions()
        return ChatResponse(
            intent="retrieve_agent_transitions",
            answer=f"Agent graph transitions loaded. Recent transitions: {len(data['transitions'])}.",
            data=data,
            actions=_actions(),
        )

    if "observability" in normalized or "trace" in normalized:
        data = fetch_observability()
        return ChatResponse(
            intent="retrieve_observability",
            answer=f"Observability loaded. Recent traces: {len(data['traces'])}; summary rows: {len(data['trace_summary'])}.",
            data=data,
            actions=_actions(),
        )

    if "approval" in normalized or "human review" in normalized:
        data = fetch_approval_queue()
        return ChatResponse(
            intent="retrieve_approvals",
            answer=f"Approval queue loaded. Items: {len(data['approvals'])}.",
            data=data,
            actions=_actions(),
        )

    if "eval" in normalized or "golden" in normalized:
        data = evaluate_golden_cases(write_latest=False)
        return ChatResponse(
            intent="retrieve_evals",
            answer=f"Golden eval suite is {data['status']} with {data['total_cases']} cases and {data['readiness_percent']}% readiness.",
            data=data,
            actions=_actions(),
        )

    if "target" in normalized:
        data = fetch_target_state()
        return ChatResponse(
            intent="retrieve_target_state",
            answer=f"Target state loaded. Profiles: {len(data['profiles'])}; probe summary rows: {len(data['summary'])}.",
            data=data,
            actions=_actions(),
        )

    if "deterministic" in normalized or "tooling" in normalized:
        data = fetch_layer4_state()
        return ChatResponse(
            intent="retrieve_deterministic_tooling",
            answer=f"Deterministic tooling state loaded. Fuzz cases: {len(data['fuzz_cases'])}; regression rows: {len(data['regression_results'])}.",
            data=data,
            actions=_actions(),
        )

    return ChatResponse(
        intent="fallback",
        answer=f"I did not recognize that command. {HELP_TEXT}",
        actions=_actions(),
    )


def _actions() -> List[str]:
    return [
        "refresh threat intel",
        "run smoke campaign",
        "probe target",
        "run fuzzer",
        "replay regressions",
        "show reports",
        "show budget",
        "show observability",
        "show approvals",
        "show evals",
        "explain architecture",
    ]
