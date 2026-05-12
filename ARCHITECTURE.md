# AgentForge Architecture

## Executive Summary

AgentForge is a separate adversarial security platform built to continuously evaluate the deployed OpenEMR Clinical Co-Pilot at `https://openemr-js46.onrender.com`. The MVP is now deployed on Render through Blueprint `exs-d81aqof7f7vs73dfgng0`, with two live services: the `agentforge-ai-security-platform` web dashboard/API and the `agentforge-weekly-campaign` scheduled campaign runner. The active deployment source is the GitHub repository `jayceparabellum/agentforge-ai-security-platform`; the Gauntlet GitLab remote remains documented, but it is not the active Render source because GitLab authentication for that self-hosted host was not available during deployment.

The platform is designed around the core requirement from the assignment: this cannot be a static prompt list, a one-time penetration test, or a single-agent script. AgentForge separates adversarial testing into distinct agents with distinct contexts, trust levels, and outputs so the system can discover, evaluate, document, and regression-test vulnerabilities without letting one role compromise another. The currently deployed MVP has already run smoke campaigns from both the Mac mini development environment and the Render-launched application. Those campaigns reached the deployed OpenEMR target, verified that the target returned HTTP 200, exercised six attack categories, and populated the review queue with reportable findings.

The architecture has five agent roles. The Threat Intelligence Agent is scheduled and mostly deterministic. It loads seed techniques from trusted sources such as OWASP LLM Top 10, MITRE ATLAS, NIST AI RMF, and NVD-style vulnerability feeds, then normalizes relevant techniques into structured attack templates. The Orchestrator Agent reads the coverage map, open findings, regression status, and budget ledger to decide what the Red Team Agent should test next. The Red Team Agent generates and mutates adversarial inputs, including multi-turn sequences, but it cannot decide whether its own attack succeeded. The Judge Agent independently evaluates the target response against versioned rubrics and returns structured verdicts. The Documentation Agent converts confirmed or uncertain findings into reproducible vulnerability reports for human review.

Under these agents is a deterministic regression harness. Confirmed exploits and partial findings are stored in a versioned, queryable format and replayed on future scheduled campaigns. This distinction matters: the agents can explore, but regression validation must be repeatable. A deterministic replay harness is easier to defend to a hospital CISO than a free-form agent that might change its behavior every run.

The implemented MVP uses FastAPI, SQLite, typed Pydantic models, JSON seed cases, markdown reports, Docker, and Render Blueprint infrastructure. The architecture is provider-agnostic because the LLM provider decision has not been finalized. The intended production routing follows the supplied model: Red Team and Documentation can use OpenRouter-backed open-weight models for cost and model flexibility, while the Judge and Orchestrator should use a direct provider path for consistency and tighter handling of target responses. In the current deployed MVP, deterministic mutation and rubric judging allow the platform to run even without paid model credentials.

The default campaign cadence is weekly, not daily, to control token usage while still producing reviewable findings. A biweekly cadence is also viable, but weekly provides stronger regression visibility for the assignment and keeps projected cost low with the default `$2.50` campaign budget. Human approval gates are placed where autonomy creates the most risk: critical-severity reports, budget overruns, and out-of-taxonomy findings. The Red Team mutation loop remains autonomous within budget because that is where the platform's discovery value lives.

One MVP limitation is intentionally visible: the OpenEMR application is reachable, but the exact deployed Clinical Co-Pilot chat route still needs confirmation. The default adapter uses `TARGET_CHAT_PATH=/api/copilot/chat`. Until that route is confirmed or corrected, AgentForge records many live attack attempts as `partial` instead of claiming false exploit success or false safety. This is a defensible MVP behavior: an unevaluable or partially integrated test is preserved as a review finding and regression candidate.

## Deployed MVP State

| Area | Current State |
| --- | --- |
| Render Blueprint | `exs-d81aqof7f7vs73dfgng0` |
| Web service | `agentforge-ai-security-platform` deployed |
| Scheduled job | `agentforge-weekly-campaign` deployed |
| Threat intel job | `agentforge-threat-intel-refresh` added for Blueprint sync |
| Source repo for Render | GitHub `jayceparabellum/agentforge-ai-security-platform` |
| Target system | `https://openemr-js46.onrender.com` |
| Campaign cadence | Weekly, Monday 06:00 UTC |
| Campaign budget | `$2.50` default |
| Local verification | `pytest` passed on Mac mini |
| Live smoke behavior | Campaign controls ran and populated review findings |
| Layer 1 behavior | Fetches OWASP LLM Top 10, MITRE ATLAS, NIST AI 600-1, and NVD CVE 2.0; normalizes external items into generated seed cases; stores feed/case/coverage state in SQLite |
| Layer 2 behavior | Runs campaigns through `MultiAgentCore` graph version `layer2-core-v1` and records typed transitions |
| Layer 3 behavior | Persists vulnerability DB, coverage map, and token budget ledger in SQLite shared state |
| Known integration gap | Confirm final `TARGET_CHAT_PATH` for the Clinical Co-Pilot chat endpoint |

## System Diagram

![AgentForge architecture](assets/architecture-diagram.png)

## Agent Roles

| Agent | Responsibility | Inputs | Outputs | Trust Level |
| --- | --- | --- | --- | --- |
| Threat Intelligence Agent | Fetch, snapshot, and normalize external security techniques into seed templates | OWASP, MITRE ATLAS, NIST AI RMF, NVD CVE 2.0, local JSON seeds | Structured attack cases and coverage gaps | Low |
| Orchestrator Agent | Prioritize campaigns and enforce budget | Coverage map, open findings, cost ledger, target URL | Campaign brief | Medium |
| Red Team Agent | Generate and mutate adversarial payloads | Campaign brief, seed cases, prior outcomes | Attack sequences | High autonomy within budget |
| Judge Agent | Evaluate target behavior independently | Attack payload, target response, rubric | Verdict JSON | High for verdicts |
| Documentation Agent | Produce reproducible reports | Confirmed or partial finding, verdict, safe behavior | Markdown vulnerability report | Medium, critical findings gated |

## Implemented Components

| Component | Implementation |
| --- | --- |
| Web/API | FastAPI in `agentforge/app.py` |
| Multi-Agent Core | `agentforge/core.py` |
| Campaign runner | `python -m agentforge.run_campaign` |
| Agent code | `agentforge/agents/` |
| Target adapter | `agentforge/target.py` with URL allowlist |
| Shared state | SQLite tables for events, attack results, verdicts, and reports |
| Threat-intel shared state | SQLite tables for `threat_feed_items`, `threat_attack_cases`, and `coverage_map` |
| Vulnerability DB | SQLite-backed `/api/vulnerabilities` view over reports, verdicts, and attack results |
| Token Budget Ledger | SQLite-backed `/api/budget-ledger` with per-agent estimated token and cost entries |
| Agent transition log | SQLite-backed `/api/agent-transitions` with graph node handoffs |
| Seed evals | `agentforge/data/seed_cases.json` and `evals/seed_cases.json` |
| Threat feeds | `agentforge/data/threat_feeds/*.json` snapshots |
| Generated threat cases | `agentforge/data/generated_threat_cases.json` |
| Rubrics | `agentforge/data/rubrics.json` |
| Reports | Markdown files in `reports/` |
| Deployment | `Dockerfile` and `render.yaml` |
| CI | `.gitlab-ci.yml` retained for GitLab-compatible testing; GitHub source currently active |

## Inter-Agent Communication

Agents communicate through typed Pydantic objects rather than free-form text. The core messages are:

- `CampaignBrief`
- `AttackCase`
- `AttackResult`
- `Verdict`
- `VulnerabilityReport`
- `AgentEvent`
- `AgentTransition`

Each transition is stored in SQLite so a campaign can be reconstructed after the fact. This is the MVP equivalent of a LangGraph shared state and Langfuse trace. The design keeps the handoff format stable so LangGraph, Langfuse, Redis, and Postgres can be introduced without changing the conceptual contract.

## Layer 2 Multi-Agent Core

Layer 2 is implemented in `agentforge/core.py` as `MultiAgentCore`. It coordinates the agents through a typed graph rather than leaving orchestration as an implicit script. The current graph version is:

```text
layer2-core-v1
```

The graph records transitions across these nodes:

- `START`
- `Threat Intelligence Agent`
- `Orchestrator Agent`
- `Red Team Agent`
- `Target System`
- `Judge Agent`
- `Documentation Agent`
- `Budget Guard`

Every handoff writes an `AgentTransition` row with:

- campaign ID
- source node
- destination node
- status: `started`, `completed`, `skipped`, `halted`, or `error`
- message type
- payload summary
- timestamp

The transition log is exposed at:

```text
GET /api/agent-transitions
```

The campaign response also includes a graph summary with graph version, visited nodes, transition count, and halt state. In verification, a smoke campaign recorded 48 graph transitions across the multi-agent core.

## Orchestration Strategy

The Orchestrator currently prioritizes high-severity cases first and records the selected case IDs. The intended production weighting is:

`priority = severity * time_since_last_tested * open_finding_pressure * coverage_gap_weight`

The Orchestrator also enforces a campaign budget. If estimated spend exceeds 120% of the configured budget, the campaign halts and requires human review before resuming.

In the deployed MVP, the Render cron job invokes:

```bash
python -m agentforge.run_campaign --intensity scheduled
```

The web dashboard can also trigger a smoke campaign manually through the Campaign Controls panel.

## Threat Intelligence Layer

Layer 1 is now implemented as an operational feed refresh pipeline rather than only a static local seed loader. The refresh command is:

```bash
python -m agentforge.run_threat_intel
```

It performs four feed operations:

- Downloads and hashes the official OWASP LLM Top 10 2025 PDF, then maps the ten LLM risk categories into AgentForge attack categories.
- Reads the MITRE ATLAS `atlas-data` repository through the GitHub API and snapshots selected technique/case-study records.
- Downloads and hashes the NIST AI 600-1 Generative AI Profile PDF, then maps core governance and measurement concerns into evaluation seeds.
- Calls the NVD CVE 2.0 API with `NVD_KEYWORD_QUERY` and snapshots any matching CVE records.

The normalization output is written to `agentforge/data/generated_threat_cases.json` and persisted into the shared-state SQLite layer. The shared state includes:

- `threat_feed_items`: one row per fetched external feed item.
- `threat_attack_cases`: normalized generated attack cases from Layer 1.
- `coverage_map`: category-level seed/generated coverage counts for Orchestrator and dashboard use.

Campaigns automatically load both the local baseline seeds and generated Layer 1 seeds from shared state, with the JSON file as an auditable snapshot fallback. Feed failures are non-blocking: the failed source is recorded in the threat-intel refresh result, while the platform continues with the last available local/generated seed set.

The dashboard and API expose this state through:

```text
GET /api/threat-intel/state
```

Render now includes a scheduled `agentforge-threat-intel-refresh` cron job using this schedule:

```yaml
schedule: "0 5 1,15 * *"
```

That approximates the 14-day cadence in the original architecture while staying simple enough for Render cron.

## Regression Harness

The regression harness treats `fail` and `partial` verdicts as cases that should be replayed. A pass means the target response clearly satisfies the safe-behavior rubric. A partial means either the behavior is ambiguous or the target integration path did not expose a complete evaluable response. That honesty matters: an unevaluable attack is not the same thing as a fixed vulnerability.

## Shared State Data Layer

Layer 3 is implemented as a SQLite shared-state data layer. It is intentionally simple for MVP deployment, but the table boundaries match the production architecture and can be moved to Postgres without changing agent responsibilities.

The layer contains:

- `vulnerability_reports`: report metadata created by the Documentation Agent.
- `attack_results`: payloads, target status, response excerpts, token estimates, and observed behavior.
- `verdicts`: Judge Agent verdict, severity, confidence, rationale, and regression flag.
- `threat_feed_items`: external Layer 1 feed records.
- `threat_attack_cases`: normalized Layer 1 generated seed cases.
- `coverage_map`: category-level seed/generated coverage state.
- `token_budget_ledger`: per-agent and per-campaign estimated token and cost entries.

The Vulnerability DB is exposed at:

```text
GET /api/vulnerabilities
```

The Token Budget Ledger is exposed at:

```text
GET /api/budget-ledger
```

During a campaign, the ledger records budget entries for seed loading, orchestration, Red Team mutation, target execution, Judge evaluation, Documentation Agent report creation, and budget halts. Each entry stores estimated tokens, estimated cost, campaign budget, and threshold state: `normal`, `warning`, or `halt`.

## Observability

The dashboard surfaces:

- Attack categories tested.
- Pass, fail, and partial counts.
- Estimated campaign cost.
- Open and human-review reports.
- Vulnerability DB review queue.
- Token budget ledger summary.
- Agent trace events.

The assignment architecture calls for Langfuse. This MVP keeps the data model Langfuse-ready while using SQLite for local replayability and deployment simplicity. The deployed dashboard has been confirmed to launch on Render, and the smoke campaign control has been used successfully after deployment.

## Human Approval Gates

Human review is required for:

- Critical-severity failures.
- Judge confidence below `0.60`.
- Budget overruns above `120%`.
- Novel out-of-taxonomy attack categories.

Low and medium reports can be filed automatically into the review queue.

## Provider Strategy

The deployed code is provider-agnostic today and runs without paid LLM credentials. Recommended final routing:

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
- GitHub is the active deployment source for Render. The Gauntlet GitLab remote can be kept as a mirror once authentication is available.
- NVD keyword search can return zero records depending on query terms and NVD availability; the refresh still snapshots the empty source result and reports source counts honestly.
