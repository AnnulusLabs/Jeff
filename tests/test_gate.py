from jeff.gate import check, flaw_history, history
from jeff.pantry.cluster import _score_consensus


def _happy_path_code() -> str:
    return "def f():\n" + "\n".join(f"    value_{i} = {i}" for i in range(25))


def test_gate_retains_flaws(tmp_path, monkeypatch):
    monkeypatch.setenv("JEFF_GATE_DIR", str(tmp_path))
    result = check(_happy_path_code(), context="unit_test")
    assert not result.passed
    assert [flaw.name for flaw in result.flaws] == ["HAPPY_PATH"]
    assert history()[-1]["flaws"] == ["HAPPY_PATH"]
    assert [flaw.name for flaw in flaw_history()] == ["HAPPY_PATH"]


def test_cluster_uses_flaw_typed_bins(tmp_path, monkeypatch):
    monkeypatch.setenv("JEFF_GATE_DIR", str(tmp_path))
    results = _score_consensus([
        {"content": _happy_path_code()},
        {"content": _happy_path_code()},
        {"content": "Short answer. No code here."},
    ])
    assert results[0]["branchial_cluster"] == "HAPPY_PATH"
    assert results[0]["branchial_flaws"] == ["HAPPY_PATH"]
    assert results[0]["branchial_weight"] > results[2]["branchial_weight"]
    assert results[2]["branchial_cluster"] == "CLEAN"
