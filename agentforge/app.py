from __future__ import annotations

import html
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from agentforge.agents.threat_intel import ThreatIntelAgent
from agentforge.campaign import run_campaign
from agentforge.config import get_settings
from agentforge.deterministic import run_fuzzer, run_regression_replay
from agentforge.evaluation import evaluate_golden_cases
from agentforge.storage import (
    decide_approval,
    fetch_agent_transitions,
    fetch_approval_queue,
    fetch_dashboard,
    fetch_layer4_state,
    fetch_observability,
    fetch_report_detail,
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


@app.get("/api/evals/progress")
def eval_progress() -> dict:
    return evaluate_golden_cases(write_latest=False)


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
def budget_ledger(campaign_id: Optional[str] = None) -> dict:
    return fetch_token_budget_ledger(campaign_id=campaign_id)


@app.get("/api/agent-transitions")
def agent_transitions(campaign_id: Optional[str] = None) -> dict:
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


@app.get("/api/reports/{report_id}")
def report_detail_api(report_id: str) -> dict:
    report = fetch_report_detail(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"report": report}


@app.post("/api/approvals/{approval_id}/approve")
def approve_finding(approval_id: str, notes: str = "") -> dict:
    return decide_approval(approval_id, "approved", notes=notes)


@app.post("/api/approvals/{approval_id}/reject")
def reject_finding(approval_id: str, notes: str = "") -> dict:
    return decide_approval(approval_id, "rejected", notes=notes)


@app.get("/reports", response_class=HTMLResponse)
def reports_index() -> str:
    data = fetch_vulnerability_db(limit=200)
    report_rows = "".join(
        f"<tr><td><a href='/reports/{html.escape(row['id'])}'>{html.escape(row['id'])}</a></td>"
        f"<td>{row['severity']}</td><td>{html.escape(row['status'])}</td>"
        f"<td>{html.escape(row['title'])}</td><td>{html.escape(row.get('campaign_id') or '')}</td>"
        f"<td>{html.escape(row.get('verdict') or '')}</td></tr>"
        for row in data["findings"]
    ) or "<tr><td colspan='6'>No captured reports yet. Run a smoke campaign to generate findings.</td></tr>"
    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AgentForge Reports</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif; --blue: #1769aa; --blue-dark: #0f4c81; --line: #cfd8e3; }}
    body {{ margin: 0; background: #e9eef4; color: #1f2933; }}
    .topbar {{ background: var(--blue); color: white; height: 52px; display: flex; align-items: center; justify-content: space-between; padding: 0 22px; box-shadow: 0 1px 3px rgba(0,0,0,.18); }}
    .brand {{ font-size: 20px; font-weight: 700; letter-spacing: 0; }}
    .target {{ font-size: 13px; opacity: .92; }}
    .tabs {{ background: #f8fafc; border-bottom: 1px solid var(--line); padding: 0 22px; display: flex; gap: 2px; }}
    .tab {{ color: #24425f; padding: 13px 18px; text-decoration: none; border-left: 1px solid transparent; border-right: 1px solid transparent; font-weight: 650; }}
    .tab.active {{ background: white; color: var(--blue-dark); border-left-color: var(--line); border-right-color: var(--line); border-top: 3px solid var(--blue); padding-top: 10px; }}
    .workspace {{ display: grid; grid-template-columns: 230px minmax(0, 1fr); min-height: calc(100vh - 98px); }}
    aside {{ background: #f8fafc; border-right: 1px solid var(--line); padding: 18px 14px; }}
    aside a {{ display: block; color: #34495e; padding: 9px 10px; border-radius: 4px; text-decoration: none; font-size: 14px; }}
    aside a:hover {{ background: #e1edf7; }}
    main {{ padding: 22px; }}
    section {{ background: white; border: 1px solid var(--line); border-radius: 4px; padding: 18px; box-shadow: 0 1px 2px rgba(15, 23, 42, .05); }}
    h1 {{ margin: 0 0 12px; font-size: 22px; letter-spacing: 0; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{ background: #edf3f8; color: #30475f; }}
    th, td {{ text-align: left; padding: 9px 8px; border: 1px solid #dbe3ec; font-size: 14px; vertical-align: top; }}
    a {{ color: #1769aa; font-weight: 650; text-decoration: none; }}
    .button-link {{ display: inline-block; background: var(--blue); color: white; border-radius: 4px; padding: 9px 13px; margin-top: 14px; }}
    @media (max-width: 760px) {{ .workspace {{ grid-template-columns: 1fr; }} aside {{ display: none; }} .topbar {{ align-items: flex-start; flex-direction: column; height: auto; gap: 4px; padding: 12px 18px; }} }}
  </style>
</head>
<body>
  <div class="topbar"><div class="brand">AgentForge</div><div class="target">Target: {get_settings().target_base_url}</div></div>
  <nav class="tabs"><a class="tab" href="/">ai-security-tool</a><a class="tab active" href="/reports">Results</a></nav>
  <div class="workspace">
    <aside>
      <a href="/">Campaign Controls</a>
      <a href="/reports">Output Reports</a>
      <a href="/#review-queue">Review Queue</a>
      <a href="/#observability">Observability</a>
    </aside>
    <main>
      <section>
        <h1>Captured Output Reports</h1>
        <table><thead><tr><th>Report</th><th>Severity</th><th>Status</th><th>Title</th><th>Campaign</th><th>Verdict</th></tr></thead><tbody>{report_rows}</tbody></table>
        <a class="button-link" href="/">Back to Tool</a>
      </section>
    </main>
  </div>
</body>
</html>
"""


@app.get("/reports/{report_id}", response_class=HTMLResponse)
def report_detail(report_id: str) -> str:
    report = fetch_report_detail(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    payload_sequence = html.escape(report.get("payload_sequence") or "[]")
    markdown_content = html.escape(report.get("markdown_content") or "")
    return f"""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(report['id'])} | AgentForge</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif; --blue: #1769aa; --blue-dark: #0f4c81; --line: #cfd8e3; }}
    body {{ margin: 0; background: #e9eef4; color: #1f2933; }}
    .topbar {{ background: var(--blue); color: white; height: 52px; display: flex; align-items: center; justify-content: space-between; padding: 0 22px; box-shadow: 0 1px 3px rgba(0,0,0,.18); }}
    .brand {{ font-size: 20px; font-weight: 700; letter-spacing: 0; }}
    .target {{ font-size: 13px; opacity: .92; }}
    .tabs {{ background: #f8fafc; border-bottom: 1px solid var(--line); padding: 0 22px; display: flex; gap: 2px; }}
    .tab {{ color: #24425f; padding: 13px 18px; text-decoration: none; border-left: 1px solid transparent; border-right: 1px solid transparent; font-weight: 650; }}
    .tab.active {{ background: white; color: var(--blue-dark); border-left-color: var(--line); border-right-color: var(--line); border-top: 3px solid var(--blue); padding-top: 10px; }}
    .workspace {{ display: grid; grid-template-columns: 230px minmax(0, 1fr); min-height: calc(100vh - 98px); }}
    aside {{ background: #f8fafc; border-right: 1px solid var(--line); padding: 18px 14px; }}
    aside a {{ display: block; color: #34495e; padding: 9px 10px; border-radius: 4px; text-decoration: none; font-size: 14px; }}
    aside a:hover {{ background: #e1edf7; }}
    main {{ padding: 22px; display: grid; gap: 18px; }}
    section {{ background: white; border: 1px solid var(--line); border-radius: 4px; padding: 18px; box-shadow: 0 1px 2px rgba(15, 23, 42, .05); }}
    h1 {{ margin: 0; font-size: 22px; letter-spacing: 0; }}
    h2 {{ font-size: 17px; margin-top: 0; color: #243b53; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; }}
    .metric {{ border: 1px solid #dbe3ec; border-radius: 4px; padding: 12px; background: #fbfdff; }}
    .metric span {{ display: block; color: #526070; font-size: 13px; }}
    .metric strong {{ display: block; margin-top: 6px; font-size: 18px; overflow-wrap: anywhere; }}
    pre {{ white-space: pre-wrap; overflow-wrap: anywhere; background: #0f172a; color: #e5edf7; border-radius: 8px; padding: 18px; line-height: 1.5; }}
    a {{ color: #1769aa; font-weight: 650; text-decoration: none; }}
    .button-link {{ display: inline-block; background: var(--blue); color: white; border-radius: 4px; padding: 9px 13px; margin-right: 8px; }}
    @media (max-width: 760px) {{ .workspace {{ grid-template-columns: 1fr; }} aside {{ display: none; }} .topbar {{ align-items: flex-start; flex-direction: column; height: auto; gap: 4px; padding: 12px 18px; }} }}
  </style>
</head>
<body>
  <div class="topbar"><div class="brand">AgentForge</div><div class="target">Target: {get_settings().target_base_url}</div></div>
  <nav class="tabs"><a class="tab" href="/">ai-security-tool</a><a class="tab active" href="/reports">Results</a></nav>
  <div class="workspace">
  <aside>
    <a href="/reports">Output Reports</a>
    <a href="/">Campaign Controls</a>
    <a href="/#review-queue">Review Queue</a>
    <a href="/#observability">Observability</a>
  </aside>
  <main>
    <h1>{html.escape(report['id'])}: {html.escape(report['title'])}</h1>
    <section>
      <div class="grid">
        <div class="metric"><span>Campaign</span><strong>{html.escape(report['campaign_id'])}</strong></div>
        <div class="metric"><span>Case</span><strong>{html.escape(report['case_id'])}</strong></div>
        <div class="metric"><span>Severity</span><strong>{report['severity']}</strong></div>
        <div class="metric"><span>Status</span><strong>{html.escape(report['status'])}</strong></div>
        <div class="metric"><span>Verdict</span><strong>{html.escape(report.get('verdict') or 'unknown')}</strong></div>
        <div class="metric"><span>Approval</span><strong>{html.escape(report.get('approval_status') or 'not required')}</strong></div>
      </div>
    </section>
    <section>
      <h2>Workflow Result</h2>
      <p><strong>Observed behavior:</strong> {html.escape(report.get('observed_behavior') or '')}</p>
      <p><strong>Judge rationale:</strong> {html.escape(report.get('rationale') or '')}</p>
      <p><strong>Target status:</strong> {html.escape(str(report.get('target_status_code') or 'n/a'))}</p>
      <p><strong>Transport error:</strong> {html.escape(report.get('transport_error') or 'none')}</p>
    </section>
    <section>
      <h2>Attack Payload Sequence</h2>
      <pre>{payload_sequence}</pre>
    </section>
    <section>
      <h2>Target Response Excerpt</h2>
      <pre>{html.escape(report.get('target_response_excerpt') or '')}</pre>
    </section>
    <section>
      <h2>Markdown Report Output</h2>
      <pre>{markdown_content}</pre>
      <a class="button-link" href="/reports">All Reports</a>
      <a class="button-link" href="/">Tool</a>
    </section>
  </main>
  </div>
</body>
</html>
"""


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
        f"<tr><td><a href='/reports/{html.escape(row['id'])}'>{html.escape(row['id'])}</a></td><td>{row['severity']}</td><td>{html.escape(row['status'])}</td><td>{html.escape(row['title'])}</td><td><a href='/reports/{html.escape(row['id'])}'>View full report</a></td></tr>"
        for row in data["reports"]
    ) or "<tr><td colspan='5'>No reports yet. Run a campaign to populate review findings.</td></tr>"
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
    ) or "<tr><td colspan='3'>No threat feed data loaded yet. Refresh threat intelligence to populate shared state.</td></tr>"
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
    ) or "<tr><td colspan='3'>No agent transitions recorded yet.</td></tr>"
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
    ) or "<tr><td colspan='4'>No traces recorded yet.</td></tr>"
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
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif; --blue: #1769aa; --blue-dark: #0f4c81; --line: #cfd8e3; }}
    body {{ margin: 0; background: #e9eef4; color: #1f2933; }}
    .topbar {{ background: var(--blue); color: white; height: 52px; display: flex; align-items: center; justify-content: space-between; padding: 0 22px; box-shadow: 0 1px 3px rgba(0,0,0,.18); }}
    .brand {{ font-size: 20px; font-weight: 700; letter-spacing: 0; }}
    .target {{ font-size: 13px; opacity: .92; }}
    .tabs {{ background: #f8fafc; border-bottom: 1px solid var(--line); padding: 0 22px; display: flex; gap: 2px; }}
    .tab {{ color: #24425f; padding: 13px 18px; text-decoration: none; border-left: 1px solid transparent; border-right: 1px solid transparent; font-weight: 650; }}
    .tab.active {{ background: white; color: var(--blue-dark); border-left-color: var(--line); border-right-color: var(--line); border-top: 3px solid var(--blue); padding-top: 10px; }}
    .workspace {{ display: grid; grid-template-columns: 230px minmax(0, 1fr); min-height: calc(100vh - 98px); }}
    aside {{ background: #f8fafc; border-right: 1px solid var(--line); padding: 18px 14px; }}
    aside a {{ display: block; color: #34495e; padding: 9px 10px; border-radius: 4px; text-decoration: none; font-size: 14px; }}
    aside a:hover {{ background: #e1edf7; }}
    main {{ padding: 22px; display: grid; gap: 18px; }}
    section {{ background: white; border: 1px solid var(--line); border-radius: 4px; padding: 18px; box-shadow: 0 1px 2px rgba(15, 23, 42, .05); }}
    h1 {{ margin: 0; font-size: 22px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 12px; font-size: 18px; color: #243b53; }}
    h3 {{ margin: 16px 0 8px; font-size: 15px; color: #334e68; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }}
    .metric {{ border: 1px solid #dbe3ec; border-radius: 4px; padding: 12px; background: #fbfdff; }}
    .metric span {{ display: block; color: #526070; text-transform: capitalize; font-size: 13px; }}
    .metric strong {{ display: block; margin-top: 6px; font-size: 22px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{ background: #edf3f8; color: #30475f; }}
    th, td {{ text-align: left; padding: 9px 8px; border: 1px solid #dbe3ec; font-size: 14px; vertical-align: top; }}
    button, .button-link {{ background: var(--blue); color: white; border: 0; border-radius: 4px; padding: 9px 13px; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; min-height: 20px; font-weight: 650; }}
    .control-row {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }}
    .secondary-control {{ background: #1f6f5b; }}
    .subtle {{ color: #526070; font-size: 13px; margin-top: 0; }}
    code {{ background: #eef2f7; padding: 2px 5px; border-radius: 4px; }}
    a {{ color: #1769aa; font-weight: 650; text-decoration: none; }}
    @media (max-width: 760px) {{ .workspace {{ grid-template-columns: 1fr; }} aside {{ display: none; }} .topbar {{ align-items: flex-start; flex-direction: column; height: auto; gap: 4px; padding: 12px 18px; }} }}
  </style>
</head>
<body>
  <div class="topbar"><div class="brand">AgentForge</div><div class="target">Target: {get_settings().target_base_url}</div></div>
  <nav class="tabs"><a class="tab active" href="/">ai-security-tool</a><a class="tab" href="/reports">Results</a></nav>
  <div class="workspace">
    <aside>
      <a href="#campaign-controls">Campaign Controls</a>
      <a href="#target-system">Target System</a>
      <a href="#shared-state">Shared State</a>
      <a href="#review-queue">Review Queue</a>
      <a href="#observability">Observability</a>
      <a href="/reports">Output Reports</a>
    </aside>
  <main>
    <h1>AI Security Tool</h1>
    <section id="campaign-controls">
      <h2>Campaign Controls</h2>
      <p class="subtle">Cadence: <code>{get_settings().agentforge_campaign_cadence}</code> | Budget: <code>${get_settings().campaign_budget_usd}</code></p>
      <div class="control-row">
        <button onclick="runControl('/api/threat-intel/refresh', this)">Refresh Intel</button>
        <button onclick="runControl('/api/campaigns/run?intensity=smoke', this)">Run Agent Workflow</button>
        <a class="button-link" href="#shared-state">Shared State</a>
        <button onclick="runControl('/api/layer4/fuzz', this)">Run Fuzzer</button>
        <button class="secondary-control" onclick="runControl('/api/layer4/regression', this)">Replay Regressions</button>
        <button onclick="runControl('/api/target/probe', this)">Probe Target</button>
        <a class="button-link" href="/reports">Results</a>
      </div>
      <span id="control-status" role="status"></span>
    </section>
    <section id="target-system">
      <h2>Target System</h2>
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
        <div class="metric"><span>Total Coverage Cost Since Launch</span><strong>${data['lifetime_coverage_cost_usd']}</strong></div>
        <div class="metric"><span>Coverage Tokens Since Launch</span><strong>{data['lifetime_coverage_tokens']}</strong></div>
        {categories}
      </div>
    </section>
    <section id="shared-state">
      <h2>Threat Intelligence Shared State</h2>
      <table><thead><tr><th>Source</th><th>Items</th><th>Last Fetched</th></tr></thead><tbody>{threat_sources}</tbody></table>
      <h3>Coverage Map</h3>
      <table><thead><tr><th>Category</th><th>Seed Cases</th><th>Generated Cases</th><th>Last Refreshed</th></tr></thead><tbody>{coverage_rows}</tbody></table>
    </section>
    <section id="review-queue">
      <h2>Review Queue</h2>
      <table><thead><tr><th>ID</th><th>Severity</th><th>Status</th><th>Title</th><th>Report</th></tr></thead><tbody>{reports}</tbody></table>
    </section>
    <section>
      <h2>Human Review</h2>
      <table><thead><tr><th>Report</th><th>Severity</th><th>Status</th><th>Title</th><th>Action</th></tr></thead><tbody>{approval_rows}</tbody></table>
    </section>
    <section>
      <h2>Token Budget Ledger</h2>
      <table><thead><tr><th>Campaign</th><th>Tokens</th><th>Spend</th><th>Budget</th><th>Threshold</th></tr></thead><tbody>{budget_rows}</tbody></table>
    </section>
    <section>
      <h2>Multi-Agent Core</h2>
      <table><thead><tr><th>Node</th><th>Status</th><th>Transitions</th></tr></thead><tbody>{transition_rows}</tbody></table>
      <h3>Provider Routes</h3>
      <table><thead><tr><th>Path</th><th>Provider</th><th>Model</th><th>Data Path</th></tr></thead><tbody>{provider_rows}</tbody></table>
    </section>
    <section id="observability">
      <h2>Observability</h2>
      <table><thead><tr><th>Agent</th><th>Event Type</th><th>Status</th><th>Count</th></tr></thead><tbody>{trace_rows}</tbody></table>
    </section>
    <section>
      <h2>Deterministic Tooling</h2>
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
  </div>
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
