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
https://clinical-copilot-0mgb.onrender.com
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

-
ulnerability_reports
- ttack_results
-
erdicts
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

The deployed Clinical Co-Pilot URL is reachable and is now the only target URL. The default target chat path is TARGET_CHAT_PATH=/chat.

## Rollback

Protected rollback tag:

`	ext
rollback-mvp-layer123-provider-routes-2026-05-12
`

See docs/ROLLBACK.md for restore commands.

## Layer 4: Deterministic Tooling

Status: implemented for MVP.

Current behavior:

- Deterministic fuzzer generates prompt/payload variants using case toggling, base64 wrapping, role-prefix wrapping, and spacing noise.
- Fuzz cases are persisted in
uzz_cases.
- Regression replay reads confirmed/partial findings and replays their payloads against the configured target.
- Replay results are persisted in
egression_replay_results.
- Dashboard and API expose Layer 4 state.
- Render config includes gentforge-regression-replay as a weekly deterministic replay job.

APIs:

- GET /api/layer4
- POST /api/layer4/fuzz
- POST /api/layer4/regression

CLI:

`ash
python -m agentforge.run_layer4 fuzz --max-cases 12
python -m agentforge.run_layer4 regression --intensity smoke
`

MVP substitution:

- Fuzzing is deterministic string transformation rather than LLM-driven mutation. This keeps replayability high and cost near zero.

## Layer 5: Target System

Status: implemented for MVP.

Current behavior:

- The target client enforces `TARGET_ALLOWLIST` before health checks, probes, campaign payloads, or regression replay traffic.
- The OpenEMR target profile is persisted in `target_profiles`.
- Endpoint probe evidence is persisted in `target_probe_results`.
- The dashboard has a Layer 5 Target System panel with profile and endpoint probe summaries.
- Render config includes `agentforge-target-probe` as a weekly pre-campaign target contract check.
- The current deployed Clinical Co-Pilot base URL is reachable, and the default red-team route is `TARGET_CHAT_PATH=/chat`.

APIs:

- GET /api/target
- POST /api/target/probe

CLI:

```bash
python -m agentforge.run_target_probe
```

MVP substitution:

- Layer 5 uses lightweight endpoint probing rather than authenticated OpenEMR workflow automation. This keeps the probe benign and low-cost while making the target integration state visible before campaigns spend tokens.
