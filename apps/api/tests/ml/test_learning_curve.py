from statistics import mean

from app.services.learning.bandit import epsilon_greedy_select
from app.services.learning.ranker import cold_start_alpha, ips_weight
from app.services.learning.synthetic import generate_synthetic_learning_curve


def test_like_rate_rises_over_200_simulated_rounds():
    history = generate_synthetic_learning_curve(rounds=200, seed=7, mock_mode=True)

    assert len(history) == 200
    first_half = mean(item["like"] for item in history[:100])
    second_half = mean(item["like"] for item in history[100:])
    assert first_half < second_half
    assert second_half > 0.6


def test_bandit_and_ranker_helpers_are_stable():
    assert cold_start_alpha(n=10, N0=20) == 0.5
    assert ips_weight(0.25) > 1.0
    candidates = [
        {"id": "a", "score": 0.21, "hard_filter": True},
        {"id": "b", "score": 0.88, "hard_filter": True},
    ]
    selected = epsilon_greedy_select(candidates, epsilon=0.0)
    assert selected["id"] == "b"
