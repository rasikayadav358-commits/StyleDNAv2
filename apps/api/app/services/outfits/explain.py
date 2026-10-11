"""Template-based outfit explanations grounded in the top rule components."""

from __future__ import annotations

from typing import Any

from app.services.outfits.features import feature_scores


def _coerce_item(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, item.get(key.replace("_", ""), default))
    return getattr(item, key, default)


def explain_outfit(candidate: Any, *, occasion: Any, season: Any, body_shape: str | None = None, attrs: dict[str, Any] | None = None) -> list[str]:
    """Return three or more factual reasons that explain the outfit score."""
    scores = feature_scores(candidate, occasion=occasion, season=season, body_shape=body_shape, attrs=attrs)
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)

    reasons: list[str] = []
    slots = _coerce_item(candidate, "slots", {}) if isinstance(candidate, dict) else getattr(candidate, "slots", {})
    item_names = []
    for item in slots.values():
        item_name = _coerce_item(item, "name", _coerce_item(item, "category", "item"))
        if item_name not in (None, ""):
            item_names.append(str(item_name))

    if ordered:
        for name, value in ordered[:3]:
            label = name.replace("_", " ").title()
            if name == "body_fit":
                reasons.append(f"Body-fit scoring is {value:.2f} for the {body_shape or 'current'} silhouette profile.")
            elif name == "color":
                colors = [str(_coerce_item(item, "color", "item")) for item in slots.values() if _coerce_item(item, "color", None) is not None]
                colors_text = ", ".join(colors) if colors else "used colors"
                reasons.append(f"Color harmony is {value:.2f} across the palette ({colors_text}).")
            elif name == "occasion":
                reasons.append(f"Occasion fit is {value:.2f} for the {occasion} brief.")
            elif name == "season":
                reasons.append(f"Season fit is {value:.2f} for {season} styling.")
            elif name == "layering":
                reasons.append(f"Layering adds {value:.2f} polish through the selected layer pieces.")
            elif name == "novelty":
                reasons.append(f"Novelty is {value:.2f}, which keeps the outfit contemporary without breaking the dress code.")
            else:
                reasons.append(f"{label} contributes {value:.2f} to the overall recommendation.")

    if len(reasons) < 3:
        reasons.extend([
            f"The outfit uses {len(slots)} slots across {', '.join(item_names[:3]) if item_names else 'selected pieces'}.",
            f"The look is set for {occasion} and {season} conditions.",
            "The skeleton remains structurally valid and season-compatible.",
        ])

    deduped: list[str] = []
    for reason in reasons:
        if reason not in deduped:
            deduped.append(reason)
    return deduped[:5]
