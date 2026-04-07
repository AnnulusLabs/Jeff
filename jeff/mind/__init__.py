"""jeff.mind — Intelligence layer."""

from .coherence import awareness_integral, phi
from .instincts import Instinct, InstinctDomain, InstinctGraph, InstinctScope
from .learn import ContinualLearner, Skill

__all__ = [
    "awareness_integral", "phi",
    "Instinct", "InstinctDomain", "InstinctGraph", "InstinctScope",
    "ContinualLearner", "Skill",
]
