import itertools

from app.services.catalog.gaps import analyze_gaps, load_archetypes
from app.services.outfits.rules import hard_filter_candidate


def _item(item_id, category, **kwargs):
    payload = {
        "id": item_id,
        "category": category,
        "is_available": True,
        "season": "all_season",
        "seasons": ["all_season"],
        "occasions": ["casual", "college", "work"],
        **kwargs,
    }
    return payload


def _bruteforce_count(wardrobe, occasion):
    top_items = [item for item in wardrobe if item["category"] == "top"]
    bottom_items = [item for item in wardrobe if item["category"] == "bottom"]
    shoe_items = [item for item in wardrobe if item["category"] == "shoes"]
    valid = 0
    for top, bottom, shoe in itertools.product(top_items, bottom_items, shoe_items):
        candidate = {"slots": {"top": top, "bottom": bottom, "shoes": shoe}}
        if hard_filter_candidate(candidate, occasion, "all_season"):
            valid += 1
    return valid


def test_counterfactual_gap_counts_match_bruteforce_on_tiny_wardrobe():
    wardrobe = [
        _item("t1", "top", style="casual", color="#111827", formality=1),
        _item("b1", "bottom", style="relaxed", color="#E5E7EB", formality=1),
        _item("s1", "shoes", style="casual", color="#FFFFFF", formality=1),
    ]
    archetype = load_archetypes()[0]
    virtual = archetype["virtual_item"]

    baseline = _bruteforce_count(wardrobe, "college")
    augmented = _bruteforce_count(wardrobe + [virtual], "college")
    delta = augmented - baseline

    payload = analyze_gaps(wardrobe, occasions=["college"])
    result = next(item for item in payload["results"] if item["id"] == archetype["id"])
    assert result["new_outfits_by_occasion"]["college"] == delta
    assert result["new_outfits_total"] == delta


def test_gap_analysis_is_reproducible_across_runs():
    wardrobe = [
        _item("t1", "top", style="casual", color="#111827", formality=1),
        _item("b1", "bottom", style="relaxed", color="#E5E7EB", formality=1),
        _item("s1", "shoes", style="casual", color="#FFFFFF", formality=1),
        _item("t2", "top", style="formal", color="#1F2937", formality=2),
    ]
    first = analyze_gaps(wardrobe)
    second = analyze_gaps(wardrobe)
    assert first == second
    assert first["count"] == len(first["results"])
    assert all(item["utility"] >= 0 for item in first["results"])
