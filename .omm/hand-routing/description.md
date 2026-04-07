# hand — Multi-Domain Task Routing

Routes tasks to the right model based on domain detection.
The butler doesn't ask which knife to use. He picks the right one.

Key innovations:
- forge.py: Self-builds missing tools at runtime (gripe #28 extension)
- pulse.py: Monitors goal-to-action ratio, catches drift (gripe #21)
- batch.py: Gathers questions, presents once, no drip-feed (gripe #37)
