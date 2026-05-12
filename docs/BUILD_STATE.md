# AgentForge Build State

Last updated: 2026-05-12

## Deployment

AgentForge is deployed on Render from the GitHub repository jayceparabellum/agentforge-ai-security-platform.

Render Blueprint: exs-d81aqof7f7vs73dfgng0

Services:

- gentforge-ai-security-platform: web dashboard/API
- gentforge-weekly-campaign: scheduled adversarial campaign runner
- gentforge-threat-intel-refresh: scheduled threat intelligence refresh

Target under test:

`	ext
https://openemr-js46.onrender.com
`

## Layer 1: Threat Intelligence

Status: implemented for MVP.

Current behavior:

- Fetches and snapshots OWASP LLM Top 10 2025.
- Fetches and snapshots MITRE ATLAS tlas-data.
- Fetches and hashes NIST AI 600-1.
- Calls and snapshots NVD CVE 2.0 results.
- Normalizes feed items into generated attack seed cases.
- Persists feed items, generated cases, and coverage state into SQLite shared state.
- Runs through the Render gentforge-threat-intel-refresh cron job.

MVP substitution:

- Uses deterministic normalization rather than an LLM normalization call to control cost and keep refreshes reliable.

## Layer 2: Multi-Agent Core

Status: implemented for MVP.

Graph version:

`	ext
layer2-langgraph-provider-routes-v2
`

Current behavior:

- Runs campaigns through MultiAgentCore.
- Records typed graph transitions in gent_transitions.
- Tracks handoffs between Threat Intelligence, Orchestrator, Red Team, Target System, Judge, Documentation, and Budget Guard.
- Adds provider-route metadata to graph payloads.

Provider routes:

| Path | Provider | Reason |
| --- | --- | --- |
| Red Team Agent | OpenRouter | Synthetic payloads only; model swapping is the offensive workflow. |
| Judge Agent | Anthropic direct | Target responses may contain PHI on successful attacks, so the Judge avoids an aggregator hop. |
| Documentation Agent | OpenRouter or direct | Works from already-flagged exploit metadata and structured verdicts. |
| Local fallback | Ollama + Dolphin-Llama3 | Offline and low-cost local testing. |

MVP substitution:

- Uses a custom LangGraph-style runner rather than the langgraph package, while preserving explicit nodes, typed transitions, shared state, and traceability.

## Layer 3: Shared State

Status: implemented for MVP.

SQLite tables include:

- ulnerability_reports
- ttack_results
- erdicts
- 	hreat_feed_items
- 	hreat_attack_cases
- coverage_map
- 	oken_budget_ledger
- gent_transitions

APIs include:

- GET /api/dashboard
- GET /api/threat-intel/state
- GET /api/vulnerabilities
- GET /api/budget-ledger
- GET /api/agent-transitions
- GET /api/provider-routes

MVP substitution:

- Uses SQLite instead of production Postgres/Redis/Langfuse. This is sufficient for MVP and keeps the system easy to deploy on Render.

## Known Caveat

The deployed OpenEMR URL is reachable, but the exact Clinical Co-Pilot chat endpoint still needs confirmation. Until TARGET_CHAT_PATH is corrected, attack outcomes may be recorded as partial integration findings rather than definitive exploit successes or passes.

## Rollback

Protected rollback tag:

`	ext
rollback-mvp-layer123-provider-routes-2026-05-12
`

See docs/ROLLBACK.md for restore commands.
