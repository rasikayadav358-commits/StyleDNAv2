"""Color harmony utilities for outfit scoring."""

from __future__ import annotations

import colorsys
import math
from typing import Any


def _normalize_hex(value: Any) -> tuple[float, float, float]:
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return tuple(float(v) for v in value)
    if isinstance(value, str):
        hex_value = value.strip().lstrip("#")
        if len(hex_value) == 3:
            hex_value = "".join(ch * 2 for ch in hex_value)
        if len(hex_value) == 6:
            return tuple(int(hex_value[i : i + 2], 16) / 255.0 for i in range(0, 6, 2))
    return (1.0, 1.0, 1.0)


def _rgb_to_lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b = rgb
    r = pow(r, 2.2) if r <= 0.04045 else ((r + 0.055) / 1.055) ** 2.4
    g = pow(g, 2.2) if g <= 0.04045 else ((g + 0.055) / 1.055) ** 2.4
    b = pow(b, 2.2) if b <= 0.04045 else ((b + 0.055) / 1.055) ** 2.4

    x = 0.4124 * r + 0.3576 * g + 0.1805 * b
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = 0.0193 * r + 0.1192 * g + 0.9505 * b

    x_n = 0.95047
    y_n = 1.0
    z_n = 1.08883

    def _f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    l = 116 * _f(y / y_n) - 16
    a = 500 * (_f(x / x_n) - _f(y / y_n))
    bb = 200 * (_f(y / y_n) - _f(z / z_n))
    return (l, a, bb)


def _lab_to_hcl(lab: tuple[float, float, float]) -> tuple[float, float]:
    l, a, b = lab
    c = math.sqrt(a * a + b * b)
    h = math.degrees(math.atan2(b, a)) if c != 0 else 0.0
    h = (h + 360.0) % 360.0
    return h, c


def color_distance_lab(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def harmony_score(color_a: Any, color_b: Any) -> float:
    """Return a 0..1 color harmony score based on Lab distance and HCL angle similarity."""
    lab_a = _rgb_to_lab(_normalize_hex(color_a))
    lab_b = _rgb_to_lab(_normalize_hex(color_b))
    delta_e = color_distance_lab(lab_a, lab_b)
    hcl_a = _lab_to_hcl(lab_a)
    hcl_b = _lab_to_hcl(lab_b)
    hue_delta = abs((hcl_a[0] - hcl_b[0]) % 360.0)
    hue_delta = min(hue_delta, 360.0 - hue_delta)
    hue_similarity = 1.0 - (hue_delta / 180.0)
    lab_similarity = 1.0 - min(delta_e / 100.0, 1.0)
    score = 0.7 * lab_similarity + 0.3 * hue_similarity
    return round(max(0.0, min(1.0, score)), 3)


def palette_harmony(colors: list[Any]) -> float:
    """Average the pairwise harmony across a palette."""
    if not colors:
        return 0.5
    if len(colors) == 1:
        return 1.0
    scores = []
    for i in range(len(colors)):
        for j in range(i + 1, len(colors)):
            scores.append(harmony_score(colors[i], colors[j]))
    return round(sum(scores) / len(scores), 3) if scores else 0.5
