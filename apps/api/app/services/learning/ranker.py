"""Lightweight logistic-ranker utilities for outfit learning.

This phase intentionally avoids LightGBM. The module keeps the earlier rule-score
blend, applies inverse propensity weighting, and exposes a small logistic model
that can operate in mock/offline mode without the ML extras installed.
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping, Sequence


def cold_start_alpha(n: int, N0: int) -> float:
    """Blend factor for cold-start ranking.

    The chosen schedule follows the requirement: alpha = max(0.2, 1 - n / N0).
    """
    n = max(0, int(n))
    N0 = max(1, int(N0))
    return max(0.2, 1.0 - (n / N0))


def ips_weight(propensity: float) -> float:
    """Inverse-propensity weighting; lower propensities are upweighted."""
    propensity = max(float(propensity), 1e-6)
    return 1.0 / propensity


def sigmoid(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _as_feature_vector(features: Mapping[str, float] | Sequence[float] | None) -> list[float]:
    if features is None:
        return []
    if isinstance(features, Mapping):
        return [float(value) for value in features.values()]
    if isinstance(features, (list, tuple)):
        return [float(value) for value in features]
    return [float(features)]


def fit_logistic_regression(
    rows: Sequence[Mapping[str, float] | Sequence[float]],
    labels: Sequence[int | float],
    *,
    learning_rate: float = 0.1,
    epochs: int = 300,
) -> dict[str, Any]:
    """Fit a tiny logistic regression model with batch gradient descent.

    The implementation stays dependency-free so it can run in the standard API
    environment when the `ml` extras are not installed.
    """
    if not rows:
        return {"weights": [], "bias": 0.0}

    feature_count = max(len(_as_feature_vector(rows[0])), 1)
    weights = [0.0 for _ in range(feature_count)]
    bias = 0.0

    for _ in range(max(1, epochs)):
        gradient_w = [0.0 for _ in range(feature_count)]
        gradient_b = 0.0
        for row, label in zip(rows, labels):
            vector = _as_feature_vector(row)
            if len(vector) < feature_count:
                vector = vector + [0.0] * (feature_count - len(vector))
            margin = bias + sum(w * value for w, value in zip(weights, vector))
            prediction = sigmoid(margin)
            error = prediction - float(label)
            for idx, value in enumerate(vector):
                gradient_w[idx] += error * value
            gradient_b += error

        if not any(gradient_w):
            break

        step = learning_rate / max(1, len(rows))
        for idx in range(feature_count):
            weights[idx] -= step * gradient_w[idx]
        bias -= step * gradient_b

    return {"weights": weights, "bias": bias}


def predict_logistic_score(model: Mapping[str, Any], features: Mapping[str, float] | Sequence[float]) -> float:
    weights = list(model.get("weights", []))
    bias = float(model.get("bias", 0.0))
    vector = _as_feature_vector(features)
    if not weights:
        if not vector:
            return 0.5
        return sigmoid(float(vector[0]))
    if len(vector) < len(weights):
        vector = vector + [0.0] * (len(weights) - len(vector))
    if len(vector) > len(weights):
        vector = vector[: len(weights)]
    margin = bias + sum(weight * value for weight, value in zip(weights, vector))
    return sigmoid(margin)


def blend_rank_score(base_score: float, model_score: float, *, n: int, N0: int) -> float:
    alpha = cold_start_alpha(n=n, N0=N0)
    blended = (1.0 - alpha) * base_score + alpha * model_score
    return round(max(0.0, min(1.0, blended)), 6)


def score_with_ips(base_score: float, model_score: float, *, propensity: float, n: int, N0: int) -> float:
    blended = blend_rank_score(base_score, model_score, n=n, N0=N0)
    return round(blended * ips_weight(propensity), 6)
