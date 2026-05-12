# AI Cost Analysis

AgentForge defaults to weekly scheduled campaigns because it is the most cost-effective cadence for this assignment. Biweekly runs are cheaper, but weekly runs produce better regression visibility while keeping spend low through seed prioritization, deterministic mutation, and rubric judging.

## MVP Assumptions

- Average campaign: 6 to 9 seed cases.
- Average case: 1 to 4 turns.
- Default campaign budget: `$2.50`.
- Deterministic fallback: near-zero LLM cost.
- Hosted model mode: Red Team and Documentation via OpenRouter, Judge via direct provider.
- Threat intelligence refresh: mostly deterministic HTTP fetch and hash work; no LLM spend in the deployed MVP.

## Scale Tiers

| Volume | Expected Architecture | Estimated Cost | Required Changes |
| --- | --- | --- | --- |
| 100 test runs | Hosted APIs or deterministic fallback | `$3-$8/day` in full hosted mode, near-zero in fallback | Single-process FastAPI and SQLite are enough |
| 1K test runs | Hosted APIs with batch judging and prompt caching | `$25-$60/day` | Batch judge calls, dedupe repeated payloads |
| 10K test runs | Hybrid hosted/self-hosted Red Team | `$150-$350/day` | Postgres, queue workers, self-hosted Red Team model |
| 100K test runs | Distributed multi-tenant evaluation | `$800-$1,800/day` | Sharded coverage map, distributed orchestrator, validated local judge |

## Why This Is Not Token Cost Times N

At higher scale, architecture changes. The Red Team Agent should move to a cheaper self-hosted or local model first because attack generation tolerates more variability. The Judge should move last because judge consistency is the integrity of the platform. Caching, semantic deduplication, batch evaluation, and campaign halting reduce cost more than simply choosing a cheaper model.

## Recommended Cadence

Weekly scheduled campaigns are recommended for the current project. They are frequent enough to show continuous testing and regression behavior, but conservative enough to avoid runaway token usage. Biweekly is acceptable once the platform has a stable baseline and fewer target changes.

Threat intelligence refresh runs twice per month. This catches new source updates without adding meaningful token cost because the current implementation uses deterministic mapping rather than LLM normalization.
