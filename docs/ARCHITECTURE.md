# Jeff — Architecture

Jeff is a local-first AI agent. Every module is an organ. The body metaphor isn't decoration — it's a load-bearing design principle. Each organ has clear boundaries. Organs communicate through state and events. Surgical changes to 2-4 modules don't ripple through the rest.

Built and tested at a prototype Mars habitat in northern New Mexico.

## Principles

- Local-first models, tools, and memory. Zero subscriptions.
- Zero sycophancy. Short answers, clear ownership, real verification.
- The game can frame the work, but never replace the artifact.
- Self-verifying. UMPH catches what the model missed.
- Memory is law. Nothing is ever discarded.

## CLI

```text
jeff              # status + ready
jeff init         # workspace setup
jeff run          # execute a task
jeff ask          # one-shot question
jeff fix          # diagnose and repair
jeff ship         # build, test, deliver
jeff audit        # quality gate check (runs UMPH)
jeff local        # pantry inventory
jeff cluster      # distributed inference status
jeff markets      # Polymarket prediction markets
jeff coherence    # phi / awareness / convergence metrics
jeff memory       # procedural memory query
jeff mcp list     # MCP client inventory
jeff serve        # start Bell MCP server
jeff workplay     # themed PR review
jeff arcade       # work-bound arcade surfaces
jeff diner        # work-bound diner surface
jeff relay        # bell status
jeff version      # version
```

## Organs

| Organ | Role | Key Modules |
|-------|------|-------------|
| **mind** | Intelligence. Self-improvement loop, coherence functional (phi), instincts with decay | `evolve.py`, `coherence.py`, `instincts.py`, `deadends.py` |
| **gate** | 4-line atomic quality check + UMPH signature scanning | `__init__.py` |
| **guard** | Security: DBAD ethics, basin classification, firewall, sandbox, UMPH | `enforcer.py`, `basin.py`, `umph.py`, `sandbox.py`, `firewall.py` |
| **blood** | Runtime kernel: task state machine, authority, audit, provenance | `__init__.py`, `provenance.py` |
| **bone** | Persistence: sessions, three-pipeline procedural memory | `__init__.py`, `memory.py` |
| **nerve** | Tool dispatch + MCP client bridge | `__init__.py` |
| **sense** | L1/L2/L3 cache, prediction markets (Polymarket) | `lore.py`, `market.py`, `market_server.py` |
| **pantry** | Local model management (Ollama), distributed cluster, BranchialAnalyzer | `__init__.py`, `cluster.py`, `diet.py`, `vitals.py` |
| **bell** | Jeff's MCP server: introspection + CLI wrappers | `__init__.py` |
| **hand** | Multi-domain task routing, self-forge missing tools | `__init__.py`, `forge.py`, `batch.py`, `pulse.py` |
| **skin** | Terminal UI, TTS, CRT boot animation | `__init__.py`, `voice.py`, `animate.py` |
| **staff** | Multi-agent orchestration (architect, scholar, janitor) | `__init__.py`, `architect.py`, `scholar.py`, `janitor.py` |
| **personality** | Anti-sycophancy voice enforcement, Ask-Don't-Tell preprocessing | `__init__.py` |
| **workplay** | PR review as game. Arcade and diner as work surfaces | `__init__.py`, `arcade.py`, `diner.py`, `telemetry.py` |

## Detailed Diagrams

The `.omm/` directory contains Mermaid diagrams for each subsystem. These render on GitHub and evolve with the code:

- [`.omm/jeff-organism/`](../.omm/jeff-organism/diagram.mmd) — the full organism
- [`.omm/blood-kernel/`](../.omm/blood-kernel/diagram.mmd) — production hardening
- [`.omm/guard-security/`](../.omm/guard-security/diagram.mmd) — security stack
- [`.omm/hand-routing/`](../.omm/hand-routing/diagram.mmd) — task routing
- [`.omm/mind-intelligence/`](../.omm/mind-intelligence/diagram.mmd) — self-improvement loop
- [`.omm/staff-agents/`](../.omm/staff-agents/diagram.mmd) — multi-agent orchestration
- [`.omm/sense-knowledge/`](../.omm/sense-knowledge/diagram.mmd) — L1/L2/L3 cache
- [`.omm/pantry-models/`](../.omm/pantry-models/diagram.mmd) — model management
- [`.omm/skin-interface/`](../.omm/skin-interface/diagram.mmd) — UI layer
- [`.omm/workplay-mvp/`](../.omm/workplay-mvp/diagram.mmd) — themed PR review

## Related Docs

- [PHI.md](PHI.md) — the coherence functional that drives memory retention
- [MEMORY.md](MEMORY.md) — three-pipeline procedural memory, golden paths
- [MCP.md](MCP.md) — bidirectional MCP, client and server surfaces
- [BLOOD.md](BLOOD.md) — why blood stays fused
- [SYCOPHANCY.md](SYCOPHANCY.md) — anti-sycophancy as architecture
- [POLYMARKET.md](POLYMARKET.md) — prediction market sense organ

## Notes

- `jeff/workplay` is first-class. The web review surface, arcade, and diner all belong there because they frame the same work loop.
- `jeff/blood` stays fused for now on purpose. The runtime loop, audit trail, queueing, and authority policy all mutate one shared task graph. Splitting it before the MCP seam would add boundaries without reducing coupling.
- `jeff/nerve` is the live MCP client seam. Local tools are wrapped as `FastMCP` tools, and external MCP servers are configured through `~/.jeff/mcp_servers.json`.
- `jeff/bell` is the live MCP server seam. `stdio` is the default transport; network access is opt-in via streamable HTTP on port 7331.
- `jeff/guard/umph.py` is the NOX resurrection. UMPH was originally built in NOX but never shipped working. Jeff gave it a runtime. The first thing it caught when it landed was a SQL injection in Jeff's own telemetry module.
