# Rollback Snapshot

Current protected build:

- Commit: 1d1bd3331551b158ce27a2efe62fe77ee617ce0c
- Tag: ollback-mvp-layer123-provider-routes-2026-05-12
- Branch: snapshot/mvp-layer123-provider-routes-2026-05-12
- Local archive: /Users/jayceparabellum/Projects/_snapshots/agentforge-ai-security-platform-1d1bd33-2026-05-12.tar.gz
- Archive SHA-256: e0ec51df7994115802ed7e85f347408f502dba3e88c2c95e229e02f94da3c599

## Restore Locally From Git

`ash
cd ~/Projects/agentforge-ai-security-platform
git fetch origin --tags
git checkout -B restore/mvp rollback-mvp-layer123-provider-routes-2026-05-12
`

## Roll Main Back To This Build

Use only if you intentionally want Render to redeploy this snapshot as main.

`ash
cd ~/Projects/agentforge-ai-security-platform
git fetch origin --tags
git checkout main
git reset --hard rollback-mvp-layer123-provider-routes-2026-05-12
git push --force-with-lease origin main
`

## Restore From Archive

`ash
mkdir -p ~/Projects/restore-agentforge
cd ~/Projects/restore-agentforge
tar -xzf ~/Projects/_snapshots/agentforge-ai-security-platform-1d1bd33-2026-05-12.tar.gz
`

## Render Rollback Options

Render can redeploy a previous successful deploy from its service dashboard. If the Git history has moved forward and you need this exact source state, reset main to the rollback tag and push using the command above, then trigger a Render deploy.
