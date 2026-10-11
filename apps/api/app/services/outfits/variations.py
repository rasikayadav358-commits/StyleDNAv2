"""Variant plans for outfit adjustments using constraint and weight nudges."""

from __future__ import annotations

from typing import Any

VARIATION_TYPES: tuple[str, ...] = (
    "more_casual",
    "more_formal",
    "more_layered",
    "monochrome",
    "weekend_relaxed",
    "work_ready",
    "bold_statement",
    "seasonal_refresh",
)


def _normalize(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _base_plan(variation_type: str) -> dict[str, Any]:
    return {
        "type": variation_type,
        "constraints": {},
        "weights": {
            "body_fit": 0.26,
            "color": 0.2,
            "style": 0.16,
            "occasion": 0.14,
            "season": 0.12,
            "layering": 0.06,
            "novelty": 0.06,
        },
    }


def generate_variations(candidate: Any, *, occasion: Any = "casual", season: Any = "all_season", variation_type: str | None = None) -> list[dict[str, Any]]:
    """Return a deterministic set of variation plans built from the candidate slot map."""
    slots = candidate.get("slots", candidate) if isinstance(candidate, dict) else getattr(candidate, "slots", {})
    plans: list[dict[str, Any]] = []
    for variation in VARIATION_TYPES:
        plan = _base_plan(variation)
        key = _normalize(variation)
        if key == "more_casual":
            plan["constraints"] = {"occasion_max_formality": 1}
            plan["weights"] = {**plan["weights"], "occasion": 0.22, "style": 0.22, "novelty": 0.04}
        elif key == "more_formal":
            plan["constraints"] = {"occasion_min_formality": 2}
            plan["weights"] = {**plan["weights"], "occasion": 0.22, "style": 0.18, "color": 0.16}
        elif key == "more_layered":
            plan["constraints"] = {"require_layer": True}
            plan["weights"] = {**plan["weights"], "layering": 0.18, "style": 0.18}
        elif key == "monochrome":
            plan["constraints"] = {"color_similarity": 0.7}
            plan["weights"] = {**plan["weights"], "color": 0.32, "style": 0.12}
        elif key == "weekend_relaxed":
            plan["constraints"] = {"occasion_max_formality": 1, "relaxed_fit": True}
            plan["weights"] = {**plan["weights"], "style": 0.2, "novelty": 0.08, "occasion": 0.18}
        elif key == "work_ready":
            plan["constraints"] = {"occasion": "work", "season": season}
            plan["weights"] = {**plan["weights"], "occasion": 0.28, "body_fit": 0.28, "style": 0.18}
        elif key == "bold_statement":
            plan["constraints"] = {"novelty_min": 0.6}
            plan["weights"] = {**plan["weights"], "novelty": 0.18, "color": 0.24, "style": 0.2}
        elif key == "seasonal_refresh":
            plan["constraints"] = {"season": season}
            plan["weights"] = {**plan["weights"], "season": 0.2, "color": 0.18, "layering": 0.08}
        plan["candidate"] = slots
        plans.append(plan)

    if variation_type is not None:
        requested = _normalize(variation_type)
        filtered = [plan for plan in plans if plan["type"] == requested]
        if filtered:
            return filtered
    return plans
