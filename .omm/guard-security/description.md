# guard — The Security Stack

The classifier insight: evaluate what a request CAN DO, not what it SAYS.

Four layers, one coordinator:
- basin.py: Capability basin mapping with K-history trust
- firewall.py: Prompt injection defense (pattern + entropy + density)
- sandbox.py: Runtime execution isolation (allowed/denied commands, paths)
- enforcer.py: Coordinates all four layers into one decision

Key innovation: accountability-gated access. Instead of "you can't" →
"you can, and here's who's accountable." Waiver system, not wall system.
