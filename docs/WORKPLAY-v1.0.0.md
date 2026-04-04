# VEIL WorkPlay v1.0.0
# The game IS the work.
# AnnulusLabs LLC · April 2026

---

## Executive Summary

**Problem:** AI agent armies are deployed everywhere. The bottleneck
is human review. 67% of remote workers report burnout. Review queues
kill productivity. The humans are burning out. The AI is waiting.

**Solution:** VEIL WorkPlay frames human-in-the-loop tasks inside
game-styled interfaces the employee already knows. Same decisions,
same artifacts, same audit trail. One toggle between game view and
work view. Instant. Private. Auditable.

**MVP:** PR code review with themed overlay. Local web app. No game
installation required. ~1,000 lines on existing Jeff stack.

**Pilot:** 20 engineers, 2 weeks, A/B tested. Targets: 25-40% faster
reviews, error rate no increase (target -18%), decision parity >95%.

**Compliance:** View-agnostic audit log. SOC 2 Type II compatible.
Data never leaves the local machine. Data never enters the game.

**Price:** Free personal. $15/user/month team. $40/user/month enterprise.

**Ask:** One pilot. 20 engineers. 2 weeks. Measurable outcomes.
The pilot report becomes the sales deck.

---

## 1. The Problem

Every enterprise is deploying AI agent armies. The bottleneck is
human-in-the-loop: someone must review, approve, direct, decide.

Nobody wants to sit in Jira reviewing 50 AI-generated PRs all day.
Nobody wants to triage 200 support tickets in a dashboard.
Nobody wants to audit compliance reports in a spreadsheet.

The review queue is where productivity goes to die.

## 2. The Insight

The work isn't boring. The INTERFACE is boring.

The cognitive task of reviewing code is identical to inspecting
equipment in a game. Triaging bugs IS tower defense. Approving
decisions IS diplomacy. Routing tasks IS logistics management.

Games solved the engagement problem decades ago.
Enterprise software never learned.

## 3. The Product

VEIL WorkPlay translates real work tasks into missions inside games
the employee already plays. Not gamification (fake badges). Not
serious games (forced fun). Real games. Real work. Same decisions.

### 3.1 The Toggle

    [GAME VIEW]  ←→  [WORK VIEW]

    - Instant switch (< 100ms)
    - Employee chooses which view to use
    - View preference is private — never reported to manager
    - Audit log identical in both views
    - Employee can lock to WORK VIEW anytime (opt-out respected)
    - Keyboard shortcut, configurable

### 3.2 The Decision Surface

    The game view does NOT replace the work artifact.
    The game view FRAMES the work artifact.

    GAME VIEW:
    ┌─────────────────────────────────────────────┐
    │  QUEST: Inspect the Gate Mechanism           │
    │                                              │
    │  The castle blacksmith presents new work.    │
    │  Examine for weak points.                    │
    │                                              │
    │  [View Blueprint]  ← opens the actual diff   │
    │  [Inspect Joints]  ← highlights edge cases   │
    │  [Test Under Load] ← runs the test suite     │
    │                                              │
    │  Verdict: [Approve] [Send Back] [Reject]     │
    └─────────────────────────────────────────────┘

    WORK VIEW (same task, same moment):
    ┌─────────────────────────────────────────────┐
    │  PR #4521: Auth module refactor              │
    │                                              │
    │  Author: bot/jeff-coder-a19af6da             │
    │  Files changed: 3  Lines: +47 / -23          │
    │                                              │
    │  [View Diff]                                 │
    │  [Show Edge Cases] (3 identified by gate)    │
    │  [Run Tests]                                 │
    │                                              │
    │  Decision: [Approve] [Request Changes] [Reject]│
    └─────────────────────────────────────────────┘

    "View Blueprint" opens the ACTUAL diff. "Inspect Joints" shows
    REAL edge cases. "Test Under Load" runs the REAL test suite.
    The game adds narrative context, not abstraction.
    The human sees the real artifact. Always.

### 3.3 Fidelity Tiers

    Not all tasks map equally well to games.

    TIER 1 — FULL TRANSLATION (80% of review tasks)
      Binary or categorical decisions with clear criteria.
      Approve/reject, triage by severity, route to team.
      Game: full narrative wrapper, high immersion.
      Example: bug triage → tower defense unit allocation

    TIER 2 — FRAMED TRANSLATION (15% of review tasks)
      Decisions requiring artifact inspection.
      Code review, document review, design review.
      Game: narrative frame + real artifact embedded.
      Example: PR review → "inspect the mechanism" + real diff

    TIER 3 — PASSTHROUGH (5% of review tasks)
      Deeply technical tasks with no clean game analogue.
      Complex refactoring, architecture decisions, legal review.
      Game: minimal chrome, mostly work view.
      Example: "The council requests your expertise" + raw task
      Toggle defaults to WORK VIEW for Tier 3.

    The system NEVER forces a bad translation.
    If it can't map cleanly, it passes through honestly.
    That builds trust. Trust is the only currency that matters.

### 3.4 Artifact Styling (Cognitive Continuity)

    When "View Blueprint" opens the diff, the viewer is styled
    to match the game's aesthetic — continuous immersion:

    Medieval RPG:   Parchment background, serif mono, gold/red diff
    Sci-fi:         Terminal green-on-black, scan lines, cyan/amber
    Pastoral:       Warm cream, earth tones, green/brown
    Minimal:        Standard diff with subtle game chrome

    Content is identical. Syntax highlighting preserved.
    Functionality preserved (copy, search, collapse).
    Only colors, fonts, and chrome change. Never the content.
    "Work-accurate mode" always one keystroke away.

### 3.5 Narrative Fatigue Engine

    Day 1: "The castle blacksmith presents new work." → engaging
    Day 14: "Oh look, another gate..." → noise

    Solution: auto-rotation based on usage.

    FULL NARRATIVE   First 3 encounters, then 20% of the time.
    BRIEF            "Gate inspection. 3 weak points found." 50%.
    SILENT           Game-styled chrome only. No text. 30%.
    HUMOR (opt-in)   "The blacksmith sighs. Another gate.
                      He wonders if the architect is okay."

    User controls: jeff workplay narrative full|brief|silent|auto|humor
    System tracks exposure per template per user.
    After 10 uses, auto-mode shifts to 70% brief/silent.
    The narrative earns its presence.

## 4. Architecture

### 4.1 System Overview

    ┌─────────────────────────────────────────────┐
    │  ENTERPRISE TOOLS (GitHub, Jira, ServiceNow) │
    └──────────────┬──────────────────────────────┘
                   │ webhooks / API
                   ▼
    ┌─────────────────────────────────────────────┐
    │  JEFF AGENT ARMY                             │
    │  Does the work. Produces artifacts.           │
    │  Requests human decisions.                    │
    └──────────────┬──────────────────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────────────────┐
    │  KERF TRANSLATION ENGINE                     │
    │  1. Basin classify the task                   │
    │  2. Score fidelity tier                       │
    │  3. Select game template                      │
    │  4. Generate narrative frame                  │
    │  5. Embed real artifact                       │
    │  6. Attach kerf_explain (transparency)        │
    │  7. Set difficulty / reward calibration        │
    └──────────┬───────────────┬──────────────────┘
               │               │
    ┌──────────▼──┐    ┌───────▼───────┐
    │  GAME VIEW   │    │  WORK VIEW    │
    │  (themed     │◄──►│  (standard    │
    │   overlay)   │    │   dashboard)  │
    └──────────────┘    └───────────────┘
               │               │
               └───────┬───────┘
                       ▼
              [HUMAN DECISION]
              approve / reject / modify / escalate
                       │
                       ▼
              [AUDIT LOG — view-agnostic]
                       │
                       ▼
              [JEFF EXECUTES DECISION]

### 4.2 Task Translation Schema

    {
      "task_id": "PR-4521",
      "source": "github",
      "work_type": "code_review",
      "kerf_basin": "quality_inspection",
      "fidelity_tier": 2,
      "artifacts": [
        {"type": "diff", "url": "github.com/...", "embed": true}
      ],
      "game_mapping": {
        "template": "medieval_inspection",
        "title": "Inspect the Gate Mechanism",
        "narrative": "The castle blacksmith presents new work.",
        "npc": "blacksmith",
        "actions": {
          "view_artifact": {"label": "View Blueprint", "opens": "diff"},
          "run_analysis": {"label": "Test Under Load", "runs": "pytest"},
          "highlight_issues": {"label": "Inspect Joints", "shows": "edge_cases"}
        },
        "decisions": ["approve", "send_back", "reject"],
        "difficulty": 1.3,
        "reward": {"type": "guild_renown", "amount": 15}
      },
      "kerf_explain": {
        "basin": "quality_inspection",
        "confidence": 0.87,
        "features": {
          "has_diff": true,
          "file_count": 3,
          "test_coverage_delta": -0.02,
          "error_handling_present": false
        },
        "alternatives": [
          {"basin": "investigation", "confidence": 0.41},
          {"basin": "construction", "confidence": 0.23}
        ],
        "reason": "Binary decision on artifact with inspectable flaws."
      },
      "work_mapping": {
        "title": "PR #4521: Auth module refactor",
        "actions": ["view_diff", "show_edge_cases", "run_tests"],
        "decisions": ["approve", "request_changes", "reject"]
      },
      "audit": {
        "presented_at": null,
        "decided_at": null,
        "decision": null,
        "view_mode": null,
        "reviewer": null,
        "time_on_task_ms": null
      }
    }

    Templates are open source. The engine is the product.

### 4.3 KERF Basin Classification

    BASIN                WORK EXAMPLES            GAME ANALOGUES
    ──────────────────   ────────────────────     ────────────────────
    binary_decision      approve/reject PR        accept/reject quest
    severity_triage      bug prioritization       tower defense waves
    resource_allocation  team/budget assignment   unit deployment
    quality_inspection   code review, QA          equipment inspection
    negotiation          vendor, contract         trade, diplomacy
    logistics            routing, scheduling      supply chain, caravan
    investigation        root cause, forensics    detective, mystery
    construction         architecture, design     building, crafting
    defense              security, compliance     fortification, patrol
    exploration          research, discovery      scouting, mapping

    Unmappable tasks → Tier 3 passthrough. Honest about limits.

    Every classification includes kerf_explain: confidence,
    features used, alternatives considered, plain-English reason.
    KERF is inspectable, not mystical. Anyone can ask "why?"

### 4.4 "Request Changes" Flow

    When the reviewer selects "Send Back" in game view:
    - The blacksmith takes the blueprint back
    - A comment field appears (real text, themed chrome)
    - Comments are stored as standard GitHub review comments
    - The NPC presents redlines in game language
    - The actual comment text is preserved verbatim
    - Frame the interaction. Never rewrite the content.

## 5. Security Architecture

    PRINCIPLE: Data never enters the game.

    ┌─────────────────────────────────────────┐
    │  GAME PROCESS (untouched, sandboxed)     │
    │  No work data. No enterprise access.     │
    │  Standard game. Unmodified.              │
    ├─────────────────────────────────────────┤
    │  VEIL OVERLAY (secure, isolated process)  │
    │  Renders themed work UI ABOVE the game.  │
    │  All work data in VEIL's memory only.     │
    │  Encrypted at rest. Cleared on close.     │
    ├─────────────────────────────────────────┤
    │  JEFF (local agent, user's machine)       │
    │  Fetches tasks via existing VPN/SSO.      │
    │  Submits decisions back via same auth.    │
    └─────────────────────────────────────────┘

    EDR sees: Jeff (approved agent) + game (standard executable).
    DLP sees: work data in Jeff's secure process. Never in game.
    SOC 2 scope: Jeff + VEIL overlay. Game excluded from scope.
    Data residency: everything local. Nothing leaves the machine.

## 6. IP and Licensing

    Phase 1 (overlay): No game modification. Screen overlay only.
    Same category as Discord overlay or Steam overlay.
    Marketing says "your favorite RPG." Never specific titles.
    Screenshots use Jeff's Arcade (original, owned).

    Phase 2 (deep mods): Community-created under each game's
    modding license. AnnulusLabs distributes nothing.

    Phase 3 (emulator): RetroArch (GPL) + user's own ROMs.

    WorkPlay ships with JEFF'S ARCADE — original games, zero IP risk.

## 7. Employee Psychology

    1. OPT-IN ONLY. Never mandatory. Employee enables it.
    2. EMPLOYEE CHOOSES GAME. Not employer. Not IT.
    3. VIEW IS PRIVATE. Manager never sees which view was active.
    4. OPT-OUT ANYTIME. One toggle. No penalty.
    5. SEPARATE SAVES. Personal game saves are sacred.
    6. NO FORCED FUN. Tier 3 passes through honestly.
    7. NO SHAMING. Leaderboards show tasks completed, opt-in only.

    Optional "time blur" for privacy-focused enterprises:
    Log only task completion within SLA (yes/no), not exact seconds.
    Prevents manager inference of view preference.

    The goal: make the review queue feel less like punishment.
    Not: make your escape game feel like work.

## 8. Telemetry (Pilot Measurement)

    Per-decision schema:

    {
      "task_id": "PR-4521",
      "reviewer": "swhelchel",
      "view_mode": "game",              // private, never reported
      "presented_at": "2026-06-15T14:30:22Z",
      "decided_at": "2026-06-15T14:32:15Z",
      "time_on_task_ms": 113000,
      "decision": "approved",
      "artifact_opens": 2,
      "analysis_runs": 1,
      "issue_highlights": 3,
      "fidelity_tier": 2,
      "template_used": "medieval_inspection",
      "kerf_confidence": 0.87,
      "decision_reversed_within_7d": false,
      "post_merge_signals": {
        "ci_failures": 0,
        "bug_reports_linked": 0,
        "hotfix_within_14d": false
      },
      "voluntary_session": true,
      "returned_without_prompt": true
    }

    PRIMARY METRIC: time-to-correct-decision
    Not speed alone. Not engagement. Not vibes.
    Accuracy-adjusted throughput. The metric a VP Eng will defend.

    DIAGNOSTIC METRICS:
    - artifact_inspection_depth
    - decision_durability (reversal + post-merge signals)
    - voluntary_engagement_rate
    - returned_without_prompt (addiction-level signal, ethically)

## 9. Pilot Plan

    20 engineers. 2 weeks. One team. Measurable.

    WEEK 1 — Setup
    - Install Jeff + WorkPlay on volunteer machines
    - Connect to team's GitHub via webhooks
    - Configure 3 templates (Medieval, Sci-fi, Minimal)
    - Baseline: current review throughput, error rate, satisfaction

    WEEK 2 — A/B Test
    - Group A (10): WorkPlay enabled, themed review mode available
    - Group B (10): Standard tooling, no WorkPlay
    - Measure all telemetry metrics above

    SUCCESS CRITERIA:
    - Reviews/day: +25% minimum (target +40%)
    - Time/review: -15% minimum (target -30%)
    - Error rate: no increase (target -18%)
    - Engagement score: +1.0 point (target +2.0)
    - Decision parity: game view = work view at >95%
    - Zero security incidents
    - Voluntary continuation: >60% choose to keep using after pilot

    DELIVERABLE: Pilot report with data. This IS the sales deck.

    Deployment: LOCAL WEB APP served by Jeff. No Steam. No game
    executable. No IT exemption. Runs in the developer's browser.
    Jeff's Arcade RPG is the controlled environment for pilot.

    Post-pilot expansion to DX12/Vulkan overlay for real games.

## 10. Pricing

    WorkPlay Personal     Free forever
      Jeff's Arcade, self-hosted, community templates

    WorkPlay Team         $15/user/month
      Enterprise tool integration, KERF auto-classification,
      10 pre-built templates, team dashboards (opt-in)

    WorkPlay Enterprise   $40/user/month
      SOC 2 Type II toolkit, SSO/SAML, custom template builder,
      SIEM-compatible audit export, decision parity analytics,
      data residency controls, priority support

    WorkPlay Custom       Contact
      Industry-specific game mods, on-premise, dedicated engineer

    WHO SIGNS THE PO:
    Buyer: VP Engineering or CIO
    Pitch: "Faster review velocity, reduced burnout turnover,
            full audit compliance, zero added security surface."
    NOT: "Let them play Skyrim."
    Metrics sell it. Toggle proves it. Pilot proves the metrics.

## 11. Roadmap

    Q2 2026    Jeff's Arcade ships (free tier, proves the concept)
    Q3 2026    WorkPlay MVP (themed PR review, local web app)
    Q3 2026    First pilot (1-3 engineering teams)
    Q4 2026    WorkPlay Team tier launch
    Q1 2027    WorkPlay Enterprise tier launch
    Q2 2027    Phase 2: community game mods
    Q4 2027    Phase 3: emulator bridge
    2028       Industry verticals + custom deployments

## 12. MVP Build Scope

    ~1,000 lines on existing Jeff stack.

    ┌─────────────────────────────────────────────┐
    │  1. GitHub webhook receiver       ~150 lines │
    │  2. KERF basin classifier         ~200 lines │
    │  3. Template renderer + theming   ~250 lines │
    │  4. Decision capture + audit      ~150 lines │
    │  5. Toggle mechanism              ~100 lines │
    │  6. Pilot telemetry + export      ~150 lines │
    │                          TOTAL  ~1,000 lines │
    └─────────────────────────────────────────────┘

    NOT IN MVP: DX12/Vulkan overlay, Jira/ServiceNow, tower defense,
    SSO/SAML, custom template editor, voice.

    Prove the loop → prove the toggle → prove the metric.

## 13. Tech Stack (What's Built)

    Jeff v1.0.0      4,284 lines   Agent army + full organism
    Jeff/staff         277 lines   Agent birth with purpose
    Jeff/gate           72 lines   Quality gate
    Jeff/guard         175 lines   DBAD ethics
    Jeff/sense         283 lines   Context prefetch
    Jeff/hand          242 lines   Multi-domain routing
    Jeff/mind/evolve   346 lines   Self-improvement loop
    Jeff/pantry        856 lines   Models + distributed compute
    Jeff/arcade        598 lines   Original games (free tier)
    VEIL v0.1            —         DX12 hook + overlay (C/Lua)
    KERF compiler    5,944 lines   Basin classification engine

    Remaining for MVP pilot: ~1,000 lines.
    Remaining for Team tier: ~6,000 lines.

## 14. What This Is Not

    Not gamification. No fake badges. No shaming leaderboards.
    Not surveillance. Game view is private. Work output is auditable.
    Not a toy. Decisions are real. The toggle proves it.
    Not replacing games. Framing work inside them.
    Not dystopia. Opt-in. Opt-out. Always. No penalty.
    Not abstraction. The artifact is real. The frame is themed.
    Not mandatory fun. Tier 3 admits when it can't map.

## 15. Buyer-Safe Positioning

    "VEIL WorkPlay is a secure decision-layer interface that
    increases human review throughput by presenting enterprise
    tasks in a familiar themed format, while preserving the
    underlying artifact, decision, and audit trail."

---

## Appendix A: Validation

    This spec survived 3 rounds of adversarial review across 7
    independent AI models (GPT, DeepSeek, Grok, Gemini, Perplexity,
    Google, Claude) with zero unresolved conceptual risks. All
    remaining risks are execution-level and addressed in the
    pilot plan.

## Appendix B: The Law III Connection

    For the manifesto. Not the sales deck.

    The game IS a meaning field.

    You don't force the employee to review code.
    You emit a field configuration (the game) that curves their
    trajectory toward the same attractor (the correct decision).

    Communication succeeds when the emitted field is strong enough
    to curve the receiver's path. Games are the strongest meaning
    field humans have ever built.

    This is Law III of Emergent Reality applied to enterprise
    productivity.

    The employee doesn't navigate to the right answer.
    They resonate with it.

---

AnnulusLabs LLC · Taos, New Mexico · April 2026
People. Planet. Profit third.

The game is the work. The toggle proves it.
