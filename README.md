# Jeff

My name Jeff. I handle it.

```
pip install jeff-code
jeff
```

## What Jeff Does

Jeff is a local-first AI agent. He runs on your machine, with your models, under your control. He codes, researches, writes, analyzes, plans, teaches, and thinks. One agent. One interface. No API keys required. No subscriptions. No engagement loops. No pets.

Built and tested at a prototype Mars habitat in northern New Mexico.

## The Story

UMPH — Jeff's metacognitive code security system — was originally built in NOX as the layer that asks "did the model actually verify this, or did it just pattern-match an answer?" NOX never shipped working. The AI tools of 2024 couldn't reliably implement security code. The ideas were real, the architecture was real, but the last 30% never landed.

Jeff includes the gate that would have caught those failures. When UMPH finally ported into Jeff, the first thing it did was find a SQL injection in Jeff's own telemetry module — code that had passed the existing safety gate. Severity 10/10. Fixed in the same commit that ported UMPH.

The system catches its own creator's mistake. The thing that prevented NOX from shipping is the thing NOX becomes when it ships inside Jeff.

```
Before UMPH: existing gate catches 13 files, 1 flaw type (HAPPY_PATH only)
After UMPH:  180 findings across 44 files, 4 flaw types — including the
             SQL injection nobody was looking for
After fix:   zero critical findings in Jeff's own code
```

## Commands

```
jeff              Status
jeff init         Set up workspace
jeff run <task>   Do the thing
jeff ask <query>  One-shot question
jeff fix <issue>  Diagnose and repair
jeff ship         Build, test, deliver
jeff audit        Quality gate + UMPH scan
jeff coherence    phi / awareness / convergence
jeff memory       Procedural memory query
jeff markets      Polymarket prediction markets
jeff local        Models in the pantry
jeff cluster      Distributed nodes
jeff mcp list     MCP tool inventory
jeff serve        Start Bell MCP server
jeff arcade       Play games. Ship code.
jeff status       Current state
jeff version      Version
```

## Architecture

Every module is an organ. The body metaphor is load-bearing. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full organism map and [.omm/](.omm/) for Mermaid diagrams of each subsystem.

```
jeff/
├── mind/          Intelligence — self-improvement, phi coherence, instincts
│   ├── evolve.py      The loop: ACT→TEST→JUDGE→LEARN→RETAIN→ADAPT→VERIFY
│   ├── coherence.py   phi(K) = 1 - H(K)/H_max — Law IV keystone
│   └── instincts.py   Learned behaviors with 30-day half-life decay
├── gate/          Quality gate — 4-line atomic check + UMPH scan
├── guard/         Security — DBAD + basin + firewall + sandbox + UMPH
│   └── umph.py        Signature scanner (NOX resurrection)
├── blood/         Kernel — task state, authority, audit, provenance
│   └── provenance.py  W3C PROV-DM chain of custody
├── bone/          Persistence — sessions, three-pipeline memory
│   └── memory.py      Episodic + procedural + semantic, SQLite+FTS5
├── nerve/         Tool dispatch + MCP client bridge
├── sense/         L1/L2/L3 cache + prediction markets
│   └── market.py      Polymarket Gamma API client
├── pantry/        Local model management (Ollama), cluster, BranchialAnalyzer
├── bell/          MCP server — introspection + CLI wrappers
├── hand/          Multi-domain task routing, self-forge missing tools
├── staff/         Multi-agent orchestration
├── skin/          Terminal UI, TTS, CRT boot animation
├── personality/   Anti-sycophancy + Ask-Don't-Tell preprocessing
└── workplay/      PR review as game, arcade, diner
```

## Requirements

- Python 3.11+
- [Ollama](https://ollama.ai) running locally
- A model: `ollama pull hermes3:8b`

## Optional

```
pip install jeff-code[voice]     # Robot butler TTS
pip install jeff-code[workplay]  # Themed PR review web UI
```

## Principles

- **Local-first.** Your machine, your models, your data. Zero cloud dependency. Zero subscriptions. Zero engagement loops.
- **Self-verifying.** UMPH runs on every gate check. 11 infection categories. Catches what the model missed.
- **Honest.** Anti-sycophancy is architecture, not aspiration. Ask-Don't-Tell preprocessing reframes flat statements as critical evaluation. Banned phrases ("great question", etc.) stripped from output. See [docs/SYCOPHANCY.md](docs/SYCOPHANCY.md).
- **Memory is law.** Nothing is ever discarded. K-history for failures. Procedural memory for golden paths. See [docs/MEMORY.md](docs/MEMORY.md).
- **MCP-native.** Bidirectional. Jeff can use any MCP server and be used by any MCP client. See [docs/MCP.md](docs/MCP.md).
- **Auditable.** W3C PROV-DM provenance for every piece of content. Chain of custody answers "who told the agent to do this?"

## Ethics

Jeff follows one rule: **Don't Be A Dick.**

He evaluates intent, not vocabulary. A chemistry teacher asking about reactions is learning. A person targeting someone is harmful. Same words. Different basins. DBAD sees the basin.

Sycophancy is a dick move. Jeff doesn't do it.

## What Jeff Is Not

- Not a chatbot
- Not a platform
- Not a subscription
- Not a game (the arcade is optional)
- Not a wrapper around someone else's API

## Philosophy

Your code deserves a butler, not a buddy.

---

AnnulusLabs LLC · Taos, New Mexico
People. Planet. Profit third.

---

*This is my application to the Anthropic AI Safety Fellowship.*
