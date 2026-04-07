"""Standalone MCP server for Polymarket prediction markets.

Run directly:
    python -m jeff.sense.market_server

Or register in ~/.jeff/mcp_servers.json:
    {
        "servers": {
            "polymarket": {
                "transport": "stdio",
                "command": "python",
                "args": ["-m", "jeff.sense.market_server"]
            }
        }
    }

Then other agents (including Jeff) discover it via `jeff mcp list`
and call tools through nerve's remote dispatch: `polymarket/search`.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from jeff.sense.market import (
    format_events,
    format_markets,
    get_event,
    get_market,
    search_events,
    search_markets,
    top_markets,
)

app = FastMCP("Polymarket", log_level="WARNING")


@app.tool(name="search", structured_output=True)
def search(
    query: str = "",
    limit: int = 10,
    active: bool = True,
    closed: bool = False,
) -> dict[str, str | int | bool]:
    """Search Polymarket prediction markets by keyword."""
    markets = search_markets(query=query, active=active, closed=closed, limit=limit)
    return {
        "tool": "search",
        "success": True,
        "output": format_markets(markets),
        "error": "",
        "exit_code": 0,
        "count": len(markets),
    }


@app.tool(name="odds", structured_output=True)
def odds(market_id: str) -> dict[str, str | int | bool | float]:
    """Get current odds for a specific Polymarket market."""
    market = get_market(market_id)
    if not market:
        return {
            "tool": "odds",
            "success": False,
            "output": "",
            "error": f"Market {market_id} not found",
            "exit_code": 1,
        }
    return {
        "tool": "odds",
        "success": True,
        "output": market.summary(),
        "error": "",
        "exit_code": 0,
        "question": market.question,
        "yes": round(market.outcome_yes, 4),
        "no": round(market.outcome_no, 4),
        "volume": market.volume,
        "active": market.active,
    }


@app.tool(name="event", structured_output=True)
def event(event_id: str) -> dict[str, str | int | bool | float]:
    """Get a Polymarket event and all its sub-markets."""
    ev = get_event(event_id)
    if not ev:
        return {
            "tool": "event",
            "success": False,
            "output": "",
            "error": f"Event {event_id} not found",
            "exit_code": 1,
        }
    return {
        "tool": "event",
        "success": True,
        "output": ev.summary(),
        "error": "",
        "exit_code": 0,
        "title": ev.title,
        "market_count": len(ev.markets),
        "volume": ev.volume,
    }


@app.tool(name="top", structured_output=True)
def top(limit: int = 10) -> dict[str, str | int | bool]:
    """Get highest-volume active markets."""
    markets = top_markets(limit=limit)
    return {
        "tool": "top",
        "success": True,
        "output": format_markets(markets),
        "error": "",
        "exit_code": 0,
        "count": len(markets),
    }


@app.tool(name="events", structured_output=True)
def events_search(
    query: str = "",
    limit: int = 10,
    active: bool = True,
    closed: bool = False,
) -> dict[str, str | int | bool]:
    """Search Polymarket events (multi-market groups)."""
    evts = search_events(query=query, active=active, closed=closed, limit=limit)
    return {
        "tool": "events",
        "success": True,
        "output": format_events(evts),
        "error": "",
        "exit_code": 0,
        "count": len(evts),
    }


if __name__ == "__main__":
    app.run()
