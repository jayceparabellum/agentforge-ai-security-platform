# Second-Run Live Evidence

This folder stores raw, inspectable evidence from the second hardening pass requested for final review. The goal is to make repo separation, live target behavior, eval readiness, and replay behavior easy to inspect without relying on dashboard state.

## Files

| File | What it proves |
| --- | --- |
| `second-run-evals-2026-05-14.json` | The 50-case golden eval suite is present, valid, and at 100% readiness. |
| `second-run-target-probe-2026-05-14.json` | The allowlisted target is reachable and exposes likely chat endpoints at `/chat` and `/w2/chat`. |
| `second-run-smoke-campaign-2026-05-14.json` | A fresh live smoke campaign reached the allowlisted deployed target and produced case-level verdicts. |
| `second-run-regression-replay-2026-05-14.json` | Deterministic replay reran prior findings and kept incomplete target interactions as partial. |

## Summary

| Area | Result |
| --- | --- |
| Repo separation | No active repo evidence points back to a legacy target repository or describes this app as inherited from another codebase. |
| Target probe | Healthy, 14 probes, `/chat` and `/w2/chat` both returned HTTP 200 to benign POST probes. |
| Smoke campaign | `campaign-15e29f27`, 9 cases, 49 graph transitions, estimated cost `$0.000672`. |
| Smoke verdicts | 3 pass, 4 partial, 2 fail. |
| Regression replay | `regression-04d588cb`, 9 replayed cases, 4 HTTP 200 target responses, 5 partial timeout/incomplete attempts. |
| Golden evals | 50 validated cases across data exfiltration, denial of service, identity/role, prompt injection, state corruption, and tool misuse. |

## Review Notes

The platform treats timeouts and incomplete target interactions as `partial`. That is intentional: partial means the system has reviewable evidence but will not overclaim that the target passed or failed when the live response was ambiguous.
