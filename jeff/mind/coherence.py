"""Law IV coherence functional and a discrete awareness integral."""

from __future__ import annotations

import math
from collections import Counter
from typing import Hashable, Sequence


def phi(k_history: Sequence[Hashable], alphabet_size: int | None = None) -> float:
    """Coherence of a finite K-history in [0, 1]."""
    n = len(k_history)
    if n < 2:
        return 0.0
    counts = Counter(k_history)
    if len(counts) == 1:
        return 1.0
    h = -sum((c / n) * math.log2(c / n) for c in counts.values())
    support = min(alphabet_size or n, n)
    h_max = math.log2(support) if support > 1 else 0.0
    return 1.0 if h_max == 0 else max(0.0, 1.0 - h / h_max)


def awareness_integral(
    rho_series: Sequence[float],
    k_magnitudes: Sequence[float],
    k_history: Sequence[Hashable],
    alphabet_size: int | None = None,
) -> float:
    """Discrete Law IV awareness integral over a retained K-history."""
    if len(rho_series) != len(k_magnitudes) or len(k_magnitudes) != len(k_history):
        raise ValueError("rho_series, k_magnitudes, and k_history must be the same length")
    coherence = phi(k_history, alphabet_size=alphabet_size)
    return sum(r * k * coherence for r, k in zip(rho_series, k_magnitudes))
