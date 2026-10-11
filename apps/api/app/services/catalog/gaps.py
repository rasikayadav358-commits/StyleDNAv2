"""Counterfactual gap analysis for outfit archetypes and virtual items."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.services.outfits.generator import generate_outfits

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
ARCHETYPE_CANDIDATES = ("outfit_archetypes.yaml", "gap_archetypes.yaml", "counterfactual_archetypes.yaml")


def _coerce_item(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(key, item.get(key.replace("_", ""), default))
    return getattr(item, key, default)


@lru_cache(maxsize=1)
def load_archetypes() -> list[dict[str, Any]]:
    """Load YAML archetypes with a deterministic fallback to a small built-in set."""
    for filename in ARCHETYPE_CANDIDATES:
        path = DATA_DIR / filename
        if path.exists():
            with open(path, encoding="utf-8") as handle:
                payload = yaml.safe_load(handle) or {}
            items = payload.get("archetypes") if isinstance(payload, dict) else payload
            if isinstance(items, list) and items:
                return items

    return [
        {
            "id": "beige_linen_trousers",
            "name": "Beige linen trousers",
            "category": "bottom",
            "style": "relaxed",
            "color": "#E5E7EB",
            "suitability": 0.9,
            "occasions": ["college", "work"],
            "virtual_item": {
                "id": "virtual_beige_linen_trousers",
                "category": "bottom",
                "style": "relaxed",
                "color": "#E5E7EB",
                "formality": 1,
                "season": "summer",
                "seasons": ["summer", "all_season"],
                "occasions": ["college", "work"],
                "is_available": True,
            },
        },
        {
            "id": "white_sneakers",
            "name": "White sneakers",
            "category": "shoes",
            "style": "casual",
            "color": "#FFFFFF",
            "suitability": 0.7,
            "occasions": ["casual", "college"],
            "virtual_item": {
                "id": "virtual_white_sneakers",
                "category": "shoes",
                "style": "casual",
                "color": "#FFFFFF",
                "formality": 1,
                "season": "all_season",
                "seasons": ["all_season"],
                "occasions": ["casual", "college"],
                "is_available": True,
            },
        },
        {
            "id": "black_kurta",
            "name": "Black kurta",
            "category": "top",
            "style": "minimal",
            "color": "#111827",
            "suitability": 0.8,
            "occasions": ["festive", "work"],
            "virtual_item": {
                "id": "virtual_black_kurta",
                "category": "top",
                "style": "minimal",
                "color": "#111827",
                "formality": 2,
                "season": "all_season",
                "seasons": ["all_season"],
                "occasions": ["festive", "work"],
                "is_available": True,
            },
        },
    ]


def _normalize_occasion(value: Any) -> str:
    return str(value).strip().lower().replace(" ", "_")


def _virtual_item_for(archetype: dict[str, Any]) -> dict[str, Any]:
    virtual = dict(archetype.get("virtual_item") or {})
    if not virtual:
        virtual = {
            "id": archetype.get("id", "virtual_item"),
            "category": archetype.get("category", "top"),
            "style": archetype.get("style", "casual"),
            "color": archetype.get("color", "#FFFFFF"),
            "formality": 1,
            "season": "all_season",
            "seasons": ["all_season"],
            "occasions": archetype.get("occasions", []),
            "is_available": True,
        }
    virtual.setdefault("id", f"virtual_{archetype.get('id', 'item')}")
    virtual.setdefault("category", archetype.get("category", "top"))
    virtual.setdefault("is_available", True)
    return virtual


def _candidate_outfit_counts(items: list[Any], occasions: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for occasion in occasions:
        counts[occasion] = len(generate_outfits(items, occasion=occasion, season="all_season", seed=0, limit=1000))
    return counts


def gap_for_archetype(archetype: dict[str, Any], wardrobe: list[Any], occasions: list[str] | None = None) -> dict[str, Any]:
    occasions = [ _normalize_occasion(value) for value in (occasions or ["casual", "college", "work", "party", "formal", "festive", "wedding", "lounge"]) ]
    unique_occasions = list(dict.fromkeys(occasions))
    suitability = float(archetype.get("suitability", 0.5) or 0.5)
    base_counts = _candidate_outfit_counts(wardrobe, unique_occasions)
    virtual_item = _virtual_item_for(archetype)
    simulated_wardrobe = [*wardrobe, virtual_item]
    simulated_counts = _candidate_outfit_counts(simulated_wardrobe, unique_occasions)

    new_outfits_by_occasion = {
        occasion: max(0, simulated_counts.get(occasion, 0) - base_counts.get(occasion, 0))
        for occasion in unique_occasions
    }
    total_new_outfits = sum(new_outfits_by_occasion.values())
    utility = round(float(total_new_outfits) * suitability, 3)
    return {
        "id": str(archetype.get("id", "virtual_item")),
        "name": str(archetype.get("name", "Virtual archetype")),
        "category": str(archetype.get("category", "top")),
        "suitability": round(suitability, 3),
        "new_outfits_total": total_new_outfits,
        "new_outfits_by_occasion": new_outfits_by_occasion,
        "utility": utility,
        "virtual_item": virtual_item,
    }


def rank_gaps(wardrobe: list[Any], occasions: list[str] | None = None) -> list[dict[str, Any]]:
    results = [gap_for_archetype(archetype, wardrobe, occasions) for archetype in load_archetypes()]
    return sorted(results, key=lambda item: (-float(item["utility"]), -int(item["new_outfits_total"]), str(item["name"])))


def analyze_gaps(wardrobe: list[Any], occasions: list[str] | None = None) -> dict[str, Any]:
    ranked = rank_gaps(wardrobe, occasions)
    return {"results": ranked, "count": len(ranked)}
