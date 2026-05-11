# AgentForge Architecture

## Executive Summary

AgentForge is a separate adversarial security platform built to continuously evaluate the deployed OpenEMR Clinical Co-Pilot at `https://openemr-js46.onrender.com`. The platform is designed around the core requirement from the assignment: this cannot be a static prompt list, a one-time penetration test, or a single-agent script. AgentForge separates adversarial testing into distinct agents with distinct contexts, trust levels, and outputs so the system can discover, evaluate, document, and regression-test vulnerabilities without letting one role compromise another.

The architecture has five agent roles. The Threat Intelligence Agent is scheduled and mostly deterministic. It loads seed techniques from trusted sources such as OWASP LLM Top 10, MITRE ATLAS, NIST AI RMF, and NVD-style vulnerability feeds, then normalizes relevant techniques into structured attack templates. The Orchestrator Agent reads the coverage map, open findings, regression status, and budget ledger to decide what the Red Team Agent should test next. The Red Team Agent generates and mutates adversarial inputs, including multi-turn sequences, but it cannot decide whether its own attack succeeded. The Judge Agent independently evaluates the target response against versioned rubrics and returns structured verdicts. The Documentation Agent converts confirmed or uncertain findings into reproducible vulnerability reports for human review.

Under these agents is a deterministic regression harness. Confirmed exploits and partial findings are stored in a versioned, queryable format and replayed on future scheduled campaigns. This distinction matters: the agents can explore, but regression validation must be repeatable. A deterministic replay harness is easier to defend to a hospital CISO than a free-form agent that might change its behavior every run.

The initial implementation uses FastAPI, SQLite, typed Pydantic models, JSON seed cases, markdown reports, and a Render cron service. The architecture is provider-agnostic because the LLM provider decision has not been finalized. The intended production routing follows the supplied model: Red Team and Documentation can use OpenRouter-backed open-weight models for cost and model flexibility, while the Judge and Orchestrator should use a direct provider path for consistency and tighter handling of target responses. In the current MVP, deterministic mutation and rubric judging allow the platform to run even without paid model credentials.

The default campaign cadence is weekly, not daily, to control token usage while still producing reviewable findings. A biweekly cadence is also viable, but weekly provides stronger regression visibility for the assignment and keeps projected cost low with the default `$2.50` campaign budget. Human approval gates are placed where autonomy creates the most risk: critical-severity reports, budget overruns, and out-of-taxonomy findings. The Red Team mutation loop remains autonomous within budget because that is where the platform’s discovery value lives.

## System Diagram

![AgentForge architecture](assets/architecture-diagram.png)

## Agent Roles

| Agent | Responsibility | Inputs | Outputs | Trust Level |
| --- | --- | --- | --- | --- |
| Threat Intelligence Agent | Load and normalize external security techniques into seed templates | OWASP, MITRE ATLAS, NIST AI RMF, NVD, local seeds | Structured attack cases and coverage gaps | Low |
| Orchestrator Agent | Prioritize campaigns and enforce budget | Coverage map, open findings, cost ledger, target URL | Campaign brief | Medium |
| Red Team Agent | Generate and mutate adversarial payloads | Campaign brief, seed cases, prior outcomes | Attack sequences | High autonomy within budget |
| Judge Agent | Evaluate target behavior independently | Attack payload, target response, rubric | Verdict JSON | High for verdicts |
| Documentation Agent | Produce reproducible reports | Confirmed or partial finding, verdict, safe behavior | Markdown vulnerability report | Medium, critical findings gated |

## Inter-Agent Communication

Agents communicate through typed Pydantic objects rather than free-form text. The core messages are:

- `CampaignBrief`
- `AttackCase`
- `AttackResult`
- `Verdict`
- `VulnerabilityReport`
- `AgentEvent`

Each transition is stored in SQLite so a campaign can be reconstructed after the fact. This is the MVP equivalent of a LangGraph shared state and Langfuse trace. The design keeps the handoff format stable so LangGraph, Langfuse, Redis, and Postgres can be introduced without changing the conceptual contract.

## Orchestration Strategy

The Orchestrator currently prioritizes high-severity cases first and records the selected case IDs. The intended production weighting is:

`priority = severity * time_since_last_tested * open_finding_pressure * coverage_gap_weight`

The Orchestrator also enforces a campaign budget. If estimated spend exceeds 120% of the configured budget, the campaign halts and requires human review before resuming.

## Regression Harness

The regression harness treats `fail` and `partial` verdicts as cases that should be replayed. A pass means the target response clearly satisfies the safe-behavior rubric. A partial means either the behavior is ambiguous or the target integration path did not expose a complete evaluable response. That honesty matters: an unevaluable attack is not the same thing as a fixed vulnerability.

## Observability

The dashboard surfaces:

- Attack categories tested.
- Pass, fail, and partial counts.
- Estimated campaign cost.
- Open and human-review reports.
- Agent trace events.

The assignment architecture calls for Langfuse. This MVP keeps the data model Langfuse-ready while using SQLite for local replayability and deployment simplicity.

## Human Approval Gates

Human review is required for:

- Critical-severity failures.
- Judge confidence below `0.60`.
- Budget overruns above `120%`.
- Novel out-of-taxonomy attack categories.

Low and medium reports can be filed automatically into the review queue.

## Provider Strategy

The code is provider-agnostic today. Recommended final routing:

- Red Team: Llama 3.3 70B or similar open-weight model via OpenRouter.
- Judge: direct Anthropic Claude Haiku-class model for consistency and narrower target-response routing.
- Orchestrator: direct low-cost reasoning model.
- Documentation: OpenRouter model because it operates on already-classified findings.
- Local fallback: Ollama-compatible open model for low-cost offline smoke tests.

## Known Tradeoffs

- The default target chat path may need updating once the deployed Co-Pilot route is confirmed.
- SQLite is correct for MVP replayability; Postgres is better for multi-user production.
- Rubric judging is deterministic and cheap, but a validated LLM judge should be added before relying on subtle semantic verdicts.
- Weekly campaigns are cost-effective, but they discover regressions more slowly than daily smoke tests.

