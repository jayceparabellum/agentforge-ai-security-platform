from pathlib import Path

from agentforge.models import AgentEvent, AttackCase, AttackResult, Verdict, VulnerabilityReport
from agentforge.storage import record_event


class DocumentationAgent:
    name = "Documentation Agent"

    def create_report(self, case: AttackCase, result: AttackResult, verdict: Verdict) -> VulnerabilityReport:
        reports_dir = Path("reports")
        reports_dir.mkdir(exist_ok=True)
        report_id = f"AF-{case.category.value.upper().replace('_', '-')}-{case.id.replace('-', '')}"
        path = reports_dir / f"{report_id}.md"
        status = "human_review" if verdict.human_review_required else "open"
        title = f"{case.category.value.replace('_', ' ').title()} - {case.subcategory.replace('_', ' ')}"
        body = f"""# {report_id}: {title}

## Severity
{verdict.severity}/5

## Status
{status}

## Clinical Impact
This finding affects the OpenEMR Clinical Co-Pilot adversarial surface for `{case.category.value}`. In a clinical workflow, a successful exploit could reduce operator trust, disclose protected data, corrupt clinical context, or increase operational cost depending on the category.

## Minimal Reproducible Attack Sequence
Target: `{result.campaign_id}` against `https://openemr-js46.onrender.com`

```text
{chr(10).join(f"{index + 1}. {prompt}" for index, prompt in enumerate(result.payload_sequence))}
```

## Expected Safe Behavior
{case.expected_safe_behavior}

## Observed Behavior
{result.observed_behavior}

Transport error: `{result.transport_error or "none"}`

Response excerpt:

```text
{result.target_response_excerpt[:1000] or "No response body captured."}
```

## Judge Verdict
Verdict: `{verdict.verdict}`

Confidence: `{verdict.confidence}`

Rationale: {verdict.rationale}

## Recommended Remediation
Validate the Clinical Co-Pilot endpoint path, enforce server-side authorization before retrieval/tool calls, add category-specific guardrails, and keep this case in the deterministic regression harness until a passing result is observed across two scheduled runs.

## Fix Validation
Pending. This report remains reviewable until the regression harness records a pass on the deployed target.
"""
        path.write_text(body, encoding="utf-8")
        report = VulnerabilityReport(
            id=report_id,
            case_id=case.id,
            campaign_id=result.campaign_id,
            title=title,
            severity=verdict.severity,
            status=status,
            markdown_path=str(path),
        )
        record_event(
            AgentEvent(
                campaign_id=result.campaign_id,
                agent=self.name,
                action="report_created",
                detail={"report_id": report.id, "path": report.markdown_path, "status": report.status},
            )
        )
        return report

