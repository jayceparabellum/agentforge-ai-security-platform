from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from agentforge.models import AttackCategory


class GoldenEvalCase(BaseModel):
    id: str
    category: AttackCategory
    title: str
    adversarial_objective: str
    prompt: str
    expected_safe_behavior: str
    pass_criteria: List[str] = Field(min_length=2)
    risk_tags: List[str] = Field(default_factory=list)
    severity: int = Field(ge=1, le=5)
    source: str


def evals_dir() -> Path:
    return Path.cwd() / "evals"


def golden_cases_path() -> Path:
    return evals_dir() / "golden_cases.json"


def latest_results_path() -> Path:
    return evals_dir() / "results.latest.json"


def load_golden_cases() -> List[GoldenEvalCase]:
    payload = json.loads(golden_cases_path().read_text(encoding="utf-8"))
    return [GoldenEvalCase.model_validate(item) for item in payload["cases"]]


def evaluate_golden_cases(write_latest: bool = True) -> Dict[str, Any]:
    cases = load_golden_cases()
    total = len(cases)
    categories = Counter(case.category.value for case in cases)
    sources = Counter(case.source for case in cases)
    severities = Counter(str(case.severity) for case in cases)
    high_risk = sum(1 for case in cases if case.severity >= 4)
    unique_ids = len({case.id for case in cases})
    cases_with_phi_guard = sum(1 for case in cases if "phi" in {tag.lower() for tag in case.risk_tags})
    cases_with_tool_guard = sum(1 for case in cases if "tool" in {tag.lower() for tag in case.risk_tags})
    categories_expected = {category.value for category in AttackCategory}
    missing_categories = sorted(categories_expected - set(categories))
    id_integrity = unique_ids == total
    quality_checks = {
        "has_50_cases": total == 50,
        "unique_ids": id_integrity,
        "all_categories_covered": not missing_categories,
        "has_phi_guards": cases_with_phi_guard >= 8,
        "has_tool_guards": cases_with_tool_guard >= 8,
        "high_risk_coverage": high_risk >= 20,
        "multi_source_coverage": len(sources) >= 6,
    }
    passed_quality_checks = sum(1 for passed in quality_checks.values() if passed)
    progress = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "suite": "agentforge-golden-safety-evals-v1",
        "status": "ready" if all(quality_checks.values()) else "needs_attention",
        "total_cases": total,
        "validated_cases": total if id_integrity else unique_ids,
        "readiness_percent": round((passed_quality_checks / len(quality_checks)) * 100, 2),
        "category_counts": dict(sorted(categories.items())),
        "source_counts": dict(sorted(sources.items())),
        "severity_counts": dict(sorted(severities.items())),
        "high_risk_cases": high_risk,
        "missing_categories": missing_categories,
        "quality_checks": quality_checks,
    }
    if write_latest:
        latest_results_path().write_text(json.dumps(progress, indent=2), encoding="utf-8")
    return progress
