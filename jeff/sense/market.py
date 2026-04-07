"""jeff.sense.market — Prediction market client. Polymarket Gamma API.

Public endpoints only. No API keys. No auth. No subscriptions.
Jeff reads the crowd's probability estimates to inform decisions.

AnnulusLabs LLC · April 2026
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

log = logging.getLogger("jeff.sense.market")

GAMMA_API = "https://gamma-api.polymarket.com"
DEFAULT_TIMEOUT = 15
DEFAULT_LIMIT = 10


@dataclass
class Market:
    id: str
    question: str
    outcome_yes: float  # 0-1 implied probability
    outcome_no: float   # 0-1 implied probability
    volume: float       # total traded USD
    liquidity: float
    active: bool
    closed: bool
    slug: str = ""
    description: str = ""
    end_date: str = ""
    volume_24hr: float = 0.0  # 24h volume, liquidity check
    category: str = ""
    image: str = ""

    @property
    def odds_str(self) -> str:
        return f"YES {self.outcome_yes:.0%} / NO {self.outcome_no:.0%}"

    def summary(self) -> str:
        status = "CLOSED" if self.closed else ("ACTIVE" if self.active else "INACTIVE")
        vol = f"vol=${self.volume:,.0f}"
        if self.volume_24hr:
            vol += f" (24h=${self.volume_24hr:,.0f})"
        return (
            f"{self.question}\n"
            f"  {self.odds_str}  {vol}  [{status}]"
        )


@dataclass
class Event:
    id: str
    title: str
    slug: str
    markets: list[Market]
    volume: float = 0.0
    liquidity: float = 0.0

    def summary(self) -> str:
        lines = [f"{self.title} (vol=${self.volume:,.0f}, {len(self.markets)} markets)"]
        for m in self.markets[:5]:
            lines.append(f"  {m.odds_str} — {m.question}")
        if len(self.markets) > 5:
            lines.append(f"  ... and {len(self.markets) - 5} more")
        return "\n".join(lines)


def _parse_market(data: dict[str, Any]) -> Market:
    outcomes = data.get("outcomePrices", "") or data.get("outcomes", "")
    yes, no = 0.5, 0.5
    if isinstance(outcomes, str) and outcomes:
        try:
            import json
            prices = json.loads(outcomes)
            if len(prices) >= 2:
                yes, no = float(prices[0]), float(prices[1])
        except Exception:
            pass
    elif isinstance(outcomes, list) and len(outcomes) >= 2:
        try:
            yes, no = float(outcomes[0]), float(outcomes[1])
        except (ValueError, TypeError):
            pass
    return Market(
        id=str(data.get("id", "")),
        question=data.get("question", data.get("title", "")),
        outcome_yes=yes,
        outcome_no=no,
        volume=float(data.get("volume", 0) or 0),
        liquidity=float(data.get("liquidity", 0) or 0),
        active=bool(data.get("active", False)),
        closed=bool(data.get("closed", False)),
        slug=data.get("slug", ""),
        description=(data.get("description", "") or "")[:500],
        end_date=data.get("endDate", data.get("end_date_iso", "")),
        volume_24hr=float(data.get("volume24hr", 0) or 0),
        category=data.get("groupItemTitle", ""),
        image=data.get("image", ""),
    )


def _parse_event(data: dict[str, Any]) -> Event:
    raw_markets = data.get("markets", [])
    markets = [_parse_market(m) for m in raw_markets] if raw_markets else []
    return Event(
        id=str(data.get("id", "")),
        title=data.get("title", ""),
        slug=data.get("slug", ""),
        markets=markets,
        volume=float(data.get("volume", 0) or 0),
        liquidity=float(data.get("liquidity", 0) or 0),
    )


def search_markets(
    query: str = "",
    active: bool = True,
    closed: bool = False,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> list[Market]:
    """Search Polymarket markets via Gamma API."""
    params: dict[str, Any] = {
        "_limit": min(limit, 100),
        "_offset": offset,
        "active": str(active).lower(),
        "closed": str(closed).lower(),
        "order": "volume",
        "ascending": "false",
    }
    if query:
        params["_q"] = query
    try:
        resp = httpx.get(
            f"{GAMMA_API}/markets",
            params=params,
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return [_parse_market(m) for m in resp.json()]
    except Exception as exc:
        log.warning(f"Polymarket search failed: {exc}")
        return []


def get_market(market_id: str) -> Market | None:
    """Get a specific market by ID."""
    try:
        resp = httpx.get(
            f"{GAMMA_API}/markets/{market_id}",
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return _parse_market(resp.json())
    except Exception as exc:
        log.warning(f"Polymarket get failed: {exc}")
        return None


def search_events(
    query: str = "",
    active: bool = True,
    closed: bool = False,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> list[Event]:
    """Search Polymarket events via Gamma API."""
    params: dict[str, Any] = {
        "_limit": min(limit, 100),
        "_offset": offset,
        "active": str(active).lower(),
        "closed": str(closed).lower(),
        "order": "volume",
        "ascending": "false",
    }
    if query:
        params["_q"] = query
    try:
        resp = httpx.get(
            f"{GAMMA_API}/events",
            params=params,
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return [_parse_event(e) for e in resp.json()]
    except Exception as exc:
        log.warning(f"Polymarket events search failed: {exc}")
        return []


def get_event(event_id: str) -> Event | None:
    """Get a specific event by ID."""
    try:
        resp = httpx.get(
            f"{GAMMA_API}/events/{event_id}",
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return _parse_event(resp.json())
    except Exception as exc:
        log.warning(f"Polymarket event get failed: {exc}")
        return None


def top_markets(limit: int = 10) -> list[Market]:
    """Get highest-volume active markets."""
    return search_markets(active=True, closed=False, limit=limit)


def format_markets(markets: list[Market]) -> str:
    """Format a list of markets for display."""
    if not markets:
        return "No markets found."
    return "\n\n".join(m.summary() for m in markets)


def format_events(events: list[Event]) -> str:
    """Format a list of events for display."""
    if not events:
        return "No events found."
    return "\n\n".join(e.summary() for e in events)
