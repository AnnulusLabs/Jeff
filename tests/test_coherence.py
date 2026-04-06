from jeff.mind.coherence import awareness_integral, phi
import pytest


def test_phi_hits_boundaries():
    assert phi([]) == 0.0
    assert phi(["same", "same"]) == 1.0
    assert phi(["a", "b", "c", "d"]) == 0.0


def test_phi_rewards_repeat_structure():
    assert round(phi(["a", "b", "a", "b"]), 2) == 0.5


def test_awareness_integral_uses_coherence():
    assert awareness_integral([1, 1], [1, 1], ["x", "x"]) == 2.0


def test_awareness_integral_rejects_mismatched_series():
    with pytest.raises(ValueError):
        awareness_integral([1, 1], [1], ["x", "x"])
