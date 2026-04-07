"""Tests for jeff.mind.instincts — Instinct graph with confidence decay."""

import time

from jeff.mind.instincts import Instinct, InstinctDomain, InstinctGraph, InstinctScope


def test_observe_creates_instinct():
    graph = InstinctGraph()
    inst = graph.observe(
        trigger="see SQL injection",
        action="use parameterized query",
        domain=InstinctDomain.SECURITY,
        project_id="jeff",
    )
    assert inst.trigger == "see SQL injection"
    assert inst.domain == InstinctDomain.SECURITY
    assert len(graph) == 1


def test_repeat_observation_reinforces():
    graph = InstinctGraph()
    inst1 = graph.observe(
        trigger="bare except",
        action="catch specific exception",
        project_id="jeff",
    )
    inst2 = graph.observe(
        trigger="bare except",
        action="catch specific exception",
        project_id="jeff",
    )
    assert inst1.id == inst2.id
    assert inst2.reinforcements == 1
    assert inst2.confidence > inst1.confidence - 0.01  # increased


def test_contradict_reduces_confidence():
    graph = InstinctGraph()
    inst = graph.observe(
        trigger="test", action="action", project_id="jeff",
    )
    before = inst.confidence
    inst.contradict(evidence="turned out wrong")
    assert inst.confidence < before
    assert inst.contradictions == 1


def test_confidence_decays_over_time():
    inst = Instinct(
        id="x", trigger="t", action="a",
        last_seen=time.time() - (60 * 86400),  # 60 days ago
        confidence=0.8,
    )
    # After 60 days with 30-day half-life, should be ~0.25
    assert inst.effective_confidence < 0.3
    assert inst.effective_confidence > 0.15


def test_active_for_filters_by_confidence():
    graph = InstinctGraph()
    graph.observe(trigger="a", action="b", project_id="jeff")
    # New instinct has confidence 0.5
    active = graph.active_for(project_id="jeff", min_confidence=0.5)
    assert len(active) >= 1
    high = graph.active_for(project_id="jeff", min_confidence=0.9)
    assert len(high) == 0


def test_active_for_filters_by_domain():
    graph = InstinctGraph()
    graph.observe(
        trigger="security", action="fix", domain=InstinctDomain.SECURITY,
        project_id="jeff",
    )
    graph.observe(
        trigger="style", action="reformat", domain=InstinctDomain.CODE_STYLE,
        project_id="jeff",
    )
    sec_only = graph.active_for(
        project_id="jeff", domain=InstinctDomain.SECURITY,
    )
    assert len(sec_only) == 1
    assert sec_only[0].domain == InstinctDomain.SECURITY


def test_promote_to_global():
    graph = InstinctGraph()
    graph.observe(trigger="x", action="y", project_id="project-a")
    graph.observe(trigger="x", action="y", project_id="project-b")
    promoted = graph.promote_if_eligible(min_projects=2)
    assert len(promoted) == 1
    assert promoted[0].scope == InstinctScope.GLOBAL


def test_compile_for_context_respects_token_budget():
    graph = InstinctGraph()
    for i in range(50):
        graph.observe(
            trigger=f"trigger_{i}" * 5,  # long text
            action=f"action_{i}" * 5,
            project_id="jeff",
        )
    compiled = graph.compile_for_context(project_id="jeff", max_tokens=200)
    assert len(compiled) < 50  # budget constraint hit


def test_garbage_collect_removes_low_confidence():
    graph = InstinctGraph()
    inst = graph.observe(trigger="t", action="a", project_id="jeff")
    # Force confidence very low
    inst.confidence = 0.05
    removed = graph.garbage_collect(min_confidence=0.1)
    assert removed == 1
    assert len(graph) == 0


def test_make_id_stable():
    graph = InstinctGraph()
    id1 = graph._make_id("trigger", "action", "project")
    id2 = graph._make_id("trigger", "action", "project")
    assert id1 == id2
    id3 = graph._make_id("trigger", "action", "different")
    assert id1 != id3
