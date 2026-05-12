# AgentForge AI Security Platform

AgentForge is a deployable multi-agent adversarial evaluation platform for testing the deployed OpenEMR Clinical Co-Pilot target:

`https://openemr-js46.onrender.com`

This is a separate application, not an OpenEMR fork. It runs authorized adversarial campaigns against an allowlisted target, records independent judge verdicts, generates reviewable vulnerability reports, and keeps uncertain or confirmed findings in a regression loop.

## Current Build State

- Status: MVP build complete and deployed on Render.
- Render Blueprint ID: `exs-d81aqof7f7vs73dfgng0`.
- Render services deployed: `agentforge-ai-security-platform` and `agentforge-weekly-campaign`.
- Deployment source: GitHub repo `jayceparabellum/agentforge-ai-security-platform`.
- Original Gauntlet GitLab URL: `https://labs.gauntletai.com/jayceparabellum/agentforge-ai-security-platform`.
- Target system: `https://openemr-js46.onrender.com`.
- Local verification: passed on the Mac mini.
- Smoke campaign: reached the deployed OpenEMR URL with HTTP 200 and generated six reviewable partial findings.
- Important caveat: the exact deployed Clinical Co-Pilot chat endpoint still needs confirmation. Until `TARGET_CHAT_PATH` is updated, live attack attempts are recorded as `partial` integration findings rather than false passes.

## What It Does

- Runs authorized adversarial evaluations against `TARGET_ALLOWLIST`.
- Separates responsibilities across Threat Intelligence, Orchestrator, Red Team, Judge, and Documentation agents.
- Refreshes external threat-intelligence feeds from OWASP LLM Top 10, MITRE ATLAS, NIST AI RMF, and NVD CVE 2.0.
- Normalizes fetched threat items into generated adversarial seed cases.
- Stores agent traces, attack results, verdicts, and report metadata in SQLite.
- Provides a FastAPI dashboard and JSON API for reviewing findings.
- Ships with a Dockerfile and Render Blueprint config.
- Runs scheduled campaigns weekly by default to control cost.

## Architecture

The implementation follows the supplied architecture model in `assets/architecture-diagram.png`.

![AgentForge architecture](assets/architecture-diagram.png)

The current MVP is provider-agnostic. If model credentials are absent, AgentForge uses deterministic seed mutation and rubric-based judging so the harness remains runnable and reproducible. The intended production routing is:

- Red Team Agent: OpenRouter-backed open-weight model.
- Judge Agent: direct provider path for consistent independent verdicts.
- Orchestrator Agent: low-cost reasoning model or deterministic prioritizer.
- Documentation Agent: cost-effective structured generation model.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn agentforge.app:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

Run tests:

```bash
pytest
```

Run a smoke campaign:

```bash
python -m agentforge.run_campaign --intensity smoke
```

Refresh Layer 1 threat intelligence:

```bash
python -m agentforge.run_threat_intel
```

## Render Deployment

Render deploys this repo through `render.yaml`.

Active Blueprint:

```text
exs-d81aqof7f7vs73dfgng0
```

Deployed Blueprint services:

- `agentforge-ai-security-platform`: web dashboard/API.
- `agentforge-weekly-campaign`: weekly scheduled campaign runner.
- `agentforge-threat-intel-refresh`: scheduled threat-intelligence refresh.

Default environment:

```text
TARGET_BASE_URL=https://openemr-js46.onrender.com
TARGET_ALLOWLIST=https://openemr-js46.onrender.com
TARGET_CHAT_PATH=/api/copilot/chat
AGENTFORGE_CAMPAIGN_CADENCE=weekly
CAMPAIGN_BUDGET_USD=2.50
THREAT_INTEL_MAX_GENERATED_CASES=12
NVD_KEYWORD_QUERY=LLM AI machine learning
```

The default cron schedule is:

```yaml
schedule: "0 6 * * 1"
```

That runs every Monday at 06:00 UTC. Weekly is recommended for the assignment because it gives recurring regression evidence without unnecessary token spend. Biweekly can be configured later if cost becomes more important than regression freshness.

Threat intelligence refresh runs on the 1st and 15th of each month:

```yaml
schedule: "0 5 1,15 * *"
```

## Review Workflow

1. The weekly cron starts a scheduled campaign.
2. The Threat Intelligence Agent loads local seeds plus generated external threat-intel seeds.
3. The Orchestrator selects high-priority seed cases.
4. The Red Team Agent creates bounded variants.
5. The target client sends payload sequences to the configured Clinical Co-Pilot endpoint.
6. The Judge Agent issues `pass`, `fail`, or `partial` verdicts using versioned rubrics.
7. The Documentation Agent writes markdown reports for `fail` and `partial` cases.
8. The dashboard shows the review queue, coverage, estimated cost, and agent trace.

## Assignment Deliverables

- `THREAT_MODEL.md`: attack surface map and prioritization summary.
- `ARCHITECTURE.md`: multi-agent architecture, trust boundaries, and diagram.
- `USERS.md`: users, workflows, and automation justification.
- `COST_ANALYSIS.md`: scale-tier cost model.
- `evals/`: seed cases and latest smoke campaign output.
- `reports/`: vulnerability report queue.
- `schemas/`: typed inter-agent message contracts.
- `agentforge/data/threat_feeds/`: latest external threat feed snapshots.
- `agentforge/data/generated_threat_cases.json`: generated Layer 1 seed cases.

## Target Integration Note

The OpenEMR application is reachable, but the actual Clinical Co-Pilot chat route may not be `/api/copilot/chat`. Set `TARGET_CHAT_PATH` in Render once the deployed route is known. The MVP intentionally marks incomplete target interactions as `partial` so the platform remains honest and reviewable.
