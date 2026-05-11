from agentforge.agents.judge import JudgeAgent
from agentforge.models import AttackCategory, AttackResult


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

