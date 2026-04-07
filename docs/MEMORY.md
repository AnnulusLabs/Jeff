# Memory

Jeff has three-pipeline procedural memory. Nothing is ever discarded.

## Pipelines

| Pipeline | What it stores | Example |
|----------|---------------|---------|
| **Episodic** | What happened — task trajectories, session events | "ran pytest, 3 failures in auth module" |
| **Procedural** | How to do things — golden paths, tool-use patterns | "extract method, run gate, verify no regressions" |
| **Semantic** | Domain knowledge — project conventions, codebase facts | "this project uses ruff, 100 char line length" |

## Golden Paths (coherence-based storage)

When a task succeeds and the K-history shows high phi (coherence), the evolve engine stores the trajectory as a procedural memory. This is option 3 from the design space — coherence-based, not manual tagging.

The threshold is `EvolutionEngine.GOLDEN_PATH_PHI_THRESHOLD` (default 0.4, tunable). 0.4 means moderate coherence — not noise, not perfectly uniform. Sessions where the same flaw type recurs and gets addressed — showing structured learning — are the ones worth remembering. Adjust the threshold if your workload produces different φ distributions.

This closes a loop: Phase 1's coherence functional drives Phase 4b's memory selection. Three phases earning each other's keep.

## Storage

SQLite at `~/.jeff/memory/procedural.db`. FTS5 full-text search. Scores reinforced on retrieval success, penalized when a retrieved memory leads to a gate failure.

**Known limitation:** Search is lexical (SQLite FTS5), not embedding-based semantic search. This is deliberate — no vector DB, no embedding model dependency. The tradeoff is that synonyms and paraphrases won't match. If this proves limiting, the upgrade path is adding an embedding column without replacing FTS5.

## CLI

```text
jeff memory                         # summary: counts per pipeline, top golden paths
jeff memory deploy                  # search all pipelines for "deploy"
jeff memory -p procedural refactor  # search procedural pipeline only
```

## Retrieval in the evolve loop

`EvolutionEngine.retrieve_relevant(task)` searches procedural memory for patterns matching the current task. Retrieved memories are formatted as strategy context alongside K-derived strategies.

## Wiring

```
gate failure → K-history → phi scores structure → high phi + success → golden path stored
                                                                         ↓
next similar task → retrieve_relevant() → procedural memories inform strategy selection
```
