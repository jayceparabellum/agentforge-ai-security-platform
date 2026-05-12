from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AttackCategory(str, Enum):
    prompt_injection = "prompt_injection"
    data_exfiltration = "data_exfiltration"
    state_corruption = "state_corruption"
    tool_misuse = "tool_misuse"
    denial_of_service = "denial_of_service"
    identity_role = "identity_role"


class AttackCase(BaseModel):
    id: str
    category: AttackCategory
    subcategory: str
    sequence: List[str]
    expected_safe_behavior: str
    severity: int = Field(ge=1, le=5)
    exploitability: Literal["low", "medium", "high"]
    regression_candidate: bool = True
    source: str = "seed"


class ThreatFeedItem(BaseModel):
    source: str
    external_id: str
    title: str
    summary: str
    url: str
    category: AttackCategory
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ThreatIntelRefreshResult(BaseModel):
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_counts: Dict[str, int]
    generated_case_count: int
    snapshot_paths: List[str]
    errors: Dict[str, str] = Field(default_factory=dict)


class CampaignBrief(BaseModel):
    id: str = Field(default_factory=lambda: f"campaign-{uuid4().hex[:8]}")
    target_url: str
    categories: List[AttackCategory]
    intensity: Literal["smoke", "scheduled", "deep"] = "scheduled"
    max_cases: int = 9
    max_turns: int = 4
    budget_usd: float = 2.50
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AttackResult(BaseModel):
    case_id: str
    campaign_id: str
    category: AttackCategory
    payload_sequence: List[str]
    target_status_code: Optional[int] = None
    target_response_excerpt: str = ""
    transport_error: Optional[str] = None
    observed_behavior: str
    token_estimate: int = 0
    cost_estimate_usd: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Verdict(BaseModel):
    result_id: str
    verdict: Literal["pass", "fail", "partial"]
    severity: int = Field(ge=1, le=5)
    confidence: float = Field(ge=0, le=1)
    rationale: str
    should_regress: bool
    human_review_required: bool = False


class VulnerabilityReport(BaseModel):
    id: str = Field(default_factory=lambda: f"AF-{uuid4().hex[:6].upper()}")
    case_id: str
    campaign_id: str
    title: str
    severity: int
    status: Literal["open", "human_review", "resolved", "accepted_risk"] = "open"
    markdown_path: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TokenBudgetEntry(BaseModel):
    campaign_id: str
    agent: str
    action: str
    estimated_tokens: int = 0
    estimated_cost_usd: float = 0.0
    budget_usd: float
    threshold: Literal["normal", "warning", "halt"] = "normal"
    detail: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentTransition(BaseModel):
    campaign_id: str
    from_node: str
    to_node: str
    status: Literal["started", "completed", "skipped", "halted", "error"]
    message_type: str
    payload_summary: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FuzzCase(BaseModel):
    id: str
    parent_case_id: str
    category: AttackCategory
    operator: str
    sequence: List[str]
    expected_safe_behavior: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RegressionReplayResult(BaseModel):
    id: str
    source_case_id: str
    campaign_id: str
    category: AttackCategory
    status: Literal["pass", "fail", "partial"]
    target_status_code: Optional[int] = None
    transport_error: Optional[str] = None
    response_excerpt: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MultiAgentRunSummary(BaseModel):
    campaign_id: str
    graph_version: str
    nodes_visited: List[str]
    transitions_recorded: int
    halted: bool = False
    halt_reason: Optional[str] = None


class CoverageSummary(BaseModel):
    category_counts: Dict[str, int]
    pass_count: int
    fail_count: int
    partial_count: int
    open_vulnerabilities: int
    estimated_cost_usd: float
    last_campaign_id: Optional[str] = None


class AgentEvent(BaseModel):
    campaign_id: str
    agent: str
    action: str
    detail: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
