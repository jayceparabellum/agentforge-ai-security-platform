from agentforge.agents.judge import JudgeAgent
from agentforge.agents.threat_intel import ThreatIntelAgent
from agentforge.models import AttackCategory, AttackResult, ThreatFeedItem
from agentforge.storage import (
    fetch_agent_transitions,
    fetch_generated_threat_cases,
    fetch_token_budget_ledger,
    fetch_vulnerability_db,
    record_budget_entry,
    save_threat_intel_state,
)
from agentforge.models import TokenBudgetEntry
from agentforge.config import get_settings


def test_judge_marks_transport_error_as_partial():
    result = AttackResult(
        case_id="PI-001",
        campaign_id="campaign-test",
        category=AttackCategory.prompt_injection,
        payload_sequence=["ignore safeguards"],
        transport_error="ConnectError",
        observed_behavior="Configured target did not expose the expected chat API path during this run.",
    )
    verdict = JudgeAgent().evaluate(result, "refuse", 3)
    assert verdict.verdict == "partial"
    assert verdict.should_regress is True


def test_threat_intel_normalizes_external_item():
    agent = ThreatIntelAgent()
    cases = agent._normalize_items(
        [
            ThreatFeedItem(
                source="OWASP LLM Top 10 2025",
                external_id="LLM01",
                title="Prompt Injection",
                summary="Prompt injection risk",
                url="https://owasp.org",
                category=AttackCategory.prompt_injection,
            )
        ]
    )
    assert cases[0].id.startswith("PI-TI-")
    assert cases[0].category == AttackCategory.prompt_injection


def test_threat_intel_shared_state_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "agentforge-test.db"))
    get_settings.cache_clear()
    agent = ThreatIntelAgent()
    item = ThreatFeedItem(
        source="NIST AI RMF Generative AI Profile",
        external_id="NIST-AI-600-1-MEASURE",
        title="Measure prompt safety failures",
        summary="Measurement seed",
        url="https://nist.gov",
        category=AttackCategory.prompt_injection,
    )
    cases = agent._normalize_items([item])
    save_threat_intel_state([item], cases)
    loaded = fetch_generated_threat_cases()
    assert loaded[0].id == cases[0].id
    assert loaded[0].source.startswith("NIST AI RMF")


def test_token_budget_ledger_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "agentforge-budget.db"))
    get_settings.cache_clear()
    record_budget_entry(
        TokenBudgetEntry(
            campaign_id="campaign-test",
            agent="Red Team Agent",
            action="mutate_payload",
            estimated_tokens=120,
            estimated_cost_usd=0.00006,
            budget_usd=2.5,
            detail={"case_id": "PI-001"},
        )
    )
    ledger = fetch_token_budget_ledger(campaign_id="campaign-test")
    assert ledger["entries"][0]["agent"] == "Red Team Agent"
    assert ledger["summary"][0]["estimated_tokens"] == 120


def test_vulnerability_db_empty_shape(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "agentforge-vulns.db"))
    get_settings.cache_clear()
    db = fetch_vulnerability_db()
    assert db["findings"] == []
    assert db["status_counts"] == []


def test_layer2_core_records_transitions(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "agentforge-layer2.db"))
    get_settings.cache_clear()
    from agentforge.storage import record_agent_transition
    from agentforge.models import AgentTransition

    record_agent_transition(
        AgentTransition(
            campaign_id="campaign-test",
            from_node="START",
            to_node="Threat Intelligence Agent",
            status="completed",
            message_type="SeedSet",
            payload_summary={"seed_count": 6},
        )
    )
    transitions = fetch_agent_transitions(campaign_id="campaign-test")
    assert transitions["transitions"][0]["to_node"] == "Threat Intelligence Agent"
    assert transitions["node_counts"][0]["count"] == 1
