import copy

from app.services.outfits.features import rank_candidates, score_outfit
from app.services.outfits.rules import hard_filter_candidate, no_formal_shoes_for_lounge, no_two_bottoms


def _item(category, item_id, **kwargs):
    payload = {"id": item_id, "category": category, "is_available": True, "season": "all_season", **kwargs}
    return payload


def test_no_two_bottoms_rejected():
    candidate = {
        "slots": {
            "top": _item("top", "t1"),
            "bottom": _item("bottom", "b1"),
            "ethnic_bottom": _item("ethnic_bottom", "b2"),
            "shoes": _item("shoes", "s1", formality=1),
        }
    }
    assert no_two_bottoms(candidate) is False
    assert hard_filter_candidate(candidate, occasion="casual", season="summer") is False


def test_formal_shoes_rejected_for_lounge_outfit():
    candidate = {
        "slots": {
            "top": _item("top", "t1"),
            "bottom": _item("bottom", "b1"),
            "shoes": _item("shoes", "s1", formality=3),
        }
    }
    assert no_formal_shoes_for_lounge(candidate, occasion="lounge") is False
    assert hard_filter_candidate(candidate, occasion="lounge", season="summer") is False


def test_rank_candidates_is_deterministic_with_seed():
    items_a = [
        _item("top", "ta", style="tailored", color="#000000", novelty=0.7),
        _item("bottom", "ba", formality=2, color="#FFFFFF"),
        _item("shoes", "sa", formality=2, style="formal"),
    ]
    items_b = [
        _item("top", "tb", style="tailored", color="#000000", novelty=0.7),
        _item("bottom", "bb", formality=2, color="#FFFFFF"),
        _item("shoes", "sb", formality=2, style="formal"),
    ]
    candidate_a = {"slots": {"top": items_a[0], "bottom": items_a[1], "shoes": items_a[2]}}
    candidate_b = {"slots": {"top": items_b[0], "bottom": items_b[1], "shoes": items_b[2]}}

    first = rank_candidates([candidate_a, candidate_b], occasion="work", season="summer", body_shape="Hourglass", seed=11)
    second = rank_candidates([copy.deepcopy(candidate_a), copy.deepcopy(candidate_b)], occasion="work", season="summer", body_shape="Hourglass", seed=11)

    assert first[0][0] == second[0][0]
    assert first[0][1] == second[0][1]
    assert score_outfit(candidate_a, occasion="work", season="summer", body_shape="Hourglass", seed=11) == score_outfit(candidate_a, occasion="work", season="summer", body_shape="Hourglass", seed=11)
