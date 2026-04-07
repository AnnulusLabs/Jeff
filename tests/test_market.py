"""Tests for jeff.sense.market — Polymarket client."""

import json

import jeff.sense.market as market


def _fake_market_data(question="Will X happen?", yes=0.65, no=0.35, volume=100000):
    return {
        "id": "test-123",
        "question": question,
        "outcomePrices": json.dumps([str(yes), str(no)]),
        "volume": volume,
        "liquidity": 50000,
        "active": True,
        "closed": False,
        "slug": "will-x-happen",
        "description": "Test market",
        "endDate": "2026-12-31",
    }


def _fake_event_data(title="Test Event", markets=None):
    return {
        "id": "event-456",
        "title": title,
        "slug": "test-event",
        "volume": 200000,
        "liquidity": 100000,
        "markets": markets or [_fake_market_data()],
    }


def test_parse_market():
    m = market._parse_market(_fake_market_data())
    assert m.id == "test-123"
    assert m.question == "Will X happen?"
    assert abs(m.outcome_yes - 0.65) < 0.01
    assert abs(m.outcome_no - 0.35) < 0.01
    assert m.active is True
    assert m.closed is False
    assert m.volume == 100000


def test_parse_market_missing_prices():
    data = _fake_market_data()
    data["outcomePrices"] = ""
    m = market._parse_market(data)
    assert m.outcome_yes == 0.5
    assert m.outcome_no == 0.5


def test_parse_event():
    e = market._parse_event(_fake_event_data())
    assert e.id == "event-456"
    assert e.title == "Test Event"
    assert len(e.markets) == 1
    assert e.markets[0].question == "Will X happen?"


def test_market_summary():
    m = market._parse_market(_fake_market_data())
    s = m.summary()
    assert "Will X happen?" in s
    assert "YES 65%" in s
    assert "ACTIVE" in s


def test_event_summary():
    e = market._parse_event(_fake_event_data())
    s = e.summary()
    assert "Test Event" in s
    assert "YES 65%" in s


def test_format_markets_empty():
    assert market.format_markets([]) == "No markets found."


def test_format_events_empty():
    assert market.format_events([]) == "No events found."


def test_search_markets_handles_network_error(monkeypatch):
    monkeypatch.setattr(market.httpx, "get", _raise_connection_error)
    result = market.search_markets("test")
    assert result == []


def test_get_market_handles_network_error(monkeypatch):
    monkeypatch.setattr(market.httpx, "get", _raise_connection_error)
    result = market.get_market("test-123")
    assert result is None


def _raise_connection_error(*args, **kwargs):
    raise market.httpx.ConnectError("offline")


def test_market_server_wraps_library(monkeypatch):
    """market_server.py is a transparent wrapper — no business logic."""
    from jeff.sense import market_server

    called = {}

    def fake_search(**kwargs):
        called["search"] = kwargs
        return [market._parse_market(_fake_market_data())]

    monkeypatch.setattr(market_server, "search_markets", fake_search)
    monkeypatch.setattr(market_server, "format_markets", lambda m: "formatted")

    result = market_server.search(query="test", limit=5)
    assert result["success"] is True
    assert result["output"] == "formatted"
    assert called["search"]["query"] == "test"
    assert called["search"]["limit"] == 5


def test_market_server_odds_wraps_library(monkeypatch):
    from jeff.sense import market_server

    fake = market._parse_market(_fake_market_data())
    monkeypatch.setattr(market_server, "get_market", lambda mid: fake)

    result = market_server.odds(market_id="test-123")
    assert result["success"] is True
    assert result["yes"] == 0.65
    assert result["no"] == 0.35
