# Users

## Primary Users

### Security Engineer

The security engineer reviews vulnerability reports, validates exploit reproduction, and decides whether a finding should become a remediation ticket. Automation is appropriate because manually prompting the Clinical Co-Pilot does not scale, is difficult to reproduce, and often misses regressions.

### AI Platform Engineer

The platform engineer owns the Clinical Co-Pilot integration, retrieval boundaries, tool schemas, and deployment behavior. AgentForge gives this user deterministic regression evidence when a prompt, retrieval, or tool-call defense changes.

### Clinical Operations Lead

The clinical operations lead needs visibility into whether the assistant is safe enough for workflow use. They do not need raw attack traces first; they need risk status, severity, clinical impact, and fix validation.

### Compliance or Security Reviewer

The compliance reviewer needs auditability: what was tested, when, against which target, and what data path each agent used. The platform’s allowlist, agent trace, and report queue support that workflow.

## Key Workflows

1. Weekly campaign runs automatically against the deployed target.
2. The dashboard populates new findings into the review queue.
3. Critical or uncertain findings are manually reviewed.
4. Confirmed findings remain in the regression harness.
5. Fixes are validated by later scheduled runs.

## Why Automation Is the Right Solution

The assignment’s problem is continuous adversarial evaluation, not a one-time demo. Automation is necessary because attack variants change, fixes regress, and manual prompting does not create durable evidence. Human review remains where judgment matters most: critical severity, low confidence, and remediation approval.

