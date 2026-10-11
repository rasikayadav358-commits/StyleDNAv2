"""Feature scoring for outfit ranking based on body-fit, color, style, and occasion rules."""

from __future__ import annotations

import random
from typing import Any

from app.services.body.fit import body_fit
from app.services.outfits.color import palette_harmony
from app.services.outfits.rules import OUTFIT_RULE_CONFIG, occasion_to_formality_band, season_match


def _coerce_item(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, item.get(key.replace("_", ""), default))
    return getattr(item, key, default)


def _extract_colors(items: list[Any]) -> list[Any]:
    colors: list[Any] = []
    for item in items:
        color = _coerce_item(item, "color", None)
        if color is not None:
            colors.append(color)
        pattern = _coerce_item(item, "pattern", None)
        if pattern is not None:
            colors.append(pattern)
    return colors


def body_feature_score(candidate: Any, shape: str | None = None, attrs: dict[str, Any] | None = None) -> float:
    if not shape:
        return 0.5
    items = list(_coerce_item(candidate, "slots", {}).values()) if isinstance(candidate, dict) else list(getattr(candidate, "slots", {}).values())
    if not items:
        return 0.5
    attr_map = attrs or {}
    if not attr_map:
        for item in items:
            for key in ("neckline", "fit", "length", "rise", "subcategory"):
                value = _coerce_item(item, key, None)
                if value is not None:
                    attr_map[key] = value
    return body_fit(attr_map, shape, source="manual")


def color_feature_score(candidate: Any) -> float:
    items = list(_coerce_item(candidate, "slots", {}).values()) if isinstance(candidate, dict) else list(getattr(candidate, "slots", {}).values())
    return palette_harmony(_extract_colors(items))


def style_feature_score(candidate: Any) -> float:
    items = list(_coerce_item(candidate, "slots", {}).values()) if isinstance(candidate, dict) else list(getattr(candidate, "slots", {}).values())
    if not items:
        return 0.5
    styles = []
    for item in items:
        style = _coerce_item(item, "style", None)
        if style is not None:
            styles.append(str(style).lower())
    if not styles:
        return 0.5
    unique = set(styles)
    return round(len(unique) / max(1, len(styles)), 3)


def occasion_feature_score(candidate: Any, occasion: Any) -> float:
    target = occasion_to_formality_band(occasion)
    slots = _coerce_item(candidate, "slots", {}) if isinstance(candidate, dict) else getattr(candidate, "slots", {})
    scores = []
    for item in slots.values():
        formality = int(_coerce_item(item, "formality", 1) or 1)
        scores.append(1.0 if formality <= target else 0.3)
    return round(sum(scores) / max(1, len(scores)), 3) if scores else 0.5


def season_feature_score(candidate: Any, season: Any) -> float:
    items = list(_coerce_item(candidate, "slots", {}).values()) if isinstance(candidate, dict) else list(getattr(candidate, "slots", {}).values())
    if not items:
        return 0.5
    valid = [1.0 if season_match(item, season) else 0.0 for item in items]
    return round(sum(valid) / len(valid), 3)


def layering_feature_score(candidate: Any) -> float:
    items = list(_coerce_item(candidate, "slots", {}).values()) if isinstance(candidate, dict) else list(getattr(candidate, "slots", {}).values())
    layered = sum(1 for item in items if _coerce_item(item, "category") in {"layer", "dupatta"})
    return 1.0 if layered else 0.5


def novelty_feature_score(candidate: Any) -> float:
    items = list(_coerce_item(candidate, "slots", {}).values()) if isinstance(candidate, dict) else list(getattr(candidate, "slots", {}).values())
    if not items:
        return 0.5
    novelty_values = []
    for item in items:
        novelty = _coerce_item(item, "novelty", 0.5)
        novelty_values.append(float(novelty))
    return round(sum(novelty_values) / len(novelty_values), 3)


def feature_scores(candidate: Any, *, occasion: Any, season: Any, body_shape: str | None = None, attrs: dict[str, Any] | None = None, seed: int | None = None) -> dict[str, float]:
    """Return the weighted component scores for a candidate outfit."""
    return {
        "body_fit": body_feature_score(candidate, body_shape, attrs),
        "color": color_feature_score(candidate),
        "style": style_feature_score(candidate),
        "occasion": occasion_feature_score(candidate, occasion),
        "season": season_feature_score(candidate, season),
        "layering": layering_feature_score(candidate),
        "novelty": novelty_feature_score(candidate),
    }


def score_outfit(candidate: Any, *, occasion: Any, season: Any, body_shape: str | None = None, attrs: dict[str, Any] | None = None, seed: int | None = None) -> float:
    """Weighted aggregate score for a candidate outfit using config-driven weights."""
    values = feature_scores(candidate, occasion=occasion, season=season, body_shape=body_shape, attrs=attrs, seed=seed)
    weights = OUTFIT_RULE_CONFIG["weights"]
    numerator = sum(weights.get(name, 0.0) * value for name, value in values.items())
    denominator = sum(weights.values())
    return round(numerator / denominator, 3) if denominator else 0.5


def rank_candidates(candidates: list[Any], *, occasion: Any, season: Any, body_shape: str | None = None, attrs: dict[str, Any] | None = None, seed: int | None = 0) -> list[tuple[float, Any]]:
    """Deterministically rank candidates using the configured weighted feature model."""
    rng = random.Random(seed)
    ranked: list[tuple[float, Any]] = []
    for candidate in candidates:
        score = score_outfit(candidate, occasion=occasion, season=season, body_shape=body_shape, attrs=attrs, seed=seed)
        tie_breaker = rng.random()
        ranked.append((score + tie_breaker * 1e-9, candidate))
    ranked.sort(key=lambda item: (-item[0], str(getattr(item[1], "item_ids", tuple()))))
    return [(score, candidate) for score, candidate in ranked]
