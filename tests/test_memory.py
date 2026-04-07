"""Tests for jeff.bone.memory — Three-pipeline procedural memory."""

from jeff.bone.memory import Pipeline, ProceduralMemory


def test_store_and_retrieve_episodic(tmp_path):
    mem = ProceduralMemory(db_path=tmp_path / "test.db")
    mem.store_episodic("fix-bug", "ran pytest, 3 failures", context="cwd:/app")
    entries = mem.by_pipeline(Pipeline.EPISODIC)
    assert len(entries) == 1
    assert entries[0].key == "fix-bug"
    assert entries[0].pipeline == Pipeline.EPISODIC


def test_store_and_retrieve_procedural(tmp_path):
    mem = ProceduralMemory(db_path=tmp_path / "test.db")
    mem.store_procedural("refactor", "extract method, run gate, verify", score=0.8)
    entries = mem.top_procedural()
    assert len(entries) == 1
    assert entries[0].score == 0.8
    assert entries[0].key == "refactor"


def test_store_and_retrieve_semantic(tmp_path):
    mem = ProceduralMemory(db_path=tmp_path / "test.db")
    mem.store_semantic("project-convention", "use ruff, 100 char line length")
    entries = mem.by_pipeline(Pipeline.SEMANTIC)
    assert len(entries) == 1
    assert entries[0].key == "project-convention"


def test_search_across_pipelines(tmp_path):
    mem = ProceduralMemory(db_path=tmp_path / "test.db")
    mem.store_episodic("deploy", "deployed to staging, green")
    mem.store_procedural("deploy", "git push, wait for CI, merge", score=0.9)
    mem.store_semantic("deploy", "always deploy to staging before prod")
    results = mem.search("deploy")
    assert len(results) == 3


def test_search_filtered_by_pipeline(tmp_path):
    mem = ProceduralMemory(db_path=tmp_path / "test.db")
    mem.store_episodic("test", "ran tests")
    mem.store_procedural("test", "golden path for testing", score=0.7)
    results = mem.search("test", pipeline=Pipeline.PROCEDURAL)
    assert len(results) == 1
    assert results[0].pipeline == Pipeline.PROCEDURAL


def test_reinforce_and_penalize(tmp_path):
    mem = ProceduralMemory(db_path=tmp_path / "test.db")
    row_id = mem.store_procedural("pattern", "do X then Y", score=0.5)
    mem.reinforce(row_id, delta=0.3)
    entry = mem.by_key("pattern")[0]
    assert abs(entry.score - 0.8) < 0.01
    mem.penalize(row_id, delta=0.2)
    entry = mem.by_key("pattern")[0]
    assert abs(entry.score - 0.6) < 0.01


def test_score_clamps_at_boundaries(tmp_path):
    mem = ProceduralMemory(db_path=tmp_path / "test.db")
    row_id = mem.store_procedural("high", "near max", score=0.95)
    mem.reinforce(row_id, delta=0.2)
    entry = mem.by_key("high")[0]
    assert entry.score == 1.0

    row_id2 = mem.store_procedural("low", "near min", score=0.05)
    mem.penalize(row_id2, delta=0.2)
    entry2 = mem.by_key("low")[0]
    assert entry2.score == 0.0


def test_count_by_pipeline(tmp_path):
    mem = ProceduralMemory(db_path=tmp_path / "test.db")
    mem.store_episodic("a", "content a")
    mem.store_episodic("b", "content b")
    mem.store_procedural("c", "content c")
    assert mem.count() == 3
    assert mem.count(Pipeline.EPISODIC) == 2
    assert mem.count(Pipeline.PROCEDURAL) == 1
    assert mem.count(Pipeline.SEMANTIC) == 0


def test_summary(tmp_path):
    mem = ProceduralMemory(db_path=tmp_path / "test.db")
    mem.store_procedural("deploy", "golden deploy path", score=0.9)
    s = mem.summary()
    assert "1 procedural" in s
    assert "deploy" in s


def test_recent(tmp_path):
    import time
    mem = ProceduralMemory(db_path=tmp_path / "test.db")
    mem.store_episodic("old", "old event")
    time.sleep(0.01)  # ensure distinct timestamps
    mem.store_episodic("new", "new event")
    recent = mem.recent(limit=1)
    assert len(recent) == 1
    assert recent[0].key == "new"


def test_golden_path_storage_on_high_phi(tmp_path, monkeypatch):
    """Storage mechanism: high phi + success → golden path stored."""
    from jeff.mind.evolve import EvolutionEngine, KEntry, CycleResult
    mem = ProceduralMemory(db_path=tmp_path / "test.db")
    monkeypatch.setenv("JEFF_GATE_DIR", str(tmp_path / "gate"))

    engine = EvolutionEngine(memory=mem)
    # Seed K-history with repeated flaw types to get high phi
    for _ in range(5):
        engine.k_history.append(KEntry(
            timestamp=0, phase="test", task="fix", what_failed="err",
            why="gate", lesson="handle errors", severity=0.5, kind="HAPPY_PATH",
        ))

    result = CycleResult(cycle=1, task="fix authentication bug")
    result.improved = True
    engine._maybe_store_golden_path("fix authentication bug", result)

    entries = mem.top_procedural()
    assert len(entries) >= 1
    assert "fix authentication bug" in entries[0].content
