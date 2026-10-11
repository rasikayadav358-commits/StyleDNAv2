"""Body-fit scoring based on shape preferences in the YAML rules."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, cast

import yaml

RULES_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "body_rules.yaml"


@lru_cache(maxsize=1)
def _load_rules() -> dict[str, Any]:
    if RULES_PATH.exists():
        with open(RULES_PATH, encoding="utf-8") as handle:
            return cast(dict[str, Any], yaml.safe_load(handle) or {})
    return {}


def _normalize(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def body_fit(attrs: dict[str, Any], shape: str, source: str = "manual") -> float:
    """Return a 0..1 fit score for the shape, using YAML-based taxonomy weights."""
    if not isinstance(attrs, dict) or not shape:
        return 0.5

    rules = _load_rules()
    source_rules = rules.get(source, rules.get("manual", {}))
    preferences = source_rules.get("styles", {}).get(shape, {}).get("preferences", {})
    if not preferences:
        return 0.5

    total_weight = 0.0
    weighted_score = 0.0

    for attribute_name, values in preferences.items():
        incoming_value = attrs.get(attribute_name)
        if incoming_value is None:
            continue
        normalized = _normalize(incoming_value)
        match_weight = values.get(normalized, 0.0)
        if match_weight <= 0:
            continue
        weighted_score += match_weight
        total_weight += 1.0

    if total_weight <= 0:
        return 0.5

    score = weighted_score / total_weight
    return round(max(0.0, min(1.0, score)), 3)
