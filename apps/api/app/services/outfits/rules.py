"""Hard filters and deterministic outfit rule helpers for Phase 5."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

OUTFIT_RULE_CONFIG: dict[str, Any] = {
    "formality_bands": {
        "casual": 1,
        "college": 1,
        "lounge": 1,
        "work": 2,
        "party": 3,
        "festive": 3,
        "formal": 4,
        "wedding": 4,
    },
    "season_aliases": {
        "summer": {"summer", "all_season"},
        "winter": {"winter", "all_season"},
        "spring": {"spring_autumn", "all_season"},
        "monsoon": {"monsoon", "all_season"},
    },
    "weights": {
        "body_fit": 0.26,
        "color": 0.20,
        "style": 0.16,
        "occasion": 0.14,
        "season": 0.12,
        "layering": 0.06,
        "novelty": 0.06,
    },
    "hard_filter_limits": {
        "max_bottoms": 1,
        "lounge_formal_shoes_max": 1,
    },
}


def _normalize(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _coerce_item(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, item.get(key.replace("_", ""), default))
    return getattr(item, key, default)


def _iter_slots(candidate: Any) -> Iterable[tuple[str, Any]]:
    if isinstance(candidate, dict):
        slots = candidate.get("slots", candidate)
        if isinstance(slots, dict):
            return slots.items()
        return ()
    slots = getattr(candidate, "slots", {})
    if isinstance(slots, dict):
        return slots.items()
    return ()


def occasion_to_formality_band(occasion: Any) -> int:
    """Map an occasion string or list to a formality band 1..4."""
    if isinstance(occasion, (list, tuple, set)):
        return max(occasion_to_formality_band(item) for item in occasion) if occasion else 1
    key = _normalize(occasion)
    return OUTFIT_RULE_CONFIG["formality_bands"].get(key, 1)


def season_match(item: Any, season: Any) -> bool:
    """Check whether an item is valid for a target season."""
    season_key = _normalize(season)
    values = _coerce_item(item, "season", None)
    if values is None:
        values = _coerce_item(item, "seasons", None)
    if values is None:
        return True
    if isinstance(values, str):
        options = { _normalize(values) }
    elif isinstance(values, (list, tuple, set)):
        options = {_normalize(v) for v in values}
    else:
        options = { _normalize(values) }
    return any(option in OUTFIT_RULE_CONFIG["season_aliases"].get(season_key, {season_key}) for option in options)


def duplicate_items(candidate: Any) -> bool:
    """Return True when the same item ID appears more than once in the candidate."""
    seen: set[str] = set()
    for _, item in _iter_slots(candidate):
        item_id = _coerce_item(item, "id")
        if item_id is None:
            continue
        if str(item_id) in seen:
            return True
        seen.add(str(item_id))
    return False


def no_two_bottoms(candidate: Any) -> bool:
    """Reject skeletons that include more than one bottom-style category."""
    bottom_count = 0
    for slot_name, item in _iter_slots(candidate):
        category = _coerce_item(item, "category")
        if category in {"bottom", "ethnic_bottom"} or slot_name in {"bottom", "ethnic_bottom"}:
            bottom_count += 1
    return bottom_count <= 1


def no_formal_shoes_for_lounge(candidate: Any, occasion: Any) -> bool:
    """Reject formal shoes when the intended outfit is lounge-oriented."""
    if occasion_to_formality_band(occasion) > 1:
        return True
    for _, item in _iter_slots(candidate):
        category = _coerce_item(item, "category")
        if category == "shoes":
            formality = _coerce_item(item, "formality", 1) or 1
            try:
                formality_value = int(formality)
            except (TypeError, ValueError):
                formality_value = 1
            if formality_value > 1:
                return False
    return True


def hard_filter_candidate(candidate: Any, occasion: Any, season: Any) -> bool:
    """Apply Phase 5 hard filters: availability, duplicates, bottom count, season, and occasion compatibility."""
    for _, item in _iter_slots(candidate):
        if _coerce_item(item, "is_available", True) is False:
            return False
        if not season_match(item, season):
            return False

    if duplicate_items(candidate):
        return False
    if not no_two_bottoms(candidate):
        return False
    if not no_formal_shoes_for_lounge(candidate, occasion):
        return False
    return True
