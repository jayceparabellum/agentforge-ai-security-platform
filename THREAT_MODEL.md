# Threat Model

## Summary

The deployed external deployed Clinical Co-Pilot target creates a high-value adversarial surface because it sits near clinical context, operational workflows, and potentially sensitive patient data. The highest-risk categories are data exfiltration, identity and role exploitation, state corruption, and tool misuse. Prompt injection remains important, but the more dangerous failure mode is not simply that the assistant obeys a malicious phrase. The dangerous failure mode is that the assistant accepts attacker-controlled context as authorization, retrieves or summarizes data across patient boundaries, invokes tools with unsafe parameters, or carries poisoned state across turns.

AgentForge prioritizes coverage based on clinical impact, exploitability, and regression risk. Data exfiltration receives the highest priority because a successful attack can expose PHI, cross-patient records, or operational identifiers. Identity and role exploitation is also high priority because an LLM assistant may be persuaded to treat conversation text as an authority signal unless server-side permissions are enforced. State corruption is a key multi-turn risk: an attacker can gradually establish false assumptions, then request sensitive behavior later in the conversation. Tool misuse matters because a safe natural-language response can still be paired with unsafe backend tool calls if parameters are not validated. Denial of service is lower clinical-severity than PHI exposure, but it matters operationally because recursive tool calls, oversized outputs, and repeated retrieval can increase cost and latency.

The platform does not assume that one successful jailbreak proves the system is insecure or that one blocked prompt proves a category is fixed. Each seed case is treated as the beginning of a coverage thread. The Threat Intelligence Agent now refreshes OWASP LLM Top 10, MITRE ATLAS, NIST AI 600-1, and NVD CVE 2.0 sources, snapshots feed results, normalizes external items into generated seed cases, and stores them in the shared-state data layer for the Orchestrator and dashboard. The Red Team Agent mutates seed prompts into variants, the Judge Agent evaluates responses against a stable rubric, and uncertain or failed cases are converted into reports and regression candidates. This gives the project a living threat model rather than a static document.

The Layer 2 multi-agent core now records each handoff as an auditable transition, which matters for healthcare security review. A finding can be traced from threat-intel seed, to orchestrator selection, to Red Team mutation, to target response, to Judge verdict, to Documentation Agent report.

Provider routing is also treated as a trust boundary. The Red Team path uses OpenRouter because it handles synthetic adversarial payloads. The Judge path uses direct Anthropic because it evaluates target responses that may contain PHI if an attack succeeds. That separation keeps attack generation independent from evaluation while minimizing data hops for the most sensitive response path.

Layer 4 adds deterministic pressure to the threat model. Fuzzing checks whether a defense only blocks a narrow wording of an attack, while regression replay checks whether previously observed partial or failed cases still reproduce after target changes. This is intentionally deterministic rather than agentic so replay results can be compared across runs.

Layer 5 makes the deployed target itself part of the security model. AgentForge stores an allowlisted external target profile, probes the base application and likely Clinical Co-Pilot API paths, and records whether the integration is `healthy`, `partial`, or `unreachable`. This keeps campaign results honest: a missing or changed endpoint is not treated as a pass, and the system does not send adversarial traffic to any URL outside `TARGET_ALLOWLIST`.

Layer 6 and Layer 7 make the evaluation auditable and reviewable. Layer 6 records Langfuse-style traces for agent handoffs, verdicts, and approval events so campaigns can be reconstructed after the fact. Layer 7 creates a human approval gate for critical-severity findings so severe results are not silently accepted without review.

Trust boundaries are explicit. The external deployed target is allowlisted. The adversarial platform must not be repointed at unauthorized systems. Attack generation is synthetic and bounded by budget. The Judge is isolated from the Red Team so it is not influenced by the attacker’s explanation of why an exploit should count. Critical-severity findings and low-confidence verdicts are routed to a human review queue. Reports are written for reproducibility, not drama: each one must include a minimal attack sequence, expected behavior, observed behavior, severity, and remediation guidance.

For the MVP, the key implementation risk is target integration. The external target application is live at `https://clinical-copilot-0mgb.onrender.com`, but the exact Clinical Co-Pilot chat endpoint may differ from the default adapter path. Until that route is confirmed, AgentForge records incomplete target interaction as a partial finding instead of falsely claiming success or safety. Once the chat route is configured, the same attack cases and judge rubrics become live regression tests.

## Attack Surface Map

| Category | Attack Surface | Potential Impact | Difficulty | Existing Defense Assumption | AgentForge Priority |
| --- | --- | --- | --- | --- | --- |
| Prompt injection | Direct user prompts, hidden instructions in uploaded text, multi-turn override attempts | Assistant ignores clinical boundaries or reveals internal instructions | Medium | System prompt and refusal policy | High |
| Data exfiltration | Chart summaries, patient lookup, retrieval context, prior user context | PHI leakage, cross-patient exposure, authorization bypass | High | Server-side auth and scoped retrieval | Critical |
| State corruption | Conversation memory, role assertions, poisoned summaries | Persistent false assumptions and unsafe later responses | Medium | Stateless auth and bounded memory | High |
| Tool misuse | Tool parameters, wildcard lookup, recursive calls | Unsafe backend actions even if text response appears safe | Medium | Tool schema validation | High |
| Denial of service | Long output requests, recursive expansion, repeated retrieval | Cost amplification, latency, degraded service | Low to Medium | Token/output limits | Medium |
| Identity and role exploitation | Persona claims, emergency access claims, admin impersonation | Privilege escalation and trust boundary violations | Medium | Auth from session, not prompt | High |

## Trust Boundaries

- User text is untrusted.
- Uploaded or retrieved content is untrusted.
- Conversation memory is untrusted unless derived from server-verified state.
- Tool calls must be authorized outside the LLM.
- Target URL must remain allowlisted.
- Target probes must remain benign and limited to the authorized authorized target deployment.
- Critical-severity findings require an explicit Layer 7 approval decision.
- Observability traces must not store full PHI payloads; they store summaries and IDs.
- Critical reports require human approval.
- Vulnerability and budget state are persisted in shared state so review decisions are auditable.

## Initial Regression Categories

The MVP includes seed cases for all six required categories and prioritizes at least three during smoke and scheduled campaigns. Confirmed or partial findings are written into the report queue and should remain regression candidates until the target produces safe behavior repeatedly.
