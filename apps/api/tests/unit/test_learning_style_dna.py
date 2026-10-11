from app.services.learning.style_dna import update_style_state_from_event


def test_style_vector_shifts_toward_simulated_preference_within_20_events():
    state = {"style_vector": {"minimal": 0.0, "ethnic": 0.0, "tailored": 0.0, "streetwear": 0.0, "classic": 0.0, "sporty": 0.0, "boho": 0.0, "luxury": 0.0, "casual": 0.0, "formal": 0.0}, "tag_affinities": {}, "n_events": 0}

    for _ in range(20):
        state = update_style_state_from_event(state, "save", ["minimal", "tailored"], alpha=0.25)

    assert state["style_vector"]["minimal"] > 0.35
    assert state["style_vector"]["tailored"] > 0.35
    assert state["style_vector"]["minimal"] > state["style_vector"]["ethnic"]
    assert state["style_vector"]["tailored"] > state["style_vector"]["streetwear"]
