# JEFF

My name Jeff. I handle it.

## Philosophy

Jeff is the butler.
Not a buddy, not a pet, not an assistant.
Jeff shows up, does the work, and goes home.

Principles:

- Local-first models, tools, and memory.
- Zero sycophancy.
- Short answers, clear ownership, real verification.
- The game can frame the work, but never replace the artifact.

## CLI

```text
jeff              # status + ready
jeff init         # workspace setup
jeff run          # execute a task
jeff ask          # one-shot question
jeff fix          # diagnose and repair
jeff ship         # build, test, deliver
jeff audit        # quality gate check
jeff local        # pantry inventory
jeff cluster      # distributed inference status
jeff workplay     # themed PR review
jeff arcade       # work-bound arcade surfaces
jeff diner        # work-bound diner surface
jeff relay        # bell status until MCP relay ships
jeff version      # version
```

## Core Subsystems

| Subsystem | Role |
|---|---|
| `jeff/mind` | Law I and Law IV machinery: evolution, coherence, awareness |
| `jeff/gate` | Four-line quality gate and retained cognitive flaws |
| `jeff/staff` | Multi-agent orchestration |
| `jeff/nerve` | Tool dispatch and MCP client bridge |
| `jeff/sense` | Context intake, L1/L2/L3 memory |
| `jeff/bone` | Session persistence and config |
| `jeff/skin` | Terminal UI |
| `jeff/blood` | Runtime spine: task state, audit, queueing, authority |
| `jeff/hand` | Domain routing and non-code work surfaces |
| `jeff/guard` | DBAD, basin checks, sandboxing, enforcement |
| `jeff/pantry` | Local model management and BranchialAnalyzer |
| `jeff/bell` | MCP server surface and relay seam |
| `jeff/workplay` | PR review plus work-bound arcade and diner surfaces |
| `jeff/personality` | Voice and anti-sycophancy shaping |

## Package Shape

```text
jeff/
├── jeff/
│   ├── cli.py
│   ├── mind/
│   ├── gate/
│   ├── staff/
│   ├── nerve/
│   ├── sense/
│   ├── bone/
│   ├── skin/
│   ├── blood/
│   ├── hand/
│   ├── guard/
│   ├── pantry/
│   ├── bell/
│   ├── workplay/
│   └── personality/
├── docs/
├── tests/
└── README.md
```

## Notes

- `jeff/workplay` is first-class. The web review surface, arcade, and diner all belong there because they frame the same work loop.
- `jeff/blood` stays fused for now on purpose. The runtime loop, audit trail, queueing, and authority policy all mutate one shared task graph. Splitting it before the MCP seam would add boundaries without reducing coupling.
- `jeff/nerve` is the live MCP client seam. Local tools are wrapped as `FastMCP` tools, and external MCP servers are configured through `~/.jeff/mcp_servers.json`.
- `jeff/bell` is the live MCP server seam. `stdio` is the default transport; network access is opt-in via streamable HTTP on port 7331.
