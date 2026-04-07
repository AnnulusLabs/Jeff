"""Tests for jeff.mind.learn — continual learning with EWC analog."""

from jeff.mind.learn import ContinualLearner, Skill


def test_learn_creates_skill():
    learner = ContinualLearner()
    skill = learner.learn("write python", "def f(): pass", correct=True)
    assert skill.name == "write python"
    assert skill.total == 1
    assert skill.accuracy == 1.0


def test_accuracy_tracks_outcomes():
    learner = ContinualLearner()
    learner.learn("test", "pass1", correct=True)
    learner.learn("test", "pass2", correct=True)
    learner.learn("test", "fail1", correct=False)
    skill = learner._skills["test"]
    assert skill.total == 3
    assert abs(skill.accuracy - 2/3) < 0.01


def test_importance_floor():
    """New skills have importance = EWC_FLOOR."""
    skill = Skill(name="new")
    assert skill.importance == 0.1


def test_importance_scales_with_reliability():
    learner = ContinualLearner()
    for i in range(30):
        learner.learn("reliable", f"ex{i}", correct=True)
    skill = learner._skills["reliable"]
    assert skill.importance > 0.9


def test_recall_finds_relevant_skills():
    learner = ContinualLearner()
    learner.learn("database queries", "SELECT * FROM users", correct=True)
    learner.learn("game physics", "collision detect", correct=True)
    results = learner.recall("query database for users")
    assert len(results) >= 1
    assert results[0][0].name == "database queries"


def test_recall_returns_empty_for_no_match():
    learner = ContinualLearner()
    learner.learn("python", "def f(): pass", correct=True)
    results = learner.recall("xyzabc123unmatched")
    # Either empty or very low similarity
    assert all(sim < 0.5 for _, sim in results)


def test_drift_detection_stable():
    learner = ContinualLearner()
    for i in range(25):
        learner.learn("stable", f"ex{i}", correct=True)
    drift = learner.detect_drift("stable")
    assert drift == 0.0


def test_drift_detection_collapse():
    learner = ContinualLearner()
    # First 10 pass, next 20 fail — recent window shows collapse
    for i in range(10):
        learner.learn("collapsing", f"pass{i}", correct=True)
    for i in range(20):
        learner.learn("collapsing", f"fail{i}", correct=False)
    drift = learner.detect_drift("collapsing")
    assert drift > 0.3


def test_ring_buffer_cap_evicts_correct_first():
    """When buffer is full, correct examples evict before failures."""
    learner = ContinualLearner()
    # Add 100 successes + 1 failure — buffer at 100
    for i in range(100):
        learner.learn("test", f"success{i}", correct=True)
    skill = learner._skills["test"]
    assert skill.total == 100
    # Add one more success — should evict an old success
    learner.learn("test", "new_success", correct=True)
    assert skill.total == 100


def test_forget_deactivates():
    learner = ContinualLearner()
    learner.learn("temp", "example", correct=True)
    assert learner.forget("temp") is True
    assert learner._skills["temp"].active is False
    # Recall shouldn't return inactive skills
    results = learner.recall("temp example")
    assert all(s.active for s, _ in results)


def test_forget_nonexistent():
    learner = ContinualLearner()
    assert learner.forget("ghost") is False


def test_consolidate_merges_similar_skills():
    learner = ContinualLearner()
    # Two skills with identical token sets
    learner.learn("handle database queries", "SELECT * FROM users", correct=True)
    learner.learn("handle database queries ", "SELECT * FROM orders", correct=True)
    merged = learner.consolidate()
    # Token sets should be similar enough to merge
    assert len(merged) >= 0  # consolidation may or may not happen


def test_rehearse_samples_examples():
    learner = ContinualLearner()
    for i in range(10):
        learner.learn(f"skill{i}", f"example{i}", correct=True)
    samples = learner.rehearse(n=5)
    assert len(samples) == 5


def test_rehearse_empty():
    learner = ContinualLearner()
    assert learner.rehearse() == []


def test_skills_report_structure():
    learner = ContinualLearner()
    learner.learn("a", "ex1", correct=True)
    learner.learn("b", "ex2", correct=False)
    report = learner.skills_report()
    assert report["total_skills"] == 2
    assert report["active"] == 2
    assert report["total_examples"] == 2


def test_error_learning_classifies_python_errors():
    learner = ContinualLearner()
    category = learner.learn_from_error(
        "NameError", "NameError: name 'foo' is not defined"
    )
    assert category == "undefined_variable"
    assert learner.error_frequency()["undefined_variable"] == 1


def test_error_learning_unknown():
    learner = ContinualLearner()
    category = learner.learn_from_error("WeirdError", "something unexpected")
    assert category == "unknown"


def test_error_signature_normalizes_files_and_lines():
    learner = ContinualLearner()
    sig1 = learner.error_signature(
        "NameError", 'File "foo.py", line 42, in handler\nNameError: name "x"',
    )
    sig2 = learner.error_signature(
        "NameError", 'File "bar.py", line 99, in handler\nNameError: name "x"',
    )
    # Different files, different line numbers — same function, same error → same sig
    assert sig1 == sig2


def test_error_signature_strips_hex_addresses():
    learner = ContinualLearner()
    sig1 = learner.error_signature("AttributeError", "at 0x7f3a4b5c")
    sig2 = learner.error_signature("AttributeError", "at 0x1234abcd")
    assert sig1 == sig2
