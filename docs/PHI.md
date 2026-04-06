# Phase 1: Candidate phi

Law IV uses:

`A(S,T) = ∫ rho(S,t) * |K(S,t)| * phi(K_history(S,t)) dt`

Jeff's current candidate is the Shannon floor:

`phi(K) = 1 - H(K) / H_max`

- `H(K)` is entropy over structural K-event types.
- `H_max` is `log2(min(alphabet_size, |K|))`.
- Jeff's intended alphabet is `gate.CognitiveFlaw`.

Boundary conditions:

- Noise -> `phi = 0`
- Single repeating pattern -> `phi = 1`
- More repeated structure -> larger `phi`

Current wiring:

- `jeff/mind/coherence.py` defines `phi()` and `awareness_integral()`.
- `jeff/mind/evolve.py` uses `phi` as a retention weight and reports `Awareness A`.
- `jeff/pantry/cluster.py` uses `phi` to score structured agreement across model outputs.
- `awareness_integral()` is strict about timestep alignment and raises on mismatched series.

Open:

- Sequence-aware `phi_LZ` is the next refinement.
- Multi-scale K is still out of scope.
- Phase 2 remains the gate K-leak: `GateResult.flaws` must be retained consistently.
