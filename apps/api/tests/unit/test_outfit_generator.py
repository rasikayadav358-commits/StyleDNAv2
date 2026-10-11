import time

from app.services.outfits.explain import explain_outfit
from app.services.outfits.generator import generate_outfits
from app.services.outfits.variations import VARIATION_TYPES, generate_variations


def _item(item_id, category, **kwargs):
    payload = {
        "id": item_id,
        "category": category,
        "is_available": True,
        "season": "all_season",
        **kwargs,
    }
    return payload


def test_demo_wardrobe_yields_distinct_outfits_under_one_second():
    wardrobe = [
        _item("t1", "top", color="#000000", style="tailored", formality=2, neckline="v_neck"),
        _item("t2", "top", color="#1E3A8A", style="casual", formality=1, neckline="round_neck"),
        _item("b1", "bottom", color="#FFFFFF", style="classic", formality=1, fit="straight"),
        _item("b2", "bottom", color="#E5E7EB", style="relaxed", formality=1, fit="wide_leg"),
        _item("s1", "shoes", color="#B0B0B0", style="formal", formality=2),
        _item("s2", "shoes", color="#3B82F6", style="casual", formality=1),
        _item("l1", "layer", color="#F5F5DC", style="structured", formality=2),
        _item("d1", "dress", color="#FF0000", style="dramatic", formality=3),
        _item("bag1", "bag", color="#000000", style="minimal", formality=1),
    ]

    start = time.perf_counter()
    outfits = generate_outfits(
        wardrobe,
        occasion="work",
        season="summer",
        body_shape="Hourglass",
        attrs={"neckline": "v_neck", "fit": "tailored", "length": "knee", "rise": "mid"},
        limit=6,
        seed=7,
    )
    elapsed = time.perf_counter() - start

    assert len(outfits) >= 3
    assert len({tuple(sorted(candidate.item_ids)) for candidate in outfits}) >= 3
    assert elapsed < 1.0


def test_variations_and_explanations_are_factual_and_complete():
    candidate = {
        "slots": {
            "top": _item("t1", "top", color="#000000", style="tailored", formality=2),
            "bottom": _item("b1", "bottom", color="#FFFFFF", style="classic", formality=1),
            "shoes": _item("s1", "shoes", color="#B0B0B0", style="formal", formality=2),
        }
    }
    variations = generate_variations(candidate, occasion="work", season="summer")
    reasons = explain_outfit(candidate, occasion="work", season="summer", body_shape="Hourglass")

    assert len(VARIATION_TYPES) == 8
    assert len(variations) == 8
    assert len(reasons) >= 3
    assert all(isinstance(reason, str) and len(reason) > 20 for reason in reasons)
