# AI Cost Analysis

AgentForge defaults to weekly scheduled campaigns because it is the most cost-effective cadence for this assignment. Biweekly runs are cheaper, but weekly runs produce better regression visibility while keeping spend low through seed prioritization, deterministic mutation, and rubric judging.

## MVP Assumptions

- Average campaign: 6 to 9 seed cases.
- Average case: 1 to 4 turns.
- Default campaign budget: `$2.50`.
- Deterministic fallback: near-zero LLM cost.
- Hosted model mode: Red Team and Documentation via OpenRouter, Judge via direct provider.
- Threat intelligence refresh: mostly deterministic HTTP fetch and hash work; no LLM spend in the deployed MVP.
- Layer 3 Token Budget Ledger records per-agent estimated token and cost entries during each campaign.

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

The Token Budget Ledger persists the operational cost model instead of leaving cost as a one-off campaign total. The MVP estimates tokens from prompt/response word counts and applies a conservative placeholder rate. In production, those entries should be replaced or augmented with provider-returned usage data.

Layer 2 now records which agent produced each budget entry. This allows campaign spend to be separated by Red Team mutation, target execution, Judge evaluation, Documentation, and Orchestrator control work.

Provider routing also affects cost strategy. Red Team generation is routed through OpenRouter because model swapping and price competition matter most on synthetic payload generation. Judge evaluation stays direct to Anthropic because correctness and a simpler data-hop story matter more than marginal routing flexibility when target responses may contain sensitive data.

Layer 4 keeps deterministic tooling cheap. Fuzzing is pure string transformation and has no model cost. Regression replay only incurs target/Judge costs when replayed cases are evaluated; this is why it is scheduled weekly after the campaign rather than continuously.
