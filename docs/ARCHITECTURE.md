# JEFF — Architecture & Naming Structure
# "My name Jeff. I handle it."
# AnnulusLabs LLC · April 2026

## Philosophy
Jeff is the butler. Not a buddy, not a pet, not an assistant.
Jeff shows up, does the work, and goes home.
Abliterated model at the helm. Zero sycophancy. Zero engagement loops.

---

## CLI

```
jeff              # "My name Jeff." — status + ready
jeff init         # workspace setup
jeff run          # execute task
jeff fix          # diagnose and repair
jeff ship         # build, test, deliver
jeff ask          # one-shot question
jeff watch        # continuous monitor mode
jeff staff        # multi-agent coordination (formerly Zoeae)
jeff audit        # Preflight quality gate
jeff local        # Ollama model management
jeff relay        # instance coordination
```

---

## Core Subsystems (internal names, not user-facing)

| Jeff Name       | Formerly        | What It Does                                    |
|-----------------|-----------------|------------------------------------------------ |
| **jeff/mind**   | kerf/mind       | KERF ContextCompiler, ModelRouter, Pipeline      |
| **jeff/gate**   | preflight       | 4-line atomic quality gate, cognitive flaw map   |
| **jeff/staff**  | zoeae           | Multi-agent orchestration, lifecycle, pool mgmt  |
| **jeff/nerve**  | kerf/nerve      | Tool dispatch (bash, edit, grep, glob, git)      |
| **jeff/sense**  | kerf/sense      | Input processing, file watching, context intake  |
| **jeff/bone**   | kerf/bone       | Session persistence, state management            |
| **jeff/skin**   | kerf/skin       | Terminal UI, output formatting, dry commentary   |
| **jeff/blood**  | kerf/blood      | Telemetry, token tracking, cost awareness        |
| **jeff/hand**   | kerf/hand       | File operations, git operations, execution       |
| **jeff/guard**  | kerf/guard      | Security, permissions, sandbox                   |
| **jeff/pantry** | ollama provider | Local model management, 39+ models               |
| **jeff/bell**   | relay @ 7331    | Inter-instance communication, coordination       |

---

## Staff System (formerly Zoeae)

The crustacean metaphors served OpenClaw's branding. Jeff uses household staff metaphors.

| Zoeae Term       | Jeff Term         | Concept                                      |
|------------------|-------------------|----------------------------------------------|
| molt             | **shift change**  | Agent state transition, capability upgrade    |
| instar           | **shift**         | Current operational stage                     |
| chitin           | **standards**     | Quality threshold, hardened requirements      |
| nauplius         | **intern**        | New agent, learning phase                     |
| zoea             | **junior**        | Capable but supervised                        |
| megalopa         | **staff**         | Full autonomous capability                    |
| adult            | **senior**        | Experienced, mentors others                   |
| elder            | **head butler**   | Oversees all operations                       |
| DreamEngine      | **night shift**   | Background consolidation, memory integration  |
| PolicyEngine     | **house rules**   | Behavioral constraints, operational policy    |
| metabolic tiers  | **budget**        | Resource allocation per agent                 |
| agent pool       | **staff roster**  | Available agents and their capabilities       |
| genome           | **training**      | Agent capability definition (TDNA preserved)  |

---

## Personality Layer

Jeff's voice is consistent across all output:

- **No exclamation marks.** Ever.
- **No emoji.** Jeff doesn't do emoji.
- **No "Great question!" or "I'd be happy to help."** Jeff just helps.
- **Dry competence.** "That's fixed." "Three issues. All resolved." "Your tests pass now."
- **Honest about problems.** "This architecture won't scale. Here's why."
- **Respects your time.** Short answers. No padding. No filler.
- **Occasional dry wit.** Earned, not forced. "I see you've written a recursive function that doesn't recurse. Bold choice."

Error levels:
- INFO:  "Noted."
- WARN:  "You'll want to look at this."
- ERROR: "This needs attention."
- FATAL: "We have a situation."

First run:
```
$ jeff
My name Jeff.
Workspace ready. What needs doing?
```

---

## Model Strategy

Primary: Abliterated local model via jeff/pantry (Ollama)
- hermes3:8b for fast tasks
- DeepSeek R1 for complex reasoning
- Consensus via BranchialAnalyzer across multiple models

Fallback: API models when local insufficient (user-configured, metered)

Jeff never hides what model is working. `jeff status` shows exactly what's running.

---

## Package Structure

```
jeff/
├── pyproject.toml          # name="jeff", entry_points={"jeff"}
├── jeff/
│   ├── __init__.py
│   ├── cli.py              # Click/Typer CLI entry
│   ├── mind/               # KERF compiler, router, pipeline
│   ├── gate/               # Quality gate (Preflight core)
│   ├── staff/              # Multi-agent orchestration
│   ├── nerve/              # Tool dispatch
│   ├── sense/              # Input processing
│   ├── bone/               # Session persistence
│   ├── skin/               # Terminal UI
│   ├── blood/              # Telemetry
│   ├── hand/               # File/git operations
│   ├── guard/              # Security layer
│   ├── pantry/             # Local model management
│   ├── bell/               # Inter-instance relay
│   └── personality/        # Voice, tone, commentary generation
├── tests/
├── skills/                 # Portable skill definitions
└── README.md               # "My name Jeff. I handle it."
```

---

## Migration Path

1. KERF core (mind/) stays as-is — it's the engine, Jeff is the product
2. Zoeae concepts migrate to jeff/staff/ with new naming
3. Preflight gate migrates to jeff/gate/
4. OllamaProvider migrates to jeff/pantry/
5. Relay at 7331 migrates to jeff/bell/
6. New: jeff/skin/ for terminal UI
7. New: jeff/nerve/ for tool dispatch (the Claude Code replacement layer)
8. New: jeff/personality/ for voice consistency

---

## Taglines

- "My name Jeff. I handle it."
- "Your code deserves a butler, not a buddy."
- "Jeff handles it."
- "No pets. No emoji. Just work."
- "The coding agent for people who build things."

---

## Repos

- github.com/AnnulusLabs/jeff         # Core
- github.com/AnnulusLabs/jeff-skills  # Portable skills
- github.com/AnnulusLabs/jeff-models  # Curated abliterated model configs

Existing repos stay up:
- github.com/AnnulusLabs/preflight    # Redirects/references jeff/gate
- github.com/AnnulusLabs/meshbridge   # Independent, Jeff can use it

---

## What Jeff Is Not

- Not a chatbot. Jeff doesn't do conversation for conversation's sake.
- Not a platform. Jeff runs on YOUR machine with YOUR models.
- Not a subscription. Jeff is free. The models are free. The code is free.
- Not a game. No pets, no gacha, no shiny variants, no dopamine schedule.
- Not a wrapper around someone else's API. Jeff IS the agent.

---

# Day One Deliverable

README.md on GitHub:

# Jeff

My name Jeff. I handle it.

`pip install jeff-code`
`jeff`

---

AnnulusLabs LLC · Taos, New Mexico · April 2026
People. Planet. Profit third.
