from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI
from fastapi.responses import HTMLResponse

from agentforge.agents.threat_intel import ThreatIntelAgent
from agentforge.campaign import run_campaign
from agentforge.config import get_settings
from agentforge.deterministic import run_fuzzer, run_regression_replay
from agentforge.storage import (
    decide_approval,
    fetch_agent_transitions,
    fetch_approval_queue,
    fetch_dashboard,
    fetch_layer4_state,
    fetch_observability,
    fetch_target_state,
    fetch_threat_intel_state,
    fetch_token_budget_ledger,
    fetch_vulnerability_db,
)
from agentforge.target import TargetClient

app = FastAPI(title="AgentForge AI Security Platform", version="0.1.0")


@app.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "service": "agentforge-ai-security-platform",
        "target_base_url": str(settings.target_base_url),
    }


@app.get("/api/target")
def target_state() -> dict:
    return fetch_target_state()


@app.post("/api/target/probe")
async def target_probe() -> dict:
    return await TargetClient(get_settings()).probe()


@app.get("/api/dashboard")
def dashboard_api() -> dict:
    return fetch_dashboard()


@app.post("/api/campaigns/run")
async def run_campaign_endpoint(intensity: str = "smoke") -> dict:
    return await run_campaign(intensity=intensity)


@app.post("/api/campaigns/schedule-trigger")
async def schedule_trigger(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(run_campaign, "scheduled")
    return {"queued": True, "cadence": get_settings().agentforge_campaign_cadence}


@app.post("/api/threat-intel/refresh")
def refresh_threat_intel() -> dict:
    return ThreatIntelAgent().refresh().model_dump(mode="json")


@app.get("/api/threat-intel/state")
def threat_intel_state() -> dict:
    return fetch_threat_intel_state()


@app.get("/api/vulnerabilities")
def vulnerability_db() -> dict:
    return fetch_vulnerability_db()


@app.get("/api/budget-ledger")
def budget_ledger(campaign_id: str | None = None) -> dict:
    return fetch_token_budget_ledger(campaign_id=campaign_id)


@app.get("/api/agent-transitions")
def agent_transitions(campaign_id: str | None = None) -> dict:
    return fetch_agent_transitions(campaign_id=campaign_id)


@app.get("/api/provider-routes")
def provider_routes() -> dict:
    return get_settings().provider_routes


@app.get("/api/observability")
def observability() -> dict:
    return fetch_observability()


@app.get("/api/approvals")
def approvals() -> dict:
    return fetch_approval_queue()


@app.post("/api/approvals/{approval_id}/approve")
def approve_finding(approval_id: str, notes: str = "") -> dict:
    return decide_approval(approval_id, "approved", notes=notes)


@app.post("/api/approvals/{approval_id}/reject")
def reject_finding(approval_id: str, notes: str = "") -> dict:
    return decide_approval(approval_id, "rejected", notes=notes)


@app.get("/api/layer4")
def layer4_state() -> dict:
    return fetch_layer4_state()


@app.post("/api/layer4/fuzz")
def layer4_fuzz(max_cases: int = 12) -> dict:
    return run_fuzzer(max_cases=max_cases)


@app.post("/api/layer4/regression")
async def layer4_regression(intensity: str = "smoke") -> dict:
    return await run_regression_replay(intensity=intensity)


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    data = fetch_dashboard()
    reports = "".join(
        f"<tr><td>{row['id']}</td><td>{row['severity']}</td><td>{row['status']}</td><td>{row['title']}</td></tr>"
        for row in data["reports"]
    ) or "<tr><td colspan='4'>No reports yet. Run a campaign to populate review findings.</td></tr>"
    events = "".join(
        f"<li><strong>{row['agent']}</strong> {row['action']} <code>{row['campaign_id']}</code></li>"
        for row in data["events"][:10]
    ) or "<li>No agent events recorded yet.</li>"
    categories = "".join(
        f"<div class='metric'><span>{category.replace('_', ' ')}</span><strong>{count}</strong></div>"
        for category, count in data["category_counts"].items()
    ) or "<div class='metric'><span>Coverage</span><strong>0</strong></div>"
    threat_sources = "".join(
        f"<tr><td>{row['source']}</td><td>{row['count']}</td><td>{row['last_fetched_at']}</td></tr>"
        for row in data["threat_sources"]
    ) or "<tr><td colspan='3'>No threat feed data loaded yet. Refresh Layer 1 to populate shared state.</td></tr>"
    coverage_rows = "".join(
        f"<tr><td>{row['category'].replace('_', ' ')}</td><td>{row['seed_count']}</td><td>{row['generated_count']}</td><td>{row['last_refreshed_at']}</td></tr>"
        for row in data["coverage_map"]
    ) or "<tr><td colspan='4'>No coverage map data yet.</td></tr>"
    budget_rows = "".join(
        f"<tr><td>{row['campaign_id']}</td><td>{row['estimated_tokens']}</td><td>${row['estimated_cost_usd']}</td><td>${row['budget_usd']}</td><td>{row['threshold']}</td></tr>"
        for row in data["budget_ledger"]
    ) or "<tr><td colspan='5'>No token budget ledger entries yet.</td></tr>"
    transition_rows = "".join(
        f"<tr><td>{row['node']}</td><td>{row['status']}</td><td>{row['count']}</td></tr>"
        for row in data["agent_transitions"]
    ) or "<tr><td colspan='3'>No Layer 2 transitions recorded yet.</td></tr>"
    provider_rows = "".join(
        f"<tr><td>{agent}</td><td>{route['provider']}</td><td>{route['model']}</td><td>{route['data_path']}</td></tr>"
        for agent, route in get_settings().provider_routes.items()
    )
    fuzz_rows = "".join(
        f"<tr><td>{row['category'].replace('_', ' ')}</td><td>{row['count']}</td></tr>"
        for row in data["fuzz_summary"]
    ) or "<tr><td colspan='2'>No fuzz cases generated yet.</td></tr>"
    replay_rows = "".join(
        f"<tr><td>{row['status']}</td><td>{row['count']}</td></tr>"
        for row in data["regression_summary"]
    ) or "<tr><td colspan='2'>No regression replay results yet.</td></tr>"
    target_profile_rows = "".join(
        f"<tr><td>{row['name']}</td><td>{row['base_url']}</td><td>{row['chat_path']}</td><td>{row['integration_status']}</td><td>{row['notes']}</td></tr>"
        for row in data["target_profiles"]
    ) or "<tr><td colspan='5'>No target profile recorded yet. Run a target probe.</td></tr>"
    target_probe_rows = "".join(
        f"<tr><td>{row['method']}</td><td>{row['path']}</td><td>{row['last_status_code']}</td><td>{bool(row['reachable'])}</td><td>{bool(row['likely_chat_endpoint'])}</td></tr>"
        for row in data["target_probe_summary"]
    ) or "<tr><td colspan='5'>No target probes recorded yet.</td></tr>"
    trace_rows = "".join(
        f"<tr><td>{row['agent']}</td><td>{row['event_type']}</td><td>{row['status']}</td><td>{row['count']}</td></tr>"
        for row in data["trace_summary"]
    ) or "<tr><td colspan='4'>No Layer 6 traces recorded yet.</td></tr>"
    approval_rows = "".join(
        f"<tr><td>{row['report_id']}</td><td>{row['severity']}</td><td>{row['status']}</td><td>{row.get('title') or ''}</td><td><button onclick=\"runControl('/api/approvals/{row['id']}/approve', this)\">Approve</button> <button onclick=\"runControl('/api/approvals/{row['id']}/reject', this)\">Reject</button></td></tr>"
        for row in data["approval_queue"]
    ) or "<tr><td colspan='5'>No critical approvals pending.</td></tr>"
    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AgentForge</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif; }}
    body {{ margin: 0; background: #f6f7f9; color: #18202a; }}
    header {{ padding: 28px 36px; background: #111827; color: white; }}
    h1 {{ margin: 0; font-size: 28px; letter-spacing: 0; }}
    header p {{ margin: 8px 0 0; color: #cbd5e1; max-width: 880px; }}
    main {{ padding: 28px 36px; display: grid; gap: 22px; }}
    section {{ background: white; border: 1px solid #dde3ea; border-radius: 8px; padding: 20px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; }}
    .metric {{ border: 1px solid #e3e8ef; border-radius: 8px; padding: 14px; background: #fbfcfd; }}
    .metric span {{ display: block; color: #526070; text-transform: capitalize; font-size: 13px; }}
    .metric strong {{ display: block; margin-top: 6px; font-size: 24px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid #e5e7eb; font-size: 14px; }}
    button {{ background: #2563eb; color: white; border: 0; border-radius: 6px; padding: 10px 14px; cursor: pointer; }}
    code {{ background: #eef2f7; padding: 2px 5px; border-radius: 4px; }}
  </style>
</head>
<body>
  <header>
    <h1>AgentForge</h1>
    <p>Multi-agent adversarial evaluation platform for the deployed OpenEMR Clinical Co-Pilot target.</p>
  </header>
  <main>
    <section>
      <h2>Campaign Controls</h2>
      <p>Target: <code>{get_settings().target_base_url}</code> | Cadence: <code>{get_settings().agentforge_campaign_cadence}</code> | Budget: <code>${get_settings().campaign_budget_usd}</code></p>
      <button onclick="runControl('/api/campaigns/run?intensity=smoke', this)">Run Smoke Campaign</button>
      <button onclick="runControl('/api/threat-intel/refresh', this)">Refresh Threat Intel</button>
      <button onclick="runControl('/api/layer4/fuzz', this)">Run Fuzzer</button>
      <button onclick="runControl('/api/layer4/regression', this)">Replay Regressions</button>
      <button onclick="runControl('/api/target/probe', this)">Probe Target</button>
      <span id="control-status" role="status"></span>
    </section>
    <section>
      <h2>Layer 5 Target System</h2>
      <table><thead><tr><th>Name</th><th>Base URL</th><th>Chat Path</th><th>Status</th><th>Notes</th></tr></thead><tbody>{target_profile_rows}</tbody></table>
      <h3>Endpoint Probes</h3>
      <table><thead><tr><th>Method</th><th>Path</th><th>Status</th><th>Reachable</th><th>Likely Chat</th></tr></thead><tbody>{target_probe_rows}</tbody></table>
    </section>
    <section>
      <h2>Coverage</h2>
      <div class="grid">
        <div class="metric"><span>Pass</span><strong>{data['pass_count']}</strong></div>
        <div class="metric"><span>Fail</span><strong>{data['fail_count']}</strong></div>
        <div class="metric"><span>Partial</span><strong>{data['partial_count']}</strong></div>
        <div class="metric"><span>Estimated Cost</span><strong>${data['estimated_cost_usd']}</strong></div>
        {categories}
      </div>
    </section>
    <section>
      <h2>Threat Intelligence Shared State</h2>
      <table><thead><tr><th>Source</th><th>Items</th><th>Last Fetched</th></tr></thead><tbody>{threat_sources}</tbody></table>
      <h3>Coverage Map</h3>
      <table><thead><tr><th>Category</th><th>Seed Cases</th><th>Generated Cases</th><th>Last Refreshed</th></tr></thead><tbody>{coverage_rows}</tbody></table>
    </section>
    <section>
      <h2>Review Queue</h2>
      <table><thead><tr><th>ID</th><th>Severity</th><th>Status</th><th>Title</th></tr></thead><tbody>{reports}</tbody></table>
    </section>
    <section>
      <h2>Layer 7 Human Trust Boundary</h2>
      <table><thead><tr><th>Report</th><th>Severity</th><th>Status</th><th>Title</th><th>Action</th></tr></thead><tbody>{approval_rows}</tbody></table>
    </section>
    <section>
      <h2>Token Budget Ledger</h2>
      <table><thead><tr><th>Campaign</th><th>Tokens</th><th>Spend</th><th>Budget</th><th>Threshold</th></tr></thead><tbody>{budget_rows}</tbody></table>
    </section>
    <section>
      <h2>Layer 2 Multi-Agent Core</h2>
      <table><thead><tr><th>Node</th><th>Status</th><th>Transitions</th></tr></thead><tbody>{transition_rows}</tbody></table>
      <h3>Provider Routes</h3>
      <table><thead><tr><th>Path</th><th>Provider</th><th>Model</th><th>Data Path</th></tr></thead><tbody>{provider_rows}</tbody></table>
    </section>
    <section>
      <h2>Layer 6 Observability</h2>
      <table><thead><tr><th>Agent</th><th>Event Type</th><th>Status</th><th>Count</th></tr></thead><tbody>{trace_rows}</tbody></table>
    </section>
    <section>
      <h2>Layer 4 Deterministic Tooling</h2>
      <h3>Fuzzer Coverage</h3>
      <table><thead><tr><th>Category</th><th>Generated Cases</th></tr></thead><tbody>{fuzz_rows}</tbody></table>
      <h3>Regression Replay</h3>
      <table><thead><tr><th>Status</th><th>Count</th></tr></thead><tbody>{replay_rows}</tbody></table>
    </section>
    <section>
      <h2>Agent Trace</h2>
      <ul>{events}</ul>
    </section>
  </main>
  <script>
    async function runControl(path, button) {{
      const status = document.getElementById('control-status');
      const original = button.textContent;
      button.disabled = true;
      button.textContent = 'Running...';
      status.textContent = '';
      try {{
        const response = await fetch(path, {{method: 'POST'}});
        if (!response.ok) {{
          const text = await response.text();
          throw new Error(`${{response.status}} ${{text.slice(0, 160)}}`);
        }}
        status.textContent = 'Complete. Refreshing...';
        location.reload();
      }} catch (error) {{
        status.textContent = `Control failed: ${{error.message}}`;
        button.disabled = false;
        button.textContent = original;
      }}
    }}
  </script>
</body>
</html>
"""
