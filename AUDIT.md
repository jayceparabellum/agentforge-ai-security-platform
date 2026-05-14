# Audit

## Current Build Audit

Date: 2026-05-14

AgentForge is deployed as a separate security platform for authorized testing of the allowlisted Clinical Co-Pilot target:

```text
https://clinical-copilot-0mgb.onrender.com
```

The application does not attack arbitrary URLs. Target traffic is constrained by `TARGET_ALLOWLIST` and `TARGET_CHAT_PATH=/chat`.

## Audit Surfaces

| Surface | Evidence |
| --- | --- |
| Threat intelligence refresh | Feed snapshots in `agentforge/data/threat_feeds/` and shared-state rows in `threat_feed_items` |
| Campaign execution | `events`, `attack_results`, `verdicts`, and `agent_transitions` SQLite tables |
| Provider routing | `/api/provider-routes` documents Red Team, Judge, Documentation, and fallback paths |
| Vulnerability reports | SQLite `vulnerability_reports` plus markdown artifacts in `reports/` |
| Report review | `/reports`, `/reports/{report_id}`, and `/api/reports/{report_id}` |
| Human approval gates | `human_approvals` table and `/api/approvals` |
| Observability | `langfuse_traces` table and `/api/observability` |
| Eval readiness | `evals/golden_cases.json`, `evals/results.latest.json`, and `/api/evals/progress` |
| Second-run live evidence | Raw JSON artifacts in `evals/live-evidence/` |

## Second-Run Evidence

| Check | Result |
| --- | --- |
| Repo separation scan | No legacy target-repo URL or inherited-repo wording outside git history |
| Target probe | Healthy; `/chat` and `/w2/chat` accepted benign POST probes with HTTP 200 |
| Smoke campaign | `campaign-15e29f27`, 9 cases, 49 graph transitions, 3 pass, 4 partial, 2 fail |
| Regression replay | `regression-04d588cb`, 9 cases, 4 HTTP 200 target responses, 5 timeout/incomplete cases held as partial |
| Golden eval readiness | 50 validated cases, 100% readiness, all six attack categories covered |

## Data-Hop Rationale

- Red Team Agent uses OpenRouter for synthetic payload generation and model flexibility. This path should not receive PHI.
- Judge Agent uses direct Anthropic routing in the intended production architecture because target responses may contain PHI if an exploit succeeds.
- Documentation Agent can use OpenRouter or direct routing depending on the compliance posture for finalized report generation.
- Local fallback remains available for development and low-cost smoke testing.

## Current Controls

- Target allowlist prevents off-target payload delivery.
- Critical-severity findings create human approval gates.
- Reports are reviewable through the Results tab and fall back to checked-in markdown artifacts if runtime SQLite state is recreated.
- Token budget ledger tracks estimated campaign spend.
- The golden eval suite validates 50 adversarial safety scenarios across all six attack categories without spending model tokens.

## Known Limitations

- SQLite is suitable for MVP and Render demo use, but Postgres should replace it for durable multi-instance production state.
- Langfuse-style traces are stored locally in SQLite rather than exported to a managed Langfuse instance.
- The golden eval suite currently validates corpus readiness and coverage. A future version can execute all 50 prompts against the live target and score target behavior automatically.
