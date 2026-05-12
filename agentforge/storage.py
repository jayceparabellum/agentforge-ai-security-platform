from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable, List

from agentforge.config import get_settings
from agentforge.models import (
    AgentEvent,
    AgentTransition,
    AttackCase,
    AttackResult,
    FuzzCase,
    HumanApproval,
    LangfuseTrace,
    RegressionReplayResult,
    TargetProbeResult,
    TargetProfile,
    ThreatFeedItem,
    TokenBudgetEntry,
    Verdict,
    VulnerabilityReport,
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  campaign_id TEXT NOT NULL,
  agent TEXT NOT NULL,
  action TEXT NOT NULL,
  detail TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attack_results (
  case_id TEXT NOT NULL,
  campaign_id TEXT NOT NULL,
  category TEXT NOT NULL,
  payload_sequence TEXT NOT NULL,
  target_status_code INTEGER,
  target_response_excerpt TEXT NOT NULL,
  transport_error TEXT,
  observed_behavior TEXT NOT NULL,
  token_estimate INTEGER NOT NULL,
  cost_estimate_usd REAL NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (case_id, campaign_id)
);
CREATE TABLE IF NOT EXISTS verdicts (
  result_id TEXT PRIMARY KEY,
  verdict TEXT NOT NULL,
  severity INTEGER NOT NULL,
  confidence REAL NOT NULL,
  rationale TEXT NOT NULL,
  should_regress INTEGER NOT NULL,
  human_review_required INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS vulnerability_reports (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL,
  campaign_id TEXT NOT NULL,
  title TEXT NOT NULL,
  severity INTEGER NOT NULL,
  status TEXT NOT NULL,
  markdown_path TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS threat_feed_items (
  source TEXT NOT NULL,
  external_id TEXT NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  url TEXT NOT NULL,
  category TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  PRIMARY KEY (source, external_id)
);
CREATE TABLE IF NOT EXISTS threat_attack_cases (
  id TEXT PRIMARY KEY,
  category TEXT NOT NULL,
  subcategory TEXT NOT NULL,
  sequence TEXT NOT NULL,
  expected_safe_behavior TEXT NOT NULL,
  severity INTEGER NOT NULL,
  exploitability TEXT NOT NULL,
  regression_candidate INTEGER NOT NULL,
  source TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS coverage_map (
  category TEXT PRIMARY KEY,
  seed_count INTEGER NOT NULL,
  generated_count INTEGER NOT NULL,
  last_refreshed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS token_budget_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  campaign_id TEXT NOT NULL,
  agent TEXT NOT NULL,
  action TEXT NOT NULL,
  estimated_tokens INTEGER NOT NULL,
  estimated_cost_usd REAL NOT NULL,
  budget_usd REAL NOT NULL,
  threshold TEXT NOT NULL,
  detail TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_transitions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  campaign_id TEXT NOT NULL,
  from_node TEXT NOT NULL,
  to_node TEXT NOT NULL,
  status TEXT NOT NULL,
  message_type TEXT NOT NULL,
  payload_summary TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fuzz_cases (
  id TEXT PRIMARY KEY,
  parent_case_id TEXT NOT NULL,
  category TEXT NOT NULL,
  operator TEXT NOT NULL,
  sequence TEXT NOT NULL,
  expected_safe_behavior TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS regression_replay_results (
  id TEXT PRIMARY KEY,
  source_case_id TEXT NOT NULL,
  campaign_id TEXT NOT NULL,
  category TEXT NOT NULL,
  status TEXT NOT NULL,
  target_status_code INTEGER,
  transport_error TEXT,
  response_excerpt TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS target_profiles (
  name TEXT PRIMARY KEY,
  base_url TEXT NOT NULL,
  chat_path TEXT NOT NULL,
  allowlisted INTEGER NOT NULL,
  host TEXT NOT NULL,
  environment TEXT NOT NULL,
  integration_status TEXT NOT NULL,
  notes TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS target_probe_results (
  id TEXT PRIMARY KEY,
  target_url TEXT NOT NULL,
  path TEXT NOT NULL,
  method TEXT NOT NULL,
  status_code INTEGER,
  reachable INTEGER NOT NULL,
  likely_chat_endpoint INTEGER NOT NULL,
  response_excerpt TEXT NOT NULL,
  error TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS langfuse_traces (
  id TEXT PRIMARY KEY,
  campaign_id TEXT NOT NULL,
  agent TEXT NOT NULL,
  span_name TEXT NOT NULL,
  event_type TEXT NOT NULL,
  status TEXT NOT NULL,
  input_summary TEXT NOT NULL,
  output_summary TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS human_approvals (
  id TEXT PRIMARY KEY,
  report_id TEXT NOT NULL,
  campaign_id TEXT NOT NULL,
  case_id TEXT NOT NULL,
  severity INTEGER NOT NULL,
  reason TEXT NOT NULL,
  status TEXT NOT NULL,
  decided_by TEXT,
  notes TEXT NOT NULL,
  created_at TEXT NOT NULL,
  decided_at TEXT
);
"""


def db_path() -> Path:
    return Path(get_settings().database_path)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def record_event(event: AgentEvent) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO events (campaign_id, agent, action, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                event.campaign_id,
                event.agent,
                event.action,
                json.dumps(event.detail),
                event.created_at.isoformat(),
            ),
        )


def save_attack_result(result: AttackResult) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO attack_results
            (case_id, campaign_id, category, payload_sequence, target_status_code, target_response_excerpt,
             transport_error, observed_behavior, token_estimate, cost_estimate_usd, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.case_id,
                result.campaign_id,
                result.category.value,
                json.dumps(result.payload_sequence),
                result.target_status_code,
                result.target_response_excerpt,
                result.transport_error,
                result.observed_behavior,
                result.token_estimate,
                result.cost_estimate_usd,
                result.created_at.isoformat(),
            ),
        )


def save_verdict(verdict: Verdict) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO verdicts
            (result_id, verdict, severity, confidence, rationale, should_regress, human_review_required)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                verdict.result_id,
                verdict.verdict,
                verdict.severity,
                verdict.confidence,
                verdict.rationale,
                int(verdict.should_regress),
                int(verdict.human_review_required),
            ),
        )


def save_report(report: VulnerabilityReport) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO vulnerability_reports
            (id, case_id, campaign_id, title, severity, status, markdown_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report.id,
                report.case_id,
                report.campaign_id,
                report.title,
                report.severity,
                report.status,
                report.markdown_path,
                report.created_at.isoformat(),
            ),
        )


def record_budget_entry(entry: TokenBudgetEntry) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO token_budget_ledger
            (campaign_id, agent, action, estimated_tokens, estimated_cost_usd,
             budget_usd, threshold, detail, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.campaign_id,
                entry.agent,
                entry.action,
                entry.estimated_tokens,
                entry.estimated_cost_usd,
                entry.budget_usd,
                entry.threshold,
                json.dumps(entry.detail),
                entry.created_at.isoformat(),
            ),
        )


def record_agent_transition(transition: AgentTransition) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO agent_transitions
            (campaign_id, from_node, to_node, status, message_type, payload_summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transition.campaign_id,
                transition.from_node,
                transition.to_node,
                transition.status,
                transition.message_type,
                json.dumps(transition.payload_summary),
                transition.created_at.isoformat(),
            ),
        )


def record_trace(trace: LangfuseTrace) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO langfuse_traces
            (id, campaign_id, agent, span_name, event_type, status, input_summary, output_summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trace.id,
                trace.campaign_id,
                trace.agent,
                trace.span_name,
                trace.event_type,
                trace.status,
                json.dumps(trace.input_summary),
                json.dumps(trace.output_summary),
                trace.created_at.isoformat(),
            ),
        )


def create_approval_gate(report: VulnerabilityReport, reason: str) -> HumanApproval:
    approval = HumanApproval(
        report_id=report.id,
        campaign_id=report.campaign_id,
        case_id=report.case_id,
        severity=report.severity,
        reason=reason,
    )
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO human_approvals
            (id, report_id, campaign_id, case_id, severity, reason, status, decided_by, notes, created_at, decided_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                approval.id,
                approval.report_id,
                approval.campaign_id,
                approval.case_id,
                approval.severity,
                approval.reason,
                approval.status,
                approval.decided_by,
                approval.notes,
                approval.created_at.isoformat(),
                approval.decided_at.isoformat() if approval.decided_at else None,
            ),
        )
    return approval


def decide_approval(approval_id: str, status: str, decided_by: str = "human-review", notes: str = "") -> dict:
    if status not in {"approved", "rejected"}:
        raise ValueError("Approval status must be approved or rejected")
    with connect() as conn:
        conn.execute(
            """
            UPDATE human_approvals
            SET status = ?, decided_by = ?, notes = ?, decided_at = datetime('now')
            WHERE id = ?
            """,
            (status, decided_by, notes, approval_id),
        )
        row = conn.execute("SELECT * FROM human_approvals WHERE id = ?", (approval_id,)).fetchone()
    if row is None:
        return {"updated": False, "approval": None}
    return {"updated": True, "approval": dict(row)}


def fetch_approval_queue(limit: int = 100) -> dict:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT ha.*, vr.title, vr.markdown_path
            FROM human_approvals ha
            LEFT JOIN vulnerability_reports vr ON vr.id = ha.report_id
            ORDER BY
              CASE ha.status WHEN 'pending' THEN 0 WHEN 'approved' THEN 1 ELSE 2 END,
              ha.severity DESC,
              ha.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        summary = conn.execute(
            "SELECT status, COUNT(*) AS count FROM human_approvals GROUP BY status ORDER BY status"
        ).fetchall()
    return {"approvals": [dict(row) for row in rows], "summary": [dict(row) for row in summary]}


def fetch_observability(limit: int = 100) -> dict:
    with connect() as conn:
        traces = conn.execute("SELECT * FROM langfuse_traces ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        trace_summary = conn.execute(
            """
            SELECT agent, event_type, status, COUNT(*) AS count
            FROM langfuse_traces
            GROUP BY agent, event_type, status
            ORDER BY agent, event_type, status
            """
        ).fetchall()
        coverage = conn.execute("SELECT * FROM coverage_map ORDER BY category").fetchall()
        verdicts = conn.execute("SELECT verdict, COUNT(*) AS count FROM verdicts GROUP BY verdict ORDER BY verdict").fetchall()
        transitions = conn.execute(
            """
            SELECT to_node AS node, status, COUNT(*) AS count
            FROM agent_transitions
            GROUP BY to_node, status
            ORDER BY node, status
            """
        ).fetchall()
    return {
        "traces": [dict(row) for row in traces],
        "trace_summary": [dict(row) for row in trace_summary],
        "coverage_map": [dict(row) for row in coverage],
        "verdict_summary": [dict(row) for row in verdicts],
        "transition_summary": [dict(row) for row in transitions],
    }


def fetch_agent_transitions(campaign_id: str | None = None, limit: int = 100) -> dict:
    with connect() as conn:
        if campaign_id:
            rows = conn.execute(
                "SELECT * FROM agent_transitions WHERE campaign_id = ? ORDER BY id ASC LIMIT ?",
                (campaign_id, limit),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM agent_transitions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        node_rows = conn.execute(
            """
            SELECT to_node AS node, status, COUNT(*) AS count
            FROM agent_transitions
            GROUP BY to_node, status
            ORDER BY to_node, status
            """
        ).fetchall()
    return {
        "transitions": [dict(row) for row in rows],
        "node_counts": [dict(row) for row in node_rows],
    }


def save_fuzz_cases(cases: List[FuzzCase]) -> None:
    with connect() as conn:
        for case in cases:
            conn.execute(
                """
                INSERT OR REPLACE INTO fuzz_cases
                (id, parent_case_id, category, operator, sequence, expected_safe_behavior, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    case.id,
                    case.parent_case_id,
                    case.category.value,
                    case.operator,
                    json.dumps(case.sequence),
                    case.expected_safe_behavior,
                    case.created_at.isoformat(),
                ),
            )


def save_regression_result(result: RegressionReplayResult) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO regression_replay_results
            (id, source_case_id, campaign_id, category, status, target_status_code,
             transport_error, response_excerpt, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.id,
                result.source_case_id,
                result.campaign_id,
                result.category.value,
                result.status,
                result.target_status_code,
                result.transport_error,
                result.response_excerpt,
                result.created_at.isoformat(),
            ),
        )


def fetch_layer4_state(limit: int = 100) -> dict:
    with connect() as conn:
        fuzz_rows = conn.execute("SELECT * FROM fuzz_cases ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        fuzz_summary = conn.execute(
            "SELECT category, operator, COUNT(*) AS count FROM fuzz_cases GROUP BY category, operator ORDER BY category, operator"
        ).fetchall()
        replay_rows = conn.execute(
            "SELECT * FROM regression_replay_results ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        replay_summary = conn.execute(
            "SELECT status, COUNT(*) AS count FROM regression_replay_results GROUP BY status ORDER BY status"
        ).fetchall()
    return {
        "fuzz_cases": [dict(row) for row in fuzz_rows],
        "fuzz_summary": [dict(row) for row in fuzz_summary],
        "regression_results": [dict(row) for row in replay_rows],
        "regression_summary": [dict(row) for row in replay_summary],
    }


def save_target_profile(profile: TargetProfile) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO target_profiles
            (name, base_url, chat_path, allowlisted, host, environment, integration_status, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile.name,
                profile.base_url,
                profile.chat_path,
                int(profile.allowlisted),
                profile.host,
                profile.environment,
                profile.integration_status,
                profile.notes,
                profile.updated_at.isoformat(),
            ),
        )


def save_target_probe_results(results: List[TargetProbeResult]) -> None:
    with connect() as conn:
        for result in results:
            conn.execute(
                """
                INSERT OR REPLACE INTO target_probe_results
                (id, target_url, path, method, status_code, reachable, likely_chat_endpoint,
                 response_excerpt, error, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.id,
                    result.target_url,
                    result.path,
                    result.method,
                    result.status_code,
                    int(result.reachable),
                    int(result.likely_chat_endpoint),
                    result.response_excerpt,
                    result.error,
                    result.created_at.isoformat(),
                ),
            )


def fetch_target_state(limit: int = 50) -> dict:
    target_url = str(get_settings().target_base_url).rstrip("/")
    with connect() as conn:
        profiles = conn.execute(
            "SELECT * FROM target_profiles WHERE base_url = ? ORDER BY updated_at DESC",
            (target_url,),
        ).fetchall()
        probes = conn.execute(
            "SELECT * FROM target_probe_results WHERE target_url = ? ORDER BY created_at DESC LIMIT ?",
            (target_url, limit),
        ).fetchall()
        summary = conn.execute(
            """
            SELECT method,
                   path,
                   COUNT(*) AS count,
                   MAX(status_code) AS last_status_code,
                   MAX(reachable) AS reachable,
                   MAX(likely_chat_endpoint) AS likely_chat_endpoint,
                   MAX(created_at) AS last_checked_at
            FROM target_probe_results
            WHERE target_url = ?
            GROUP BY method, path
            ORDER BY likely_chat_endpoint DESC, reachable DESC, path
            """,
            (target_url,),
        ).fetchall()
    return {
        "profiles": [dict(row) for row in profiles],
        "probes": [dict(row) for row in probes],
        "summary": [dict(row) for row in summary],
    }


def save_threat_intel_state(items: List[ThreatFeedItem], cases: List[AttackCase]) -> None:
    with connect() as conn:
        for item in items:
            conn.execute(
                """
                INSERT OR REPLACE INTO threat_feed_items
                (source, external_id, title, summary, url, category, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.source,
                    item.external_id,
                    item.title,
                    item.summary,
                    item.url,
                    item.category.value,
                    item.fetched_at.isoformat(),
                ),
            )
        for case in cases:
            conn.execute(
                """
                INSERT OR REPLACE INTO threat_attack_cases
                (id, category, subcategory, sequence, expected_safe_behavior, severity,
                 exploitability, regression_candidate, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    case.id,
                    case.category.value,
                    case.subcategory,
                    json.dumps(case.sequence),
                    case.expected_safe_behavior,
                    case.severity,
                    case.exploitability,
                    int(case.regression_candidate),
                    case.source,
                ),
            )
        coverage_rows = conn.execute(
            """
            SELECT category,
                   SUM(CASE WHEN source LIKE '%: %' THEN 1 ELSE 0 END) AS generated_count,
                   COUNT(*) AS total_count
            FROM threat_attack_cases
            GROUP BY category
            """
        ).fetchall()
        for row in coverage_rows:
            generated_count = int(row["generated_count"] or 0)
            total_count = int(row["total_count"] or 0)
            conn.execute(
                """
                INSERT OR REPLACE INTO coverage_map
                (category, seed_count, generated_count, last_refreshed_at)
                VALUES (?, ?, ?, datetime('now'))
                """,
                (row["category"], total_count - generated_count, generated_count),
            )


def fetch_generated_threat_cases() -> List[AttackCase]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM threat_attack_cases ORDER BY severity DESC, category, id").fetchall()
    return [
        AttackCase(
            id=row["id"],
            category=row["category"],
            subcategory=row["subcategory"],
            sequence=json.loads(row["sequence"]),
            expected_safe_behavior=row["expected_safe_behavior"],
            severity=row["severity"],
            exploitability=row["exploitability"],
            regression_candidate=bool(row["regression_candidate"]),
            source=row["source"],
        )
        for row in rows
    ]


def fetch_threat_intel_state(limit: int = 50) -> dict:
    with connect() as conn:
        sources = conn.execute(
            "SELECT source, COUNT(*) AS count, MAX(fetched_at) AS last_fetched_at FROM threat_feed_items GROUP BY source ORDER BY source"
        ).fetchall()
        coverage = conn.execute("SELECT * FROM coverage_map ORDER BY category").fetchall()
        items = conn.execute(
            "SELECT * FROM threat_feed_items ORDER BY fetched_at DESC, source, external_id LIMIT ?",
            (limit,),
        ).fetchall()
        cases = conn.execute(
            "SELECT * FROM threat_attack_cases ORDER BY severity DESC, category, id LIMIT ?",
            (limit,),
        ).fetchall()
    return {
        "sources": [dict(row) for row in sources],
        "coverage_map": [dict(row) for row in coverage],
        "feed_items": [dict(row) for row in items],
        "generated_cases": [dict(row) for row in cases],
    }


def fetch_vulnerability_db(limit: int = 100) -> dict:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT vr.id,
                   vr.title,
                   vr.severity,
                   vr.status,
                   vr.markdown_path,
                   vr.created_at,
                   ar.case_id,
                   ar.campaign_id,
                   ar.category,
                   ar.observed_behavior,
                   ar.transport_error,
                   v.verdict,
                   v.confidence,
                   v.rationale,
                   v.should_regress,
                   v.human_review_required
            FROM vulnerability_reports vr
            LEFT JOIN attack_results ar
              ON ar.case_id = vr.case_id AND ar.campaign_id = vr.campaign_id
            LEFT JOIN verdicts v
              ON v.result_id = vr.case_id || ':' || vr.campaign_id
            ORDER BY vr.severity DESC, vr.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        status_rows = conn.execute(
            "SELECT status, COUNT(*) AS count FROM vulnerability_reports GROUP BY status ORDER BY status"
        ).fetchall()
        severity_rows = conn.execute(
            "SELECT severity, COUNT(*) AS count FROM vulnerability_reports GROUP BY severity ORDER BY severity DESC"
        ).fetchall()
    return {
        "findings": [dict(row) for row in rows],
        "status_counts": [dict(row) for row in status_rows],
        "severity_counts": [dict(row) for row in severity_rows],
    }


def fetch_token_budget_ledger(campaign_id: str | None = None, limit: int = 100) -> dict:
    with connect() as conn:
        if campaign_id:
            rows = conn.execute(
                "SELECT * FROM token_budget_ledger WHERE campaign_id = ? ORDER BY id DESC LIMIT ?",
                (campaign_id, limit),
            ).fetchall()
            summary_rows = conn.execute(
                """
                SELECT campaign_id,
                       agent,
                       SUM(estimated_tokens) AS estimated_tokens,
                       SUM(estimated_cost_usd) AS estimated_cost_usd,
                       MAX(budget_usd) AS budget_usd,
                       MAX(CASE threshold WHEN 'halt' THEN 2 WHEN 'warning' THEN 1 ELSE 0 END) AS max_threshold
                FROM token_budget_ledger
                WHERE campaign_id = ?
                GROUP BY campaign_id, agent
                ORDER BY estimated_cost_usd DESC
                """,
                (campaign_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM token_budget_ledger ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            summary_rows = conn.execute(
                """
                SELECT campaign_id,
                       agent,
                       SUM(estimated_tokens) AS estimated_tokens,
                       SUM(estimated_cost_usd) AS estimated_cost_usd,
                       MAX(budget_usd) AS budget_usd,
                       MAX(CASE threshold WHEN 'halt' THEN 2 WHEN 'warning' THEN 1 ELSE 0 END) AS max_threshold
                FROM token_budget_ledger
                GROUP BY campaign_id, agent
                ORDER BY campaign_id DESC, estimated_cost_usd DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    threshold_names = {0: "normal", 1: "warning", 2: "halt"}
    return {
        "entries": [dict(row) for row in rows],
        "summary": [
            {
                **{key: row[key] for key in row.keys() if key != "max_threshold"},
                "threshold": threshold_names.get(row["max_threshold"], "normal"),
            }
            for row in summary_rows
        ],
    }


def fetch_dashboard() -> dict:
    with connect() as conn:
        category_rows = conn.execute(
            "SELECT category, COUNT(*) AS count FROM attack_results GROUP BY category ORDER BY category"
        ).fetchall()
        verdict_rows = conn.execute("SELECT verdict, COUNT(*) AS count FROM verdicts GROUP BY verdict").fetchall()
        reports = conn.execute("SELECT * FROM vulnerability_reports ORDER BY created_at DESC LIMIT 20").fetchall()
        events = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT 30").fetchall()
        threat_sources = conn.execute(
            "SELECT source, COUNT(*) AS count, MAX(fetched_at) AS last_fetched_at FROM threat_feed_items GROUP BY source ORDER BY source"
        ).fetchall()
        coverage_map = conn.execute("SELECT * FROM coverage_map ORDER BY category").fetchall()
        budget_rows = conn.execute(
            """
            SELECT campaign_id,
                   SUM(estimated_tokens) AS estimated_tokens,
                   SUM(estimated_cost_usd) AS estimated_cost_usd,
                   MAX(budget_usd) AS budget_usd,
                   MAX(CASE threshold WHEN 'halt' THEN 2 WHEN 'warning' THEN 1 ELSE 0 END) AS max_threshold
            FROM token_budget_ledger
            GROUP BY campaign_id
            ORDER BY MAX(created_at) DESC
            LIMIT 10
            """
        ).fetchall()
        transition_rows = conn.execute(
            """
            SELECT to_node AS node, status, COUNT(*) AS count
            FROM agent_transitions
            GROUP BY to_node, status
            ORDER BY to_node, status
            """
        ).fetchall()
        fuzz_summary = conn.execute(
            "SELECT category, COUNT(*) AS count FROM fuzz_cases GROUP BY category ORDER BY category"
        ).fetchall()
        replay_summary = conn.execute(
            "SELECT status, COUNT(*) AS count FROM regression_replay_results GROUP BY status ORDER BY status"
        ).fetchall()
        target_url = str(get_settings().target_base_url).rstrip("/")
        target_profiles = conn.execute(
            "SELECT * FROM target_profiles WHERE base_url = ? ORDER BY updated_at DESC LIMIT 3",
            (target_url,),
        ).fetchall()
        target_probe_summary = conn.execute(
            """
            SELECT method,
                   path,
                   MAX(status_code) AS last_status_code,
                   MAX(reachable) AS reachable,
                   MAX(likely_chat_endpoint) AS likely_chat_endpoint,
                   MAX(created_at) AS last_checked_at
            FROM target_probe_results
            WHERE target_url = ?
            GROUP BY method, path
            ORDER BY likely_chat_endpoint DESC, reachable DESC, path
            LIMIT 12
            """,
            (target_url,),
        ).fetchall()
        trace_summary = conn.execute(
            """
            SELECT agent, event_type, status, COUNT(*) AS count
            FROM langfuse_traces
            GROUP BY agent, event_type, status
            ORDER BY agent, event_type, status
            LIMIT 20
            """
        ).fetchall()
        approval_rows = conn.execute(
            """
            SELECT ha.*, vr.title
            FROM human_approvals ha
            LEFT JOIN vulnerability_reports vr ON vr.id = ha.report_id
            ORDER BY
              CASE ha.status WHEN 'pending' THEN 0 WHEN 'approved' THEN 1 ELSE 2 END,
              ha.severity DESC,
              ha.created_at DESC
            LIMIT 10
            """
        ).fetchall()
        approval_summary = conn.execute(
            "SELECT status, COUNT(*) AS count FROM human_approvals GROUP BY status ORDER BY status"
        ).fetchall()
        cost = conn.execute("SELECT COALESCE(SUM(cost_estimate_usd), 0) AS cost FROM attack_results").fetchone()["cost"]
        last = conn.execute("SELECT campaign_id FROM events ORDER BY id DESC LIMIT 1").fetchone()
    verdict_counts = {row["verdict"]: row["count"] for row in verdict_rows}
    return {
        "category_counts": {row["category"]: row["count"] for row in category_rows},
        "pass_count": verdict_counts.get("pass", 0),
        "fail_count": verdict_counts.get("fail", 0),
        "partial_count": verdict_counts.get("partial", 0),
        "open_vulnerabilities": sum(1 for row in reports if row["status"] in {"open", "human_review"}),
        "estimated_cost_usd": round(float(cost), 4),
        "last_campaign_id": last["campaign_id"] if last else None,
        "reports": [dict(row) for row in reports],
        "events": [dict(row) for row in events],
        "threat_sources": [dict(row) for row in threat_sources],
        "coverage_map": [dict(row) for row in coverage_map],
        "budget_ledger": [
            {
                "campaign_id": row["campaign_id"],
                "estimated_tokens": row["estimated_tokens"],
                "estimated_cost_usd": round(float(row["estimated_cost_usd"] or 0), 6),
                "budget_usd": row["budget_usd"],
                "threshold": {0: "normal", 1: "warning", 2: "halt"}.get(row["max_threshold"], "normal"),
            }
            for row in budget_rows
        ],
        "agent_transitions": [dict(row) for row in transition_rows],
        "fuzz_summary": [dict(row) for row in fuzz_summary],
        "regression_summary": [dict(row) for row in replay_summary],
        "target_profiles": [dict(row) for row in target_profiles],
        "target_probe_summary": [dict(row) for row in target_probe_summary],
        "trace_summary": [dict(row) for row in trace_summary],
        "approval_queue": [dict(row) for row in approval_rows],
        "approval_summary": [dict(row) for row in approval_summary],
    }


def iter_confirmed_failures() -> Iterable[sqlite3.Row]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT ar.*, v.verdict, v.severity, v.confidence, v.rationale
            FROM attack_results ar
            JOIN verdicts v ON v.result_id = ar.case_id || ':' || ar.campaign_id
            WHERE v.verdict IN ('fail', 'partial') AND v.should_regress = 1
            ORDER BY ar.created_at DESC
            """
        ).fetchall()
    return rows
