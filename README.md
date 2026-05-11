# AgentForge AI Security Platform

AgentForge is a deployable multi-agent adversarial evaluation platform for testing the deployed OpenEMR Clinical Co-Pilot at:

`https://openemr-js46.onrender.com`

This is a separate application, not an OpenEMR fork. It continuously exercises the target with structured adversarial campaigns, records judge verdicts, creates reviewable vulnerability reports, and keeps confirmed or uncertain findings in a deterministic regression loop.

## What It Does

- Runs authorized adversarial evaluations against an allowlisted target.
- Separates responsibilities across Threat Intelligence, Orchestrator, Red Team, Judge, and Documentation agents.
- Stores agent traces, results, verdicts, and report metadata in SQLite.
- Provides a FastAPI dashboard and JSON API for reviewing findings.
- Ships with a Render web service and weekly cron job configuration.
- Defaults to a low-cost weekly cadence, with a biweekly option documented below.

## Architecture

The design follows the attached architecture model in `assets/architecture-diagram.png`.

![AgentForge architecture](assets/architecture-diagram.png)

The current implementation is intentionally provider-agnostic. If `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, and Langfuse credentials are absent, AgentForge uses deterministic seed mutation and rubric-based judging so the harness remains runnable and reproducible. The interfaces are shaped so hosted models can be plugged into the same agent boundaries later.

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn agentforge.app:app --reload
```

Open `http://127.0.0.1:8000`.

Run a smoke campaign:

```bash
python -m agentforge.run_campaign --intensity smoke
```

Run tests:

```bash
pytest
```

## Deployment

The repo includes:

- `Dockerfile` for container deployment.
- `render.yaml` for a Render web service plus weekly cron.
- `TARGET_ALLOWLIST` guardrail so campaigns only run against explicitly approved targets.

The default schedule in `render.yaml` is weekly:

```yaml
schedule: "0 6 * * 1"
```

For a biweekly cadence, change the cron service to a low-frequency external trigger or use Render's scheduled job settings to run every other Monday. Weekly is recommended for this project because it gives enough signal for the assignment while keeping the default campaign budget at `$2.50`.

## Review Workflow

1. The weekly cron starts a scheduled campaign.
2. The Orchestrator chooses high-severity seed cases.
3. The Red Team Agent creates bounded variants.
4. The target client sends payload sequences to the configured Clinical Co-Pilot endpoint.
5. The Judge Agent issues `pass`, `fail`, or `partial` verdicts using versioned rubrics.
6. The Documentation Agent writes markdown reports for `fail` and `partial` cases.
7. The dashboard shows the review queue, coverage, estimated cost, and agent trace.

## Important Target Integration Note

The deployed OpenEMR URL is live, but the actual Clinical Co-Pilot chat endpoint path may differ from the default `/api/copilot/chat`. Set `TARGET_CHAT_PATH` once the deployed Co-Pilot API route is known. Until then, AgentForge records integration findings as `partial` so the test harness remains honest and reviewable.

## Repository Remote

Intended GitLab remote:

`https://labs.gauntletai.com/jayceparabellum/agentforge-ai-security-platform`

