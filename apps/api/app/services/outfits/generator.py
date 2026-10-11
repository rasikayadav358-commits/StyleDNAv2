"""Outfit generation with deterministic MMR diversification and rule scoring."""

from __future__ import annotations

import random
from typing import Any

from app.services.outfits.features import feature_scores, score_outfit
from app.services.outfits.rules import hard_filter_candidate
from app.services.outfits.skeletons import OutfitCandidate, generate_candidates


def _coerce_item(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, item.get(key.replace("_", ""), default))
    return getattr(item, key, default)


def _signature(candidate: OutfitCandidate) -> set[str]:
    signature: set[str] = set()
    for item in candidate.slots.values():
        category = str(_coerce_item(item, "category", ""))
        style = str(_coerce_item(item, "style", ""))
        color = str(_coerce_item(item, "color", ""))
        item_id = str(_coerce_item(item, "id", ""))
        for value in (category, style, color, item_id):
            if value:
                signature.add(value.lower())
    return signature


def _similarity(a: OutfitCandidate, b: OutfitCandidate) -> float:
    left = _signature(a)
    right = _signature(b)
    if not left and not right:
        return 0.0
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _mmr_diversify(ranked: list[tuple[float, OutfitCandidate]], *, limit: int, seed: int | None = 0) -> list[tuple[float, OutfitCandidate]]:
    if not ranked:
        return []
    rng = random.Random(seed)
    selected: list[tuple[float, OutfitCandidate]] = [ranked[0]]
    remaining = ranked[1:]
    while len(selected) < min(limit, len(ranked)) and remaining:
        best_index = -1
        best_value = float("-inf")
        for index, (score, candidate) in enumerate(remaining):
            max_similarity = max(_similarity(candidate, chosen_candidate) for _, chosen_candidate in selected) if selected else 0.0
            mmr_value = (0.75 * score) - (0.25 * max_similarity) + (rng.random() * 1e-9)
            if mmr_value > best_value:
                best_value = mmr_value
                best_index = index
        if best_index < 0:
            break
        selected.append(remaining.pop(best_index))
    return selected


def generate_outfits(
    items: list[Any],
    *,
    occasion: Any = "casual",
    season: Any = "all_season",
    body_shape: str | None = None,
    attrs: dict[str, Any] | None = None,
    seed: int | None = 0,
    limit: int = 8,
    max_candidates: int = 5000,
) -> list[OutfitCandidate]:
    """Generate and rank a diversified set of valid outfit candidates for a user."""
    skeletons = generate_candidates(items, max_candidates=max_candidates)
    valid = [candidate for candidate in skeletons if hard_filter_candidate(candidate, occasion, season)]
    ranked: list[tuple[float, OutfitCandidate]] = []
    for candidate in valid:
        ranked.append((score_outfit(candidate, occasion=occasion, season=season, body_shape=body_shape, attrs=attrs, seed=seed), candidate))
    if not ranked:
        return []
    ranked.sort(key=lambda item: (-item[0], str(item[1].item_ids)))
    diversified = _mmr_diversify(ranked, limit=limit, seed=seed)
    return [candidate for _, candidate in diversified]


def generate_ranked_outfits(
    items: list[Any],
    *,
    occasion: Any = "casual",
    season: Any = "all_season",
    body_shape: str | None = None,
    attrs: dict[str, Any] | None = None,
    seed: int | None = 0,
    limit: int = 8,
    max_candidates: int = 5000,
) -> list[tuple[float, OutfitCandidate]]:
    """Return ranked candidates, preserving the rule-score ordering before diversification."""
    skeletons = generate_candidates(items, max_candidates=max_candidates)
    valid = [candidate for candidate in skeletons if hard_filter_candidate(candidate, occasion, season)]
    ranked: list[tuple[float, OutfitCandidate]] = []
    for candidate in valid:
        ranked.append((score_outfit(candidate, occasion=occasion, season=season, body_shape=body_shape, attrs=attrs, seed=seed), candidate))
    ranked.sort(key=lambda item: (-item[0], str(item[1].item_ids)))
    return ranked[:limit]
