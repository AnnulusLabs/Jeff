# Polymarket

Jeff reads prediction markets to inform decisions.

## What

Polymarket is a public prediction market. Prices are implied probabilities (0-1) denominated in USDC on Polygon. No API key needed — the Gamma API is public.

## Architecture

Polymarket is a **separate MCP server**, not embedded in Bell. This follows the Phase 3.5 loose coupling principle: external data sources are MCP servers that Jeff discovers through config, not tools bolted onto Bell.

```
jeff/sense/market.py         — client library (httpx, data parsing)
jeff/sense/market_server.py  — standalone FastMCP server wrapping the library
~/.jeff/mcp_servers.json     — config entry registering the server
```

Bell does not know Polymarket exists. Nerve discovers it through the MCP client surface.

## Setup

Add to `~/.jeff/mcp_servers.json`:

```json
{
  "servers": {
    "polymarket": {
      "transport": "stdio",
      "command": "python",
      "args": ["-m", "jeff.sense.market_server"]
    }
  }
}
```

Then `jeff mcp list` shows polymarket among connected servers.

## MCP Tools (via market_server)

- `polymarket/search(query, limit, active, closed)` — search markets by keyword
- `polymarket/odds(market_id)` — get current prices for one market
- `polymarket/event(event_id)` — get event with all sub-markets
- `polymarket/top(limit)` — highest-volume active markets
- `polymarket/events(query, limit, active, closed)` — search events

## CLI (in-process convenience)

```text
jeff markets                    # top active markets by volume
jeff markets AI                 # search for AI-related markets
jeff markets --closed           # include resolved markets
jeff markets --limit 5 election # top 5 election markets
```

The CLI command calls `market.py` directly (in-process). MCP clients call through the server.

## Key Fields

- `outcomePrices` — implied probabilities, raw signal, not converted
- `volume` — total traded USD, proxy for market confidence
- `endDate` — when the market resolves
- `question` — the event being predicted

## Why

Prediction markets aggregate distributed information into calibrated probabilities. When Jeff needs to reason about uncertain outcomes, market prices are more calibrated than any single model's opinion. Polymarket is a sense organ — another input to the L2 cache.
