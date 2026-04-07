# MCP

Jeff is MCP-native in two directions:

- `jeff/nerve` is the MCP client surface.
- `jeff/bell` is the MCP server surface.

Phase 3.5 lands these in two halves so the tool seam gets proven before Jeff exposes itself outward.

## Half 1: Nerve as Client

`jeff/nerve` now wraps Jeff's built-in tools as local `FastMCP` tools. Existing code still calls `dispatch()` and gets the same `ToolResult`, but the tools now also have MCP schemas and can be listed through the client surface.

Local tools:

- `bash`
- `read`
- `write`
- `edit`
- `grep`
- `glob`
- `git`
- `tree`

The local server name is `local`. `jeff mcp list` shows these even if no external servers are configured.

## External Servers

Jeff reads external MCP server config from `~/.jeff/mcp_servers.json`.

Missing file means "no external servers" and is not an error.

Supported config forms:

```json
{
  "servers": {
    "filesystem": {
      "transport": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."]
    }
  }
}
```

```json
[
  {
    "name": "notes",
    "transport": "http",
    "url": "http://127.0.0.1:7331/mcp"
  }
]
```

Supported transports:

- `stdio`
- `http` / `streamable-http`

Remote tools can be addressed through `dispatch()` with `server/tool` or `server:tool`.

## CLI

```text
jeff mcp list
jeff serve
jeff serve --transport http --port 7331
```

Shows:

- local MCP-backed tools
- configured external MCP servers
- connection errors per server, if any

`jeff serve` starts Bell as an MCP server:

- `stdio` is the default transport for local agent-to-agent use
- `http` starts Bell on streamable HTTP over TCP

## Half 2: Bell as Server

`jeff/bell` exposes Jeff to other MCP clients.

Bell tools:

- `jeff_status`
- `jeff_ask`
- `jeff_run`
- `jeff_audit`

The first round keeps Bell thin on purpose:

- `jeff_status` is in-process and returns structured workspace state
- `jeff_ask`, `jeff_run`, and `jeff_audit` wrap Jeff's existing CLI so the server surface stays consistent with the shipped behavior

The 7331 relay concept becomes Bell's network transport:

- default: local stdio
- opt-in: streamable HTTP on `127.0.0.1:7331`

## Design Constraint

The MCP SDK is async-native. Jeff's CLI and runtime surfaces are mostly sync. The bridge stays inside `jeff/nerve`: local and remote MCP calls are awaited there and normalized back into the existing sync `ToolResult` shape so async does not leak upward into the rest of Jeff.
