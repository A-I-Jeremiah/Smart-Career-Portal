# backend/models/department_filter.py
"""
Post-processing layer: re-rank ML career probabilities by student department.

Tiers per department:
  - primary:   core careers for that SSS stream (heavy boost)
  - secondary: plausible adjacent paths (mild boost)
  - cross:     everything else (strong penalty, optionally hard-blocked)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from backend.config import (
    DEPT_CROSS_OVERRIDE_RAW_CONF,
    DEPT_CROSS_PENALTY,
    DEPT_FILTER_ENABLED,
    DEPT_HARD_BLOCK_CROSS,
    DEPT_PRIMARY_BOOST,
    DEPT_SECONDARY_BOOST,
    DEPT_TOP_K,
)

# Must match label_encoder.classes_ exactly (10 careers)
ALL_CAREERS: Tuple[str, ...] = (
    "Agriculture & Environmental Sciences",
    "Business & Finance",
    "Computer Science & IT",
    "Creative Arts & Design",
    "Education & Humanities",
    "Engineering & Technology",
    "Entrepreneurship & Management",
    "Law & Social Sciences",
    "Mass Communication & Media",
    "Medicine & Health Sciences",
)

# Nigerian SSS stream → career tiers
CAREER_DEPARTMENT_TIERS: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "Science": {
        "primary": (
            "Medicine & Health Sciences",
            "Engineering & Technology",
            "Computer Science & IT",
            "Agriculture & Environmental Sciences",
        ),
        "secondary": (
            "Education & Humanities",
        ),
    },
    "Arts": {
        "primary": (
            "Creative Arts & Design",
            "Mass Communication & Media",
            "Law & Social Sciences",
            "Education & Humanities",
        ),
        "secondary": (
            "Business & Finance",
        ),
    },
    "Commercial": {
        "primary": (
            "Business & Finance",
            "Entrepreneurship & Management",
        ),
        "secondary": (
            "Law & Social Sciences",
            "Mass Communication & Media",
            "Education & Humanities",
        ),
    },
}

DEPARTMENT_ALIASES = {
    "science": "Science",
    "arts": "Arts",
    "commercial": "Commercial",
    "social science": "Arts",
    "humanities": "Arts",
}


@dataclass(frozen=True)
class DepartmentFilterResult:
    adjusted_proba: np.ndarray
    raw_proba: np.ndarray
    department: str
    alignment_applied: bool
    realigned: bool
    warning: Optional[str] = None


def normalize_department(department: Optional[str]) -> str:
    if not department:
        return "Unknown"
    key = str(department).strip()
    if key in CAREER_DEPARTMENT_TIERS:
        return key
    return DEPARTMENT_ALIASES.get(key.lower(), key)


def _tier_for_career(department: str, career: str) -> str:
    tiers = CAREER_DEPARTMENT_TIERS.get(department, {})
    if career in tiers.get("primary", ()):
        return "primary"
    if career in tiers.get("secondary", ()):
        return "secondary"
    return "cross"


def _weight_for_tier(tier: str) -> float:
    if tier == "primary":
        return DEPT_PRIMARY_BOOST
    if tier == "secondary":
        return DEPT_SECONDARY_BOOST
    if DEPT_HARD_BLOCK_CROSS:
        return 0.0
    return DEPT_CROSS_PENALTY


def apply_department_alignment(
    raw_proba: Sequence[float],
    class_labels: Sequence[str],
    department: Optional[str],
) -> DepartmentFilterResult:
    """
    Multiply each class probability by a department tier weight, then renormalize.

    Cross-department override: if raw probability for a cross-dept career is
    exceptionally high (>= DEPT_CROSS_OVERRIDE_RAW_CONF), keep full weight so
    gifted outliers are not suppressed.
    """
    raw = np.asarray(raw_proba, dtype=np.float64)
    dept = normalize_department(department)

    if not DEPT_FILTER_ENABLED or dept not in CAREER_DEPARTMENT_TIERS:
        return DepartmentFilterResult(
            adjusted_proba=raw.copy(),
            raw_proba=raw.copy(),
            department=dept,
            alignment_applied=False,
            realigned=False,
        )

    weights = np.ones(len(class_labels), dtype=np.float64)
    for i, career in enumerate(class_labels):
        tier = _tier_for_career(dept, career)
        w = _weight_for_tier(tier)
        if tier == "cross" and raw[i] >= DEPT_CROSS_OVERRIDE_RAW_CONF:
            w = 1.0
        weights[i] = w

    adjusted = raw * weights
    total = adjusted.sum()
    if total <= 0:
        primary_mask = np.array(
            [_tier_for_career(dept, c) == "primary" for c in class_labels],
            dtype=bool,
        )
        adjusted = np.where(primary_mask, raw, 0.0)
        total = adjusted.sum()
        if total <= 0:
            adjusted = raw.copy()
        else:
            adjusted /= total
    else:
        adjusted /= total

    raw_top = int(np.argmax(raw))
    adj_top = int(np.argmax(adjusted))
    realigned = raw_top != adj_top

    warning = None
    if realigned:
        raw_career = class_labels[raw_top]
        adj_career = class_labels[adj_top]
        warning = (
            f"Recommendation adjusted for {dept} department "
            f"({raw_career} → {adj_career})."
        )

    return DepartmentFilterResult(
        adjusted_proba=adjusted,
        raw_proba=raw,
        department=dept,
        alignment_applied=True,
        realigned=realigned,
        warning=warning,
    )


def build_top_k(
    proba: Sequence[float],
    class_labels: Sequence[str],
    k: int = DEPT_TOP_K,
) -> List[Tuple[str, float]]:
    indices = np.argsort(proba)[::-1][:k]
    return [(class_labels[i], float(proba[i])) for i in indices]


def filter_careers_for_department(
    careers: Iterable[str],
    department: Optional[str],
    *,
    include_secondary: bool = True,
) -> List[str]:
    """Used by heuristic fallback — only consider department-allowed careers."""
    dept = normalize_department(department)
    tiers = CAREER_DEPARTMENT_TIERS.get(dept)
    if not tiers:
        return list(careers)
    allowed = set(tiers["primary"])
    if include_secondary:
        allowed.update(tiers["secondary"])
    return [c for c in careers if c in allowed]
