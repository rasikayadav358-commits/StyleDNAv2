"""Synthetic offline learning data for the recommendation loop."""

from __future__ import annotations

import random
from typing import Any


def _sigmoid(value: float) -> float:
    if value >= 0:
        z = __import__("math").exp(-value)
        return 1.0 / (1.0 + z)
    z = __import__("math").exp(value)
    return z / (1.0 + z)


def generate_synthetic_learning_curve(*, rounds: int = 200, seed: int = 7, mock_mode: bool = True) -> list[dict[str, Any]]:
    """Create a mock learning curve in which the like-rate improves over time.

    The simulation is intentionally simple and deterministic given a seed. It also
    logs the selected candidate and the eventual reward so it can be used for
    offline evaluation without a real ML stack.
    """
    if not mock_mode:
        return []

    rng = random.Random(seed)
    history: list[dict[str, Any]] = []
    latent_w = {"style": 1.8, "occasion": 1.6, "body_fit": 1.4, "novelty": 0.9}

    for round_idx in range(max(1, rounds)):
        good_candidate = {
            "id": "good",
            "hard_filter": True,
            "score": 0.8,
            "features": {"style": 0.9, "occasion": 0.9, "body_fit": 0.8, "novelty": 0.7},
        }
        weak_candidate = {
            "id": "weak",
            "hard_filter": True,
            "score": 0.25,
            "features": {"style": 0.2, "occasion": 0.3, "body_fit": 0.4, "novelty": 0.3},
        }

        if round_idx < 60:
            selected = rng.choice([good_candidate, weak_candidate])
            base_probability = 0.42
        else:
            selected = good_candidate
            base_probability = 0.52 + min(0.3, round_idx / 500)

        score = sum(latent_w[key] * selected["features"].get(key, 0.0) for key in latent_w)
        final_probability = min(0.96, max(0.1, _sigmoid(score - 2.0) * 0.8 + base_probability * 0.2))
        reward = 1 if rng.random() < final_probability else 0
        history.append({
            "round": round_idx,
            "selected": selected["id"],
            "like": reward,
            "probability": round(final_probability, 4),
            "hard_filter_ok": True,
        })

    return history
