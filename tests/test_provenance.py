"""Tests for jeff.blood.provenance — W3C PROV-DM audit trail."""

from jeff.blood.provenance import (
    EntityType,
    ProvenanceRecord,
    ProvenanceTracker,
    SourceType,
)


def test_record_basic():
    tracker = ProvenanceTracker()
    rec = tracker.record(
        content="print('hello')",
        source="user-input",
        author="steve@annulus",
    )
    assert rec.record_id.startswith("prov:")
    assert rec.source_type == SourceType.HUMAN
    assert rec.trust_score == 0.7


def test_classify_github_source():
    tracker = ProvenanceTracker()
    rec = tracker.record(
        content="def f(): pass",
        source="github.com/user/repo",
        author="unknown",
    )
    assert rec.source_type == SourceType.GITHUB


def test_classify_agent_source():
    tracker = ProvenanceTracker()
    rec = tracker.record(
        content="def f(): pass",
        source="claude-agent",
        author="claude",
    )
    assert rec.source_type == SourceType.AGENT


def test_classify_self_source():
    tracker = ProvenanceTracker()
    rec = tracker.record(
        content="def f(): pass",
        source="jeff-internal",
        author="self",
    )
    assert rec.source_type == SourceType.SELF


def test_dedupes_by_content_hash():
    tracker = ProvenanceTracker()
    rec1 = tracker.record(content="same", source="a", author="alice")
    rec2 = tracker.record(content="same", source="b", author="bob")
    assert rec1.record_id == rec2.record_id


def test_derive_creates_lineage():
    tracker = ProvenanceTracker()
    parent = tracker.record(content="original", source="human", author="alice@example")
    child = tracker.derive(
        content="modified",
        parent_hash=parent.content_hash,
        source="agent",
        author="claude",
        transformations=["refactored"],
    )
    assert child.derived_from == [parent.record_id]
    assert child.transformations == ["refactored"]


def test_get_lineage_traces_back():
    tracker = ProvenanceTracker()
    gp = tracker.record(content="v1", source="human", author="alice@example")
    p = tracker.derive(content="v2", parent_hash=gp.content_hash, author="alice@example")
    c = tracker.derive(content="v3", parent_hash=p.content_hash, author="claude")
    lineage = tracker.get_lineage(c.record_id)
    assert lineage["depth"] >= 1
    assert len(lineage["parents"]) >= 1


def test_verify_bumps_trust():
    tracker = ProvenanceTracker()
    rec = tracker.record(content="test", source="agent", author="bot")
    before = rec.trust_score
    assert tracker.verify(rec.record_id, method="tests-pass")
    assert rec.trust_score > before
    assert rec.verified
    assert rec.verification_method == "tests-pass"


def test_infections_reduce_trust():
    tracker = ProvenanceTracker()
    clean = tracker.record(
        content="clean code", source="self", author="jeff", infections_found=0,
    )
    infected = tracker.record(
        content="infected code", source="self", author="jeff", infections_found=3,
    )
    assert infected.trust_score < clean.trust_score


def test_blocked_when_untrusted_and_infected():
    tracker = ProvenanceTracker()
    rec = tracker.record(
        content="bad", source="unknown", author="unknown", infections_found=5,
    )
    assert rec.blocked is True


def test_get_suspicious_filters():
    tracker = ProvenanceTracker()
    tracker.record(content="trusted", source="self", author="jeff")
    tracker.record(content="untrusted", source="unknown", author="unknown", infections_found=3)
    suspicious = tracker.get_suspicious(trust_threshold=0.3)
    assert len(suspicious) >= 1
    assert all(r.trust_score < 0.3 for r in suspicious)


def test_report_includes_counts():
    tracker = ProvenanceTracker()
    tracker.record(content="a", source="self", author="jeff")
    tracker.record(content="b", source="github", author="alice@example")
    report = tracker.report()
    assert "Provenance:" in report
    assert "2 records" in report


def test_record_serialization_roundtrip():
    tracker = ProvenanceTracker()
    rec = tracker.record(
        content="original",
        source="github.com/jeff/jeff",
        author="steve@annulus",
        entity_type=EntityType.CODE,
    )
    data = rec.to_dict()
    restored = ProvenanceRecord.from_dict(data)
    assert restored.record_id == rec.record_id
    assert restored.source_type == rec.source_type
    assert restored.entity_type == rec.entity_type
