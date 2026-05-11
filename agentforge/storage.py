from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from agentforge.config import get_settings
from agentforge.models import AgentEvent, AttackResult, Verdict, VulnerabilityReport


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


def fetch_dashboard() -> dict:
    with connect() as conn:
        category_rows = conn.execute(
            "SELECT category, COUNT(*) AS count FROM attack_results GROUP BY category ORDER BY category"
        ).fetchall()
        verdict_rows = conn.execute("SELECT verdict, COUNT(*) AS count FROM verdicts GROUP BY verdict").fetchall()
        reports = conn.execute("SELECT * FROM vulnerability_reports ORDER BY created_at DESC LIMIT 20").fetchall()
        events = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT 30").fetchall()
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
