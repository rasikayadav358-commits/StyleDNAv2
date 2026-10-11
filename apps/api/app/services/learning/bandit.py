"""Exploration policies for outfit recommendation.

The bandit is intentionally conservative: it only explores among candidates that
pass the hard filter gate. This prevents invalid outfits from ever being selected
just because they look promising in a noisy score estimate.
"""

from __future__ import annotations

import random
from typing import Any, Callable, Mapping, Sequence


def _passes_hard_filter(candidate: Mapping[str, Any] | Any, hard_filter: Callable[[Any], bool] | None = None) -> bool:
    if hard_filter is None:
        if isinstance(candidate, dict):
            return bool(candidate.get("hard_filter", True))
        return True
    return bool(hard_filter(candidate))


def epsilon_greedy_select(
    candidates: Sequence[Any],
    *,
    epsilon: float = 0.1,
    hard_filter: Callable[[Any], bool] | None = None,
    score_key: str = "score",
    rng: random.Random | None = None,
) -> Any:
    """Choose the best valid candidate with epsilon-greedy exploration."""
    valid = [candidate for candidate in candidates if _passes_hard_filter(candidate, hard_filter)]
    if not valid:
        return None

    engine = rng or random.Random()
    if engine.random() < max(0.0, min(1.0, epsilon)):
        return engine.choice(valid)

    return max(valid, key=lambda candidate: float(candidate.get(score_key, candidate.get("base_score", 0.0))))
