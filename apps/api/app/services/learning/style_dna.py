"""Style DNA state updates using EMA over outfit event feedback."""

from __future__ import annotations

from typing import Any

EVENT_WEIGHTS: dict[str, float] = {
    "impression": 0.1,
    "like": 1.0,
    "dislike": -1.0,
    "save": 1.5,
    "skip": -0.3,
    "wear": 2.0,
    "variation": 0.2,
    "buy_click": 1.0,
}

DEFAULT_STYLE_TAGS: tuple[str, ...] = (
    "minimal",
    "ethnic",
    "tailored",
    "streetwear",
    "classic",
    "sporty",
    "boho",
    "luxury",
    "casual",
    "formal",
)


def _normalize_tag(tag: Any) -> str:
    text = str(tag).strip().lower().replace(" ", "_")
    return text


def empty_style_vector() -> dict[str, float]:
    return {tag: 0.0 for tag in DEFAULT_STYLE_TAGS}


def normalize_tags(tags: list[str] | tuple[str, ...] | set[str] | None) -> list[str]:
    if not tags:
        return []
    normalized: list[str] = []
    for tag in tags:
        value = _normalize_tag(tag)
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def update_style_state_from_event(
    state: dict[str, Any] | None,
    event_type: str,
    style_tags: list[str] | tuple[str, ...] | set[str] | None = None,
    *,
    alpha: float = 0.25,
) -> dict[str, Any]:
    """Apply an EMA update to the user's style vector and affinities."""
    vector = (state or {}).get("style_vector") or empty_style_vector()
    if not isinstance(vector, dict):
        vector = empty_style_vector()

    event_key = str(event_type).strip().lower()
    weight = EVENT_WEIGHTS.get(event_key, 0.0)
    next_vector = {tag: float(value) for tag, value in vector.items()}
    tags = normalize_tags(style_tags)

    for tag in DEFAULT_STYLE_TAGS:
        current = next_vector.get(tag, 0.0)
        signal = 1.0 if tag in tags else 0.0
        next_vector[tag] = round((1.0 - alpha) * current + alpha * (weight * signal), 6)

    if not tags and weight == 0.0:
        next_vector = {tag: round(float(value), 6) for tag, value in next_vector.items()}

    updated_state = dict(state or {})
    updated_state["style_vector"] = next_vector
    updated_state["tag_affinities"] = next_vector.copy()
    updated_state["n_events"] = int((state or {}).get("n_events", 0)) + 1
    return updated_state
