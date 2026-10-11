"""
Body shape classification service.

Computes proportional ratios and evaluates soft scores against body_rules.yaml.
Strictly body-positive: outputs neutral styling guidance (fits, silhouettes, cuts).
Never outputs weight, BMI, or evaluative judgments.
"""

from pathlib import Path
from typing import Any, cast

import yaml

from app.core.logging import get_logger

logger = get_logger("body.shape")

RULES_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "body_rules.yaml"


def _load_body_rules() -> dict[str, Any]:
    if RULES_PATH.exists():
        with open(RULES_PATH, encoding="utf-8") as f:
            return cast(dict[str, Any], yaml.safe_load(f) or {})
    return {}


BODY_RULES = _load_body_rules()


def _shape_rule_set(source: str = "manual") -> dict[str, Any]:
    source_name = source if source in BODY_RULES else "manual"
    return cast(dict[str, Any], BODY_RULES.get(source_name, {}))


def _condition_matches(condition_key: str, value: float, thresholds: dict[str, float]) -> bool:
    if condition_key.endswith("_max"):
        ratio_name = condition_key[:-4]
        return value <= thresholds.get(condition_key, float("inf"))
    if condition_key.endswith("_min"):
        ratio_name = condition_key[:-4]
        return value >= thresholds.get(condition_key, float("-inf"))
    return True


def _score_shape(shape_name: str, thresholds: dict[str, float], ratios: dict[str, float]) -> float:
    score = 0.0
    for condition_key, threshold in thresholds.items():
        ratio_name = condition_key[:-4] if condition_key.endswith("_max") or condition_key.endswith("_min") else condition_key
        if ratio_name not in ratios:
            continue
        ratio_value = ratios[ratio_name]
        if _condition_matches(condition_key, ratio_value, thresholds):
            score += 1.0
    return score


def _build_recommendations(shape_name: str, preferences: dict[str, Any]) -> list[str]:
    recommendations: list[str] = []
    for attribute_name in ("neckline", "fit", "length", "rise", "subcategory"):
        values = preferences.get(attribute_name, {})
        if not values:
            continue
        best_key, best_weight = max(values.items(), key=lambda item: item[1])
        worst_key, worst_weight = min(values.items(), key=lambda item: item[1])
        if best_weight > 0:
            recommendations.append(f"More emphasis on {best_key.replace('_', ' ')} {attribute_name} picks.")
        if worst_weight < best_weight:
            recommendations.append(f"Less emphasis on {worst_key.replace('_', ' ')} {attribute_name} choices.")
    if not recommendations:
        recommendations.append("More emphasis on balanced silhouettes and well-fitted lines.")
    return recommendations[:4]


def compute_proportional_ratios(
    shoulder: float,
    waist: float,
    hip: float,
    bust: float | None = None,
    height: float | None = None,
    inseam: float | None = None,
) -> dict[str, float]:
    """Calculate key proportional ratios from bodily dimensions."""
    if hip <= 0 or shoulder <= 0 or waist <= 0:
        raise ValueError("Measurements must be positive numbers")

    ratios = {
        "shoulder_to_hip": round(shoulder / hip, 3),
        "waist_to_hip": round(waist / hip, 3),
        "waist_to_shoulder": round(waist / shoulder, 3),
    }

    if bust and bust > 0:
        ratios["bust_to_hip"] = round(bust / hip, 3)

    if height and inseam and height > inseam and inseam > 0:
        torso = height - inseam
        ratios["torso_to_leg"] = round(torso / inseam, 3)

    return ratios


def classify_body_shape(
    shoulder: float,
    waist: float,
    hip: float,
    bust: float | None = None,
    height: float | None = None,
    inseam: float | None = None,
    source: str = "manual",
) -> dict[str, Any]:
    """
    Classify body proportions into styling shapes using YAML-defined thresholds.
    Returns: shape, confidence, runner_up, ratios, styling recommendations, and fit guidance.
    """
    ratios = compute_proportional_ratios(
        shoulder=shoulder,
        waist=waist,
        hip=hip,
        bust=bust,
        height=height,
        inseam=inseam,
    )

    rule_set = _shape_rule_set(source)
    thresholds = rule_set.get("thresholds", {})
    styles = rule_set.get("styles", {})
    defaults = rule_set.get("defaults", {})

    scores: dict[str, float] = {shape_name: _score_shape(shape_name, config, ratios) for shape_name, config in thresholds.items()}

    if not any(score > 0 for score in scores.values()):
        winner_shape = defaults.get("fallback", "Rectangle")
        confidence = float(defaults.get("confidence", 0.55))
        runner_up_shape = "Hourglass"
    else:
        sorted_shapes = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        winner_shape, top_score = sorted_shapes[0]
        runner_up_shape = sorted_shapes[1][0] if len(sorted_shapes) > 1 else None
        total_score = max(1.0, sum(scores.values()))
        confidence = round(max(0.50, min(0.95, top_score / total_score)), 2)

    runner_up = runner_up_shape if runner_up_shape and runner_up_shape != winner_shape else None
    shape_meta = styles.get(winner_shape, {})
    preferences = shape_meta.get("preferences", {})

    return {
        "shape": winner_shape,
        "confidence": confidence,
        "runner_up": runner_up,
        "ratios": ratios,
        "recommended_silhouettes": shape_meta.get("recommended_silhouettes", []),
        "suggested_fits": shape_meta.get("suggested_fits", []),
        "styles_to_try": shape_meta.get("styles_to_try", []),
        "notes": shape_meta.get("notes", "Dress in silhouettes that bring comfort and personal confidence."),
        "recommendations": shape_meta.get("recommendations", _build_recommendations(winner_shape, preferences)),
        "preferences": preferences,
    }
