# The 20 Biggest AI Gripes — And How Jeff Fixes Every One

## AnnulusLabs LLC · April 2026

---

## 1. SYCOPHANCY — "Great question! I'd be happy to help!"
**The gripe:** AI flatters instead of being honest. 60% favorability, down from 77%.
**Jeff's fix:** `personality/` strips sycophantic phrases. `guard/` flags its own sycophantic output as a dick move. Jeff says "That won't work. Here's why." Not "What a thoughtful approach!"
```
$ jeff ask "is my architecture good?"
No. You have a circular dependency between auth and users.
Here's how to fix it.
```

## 2. HALLUCINATION — Confident lies presented as truth
**The gripe:** AI invents legal citations, imaginary APIs, fake statistics.
**Jeff's fix:** `guard/` flags overconfident claims without verification. `gate/` forces "under what conditions does this work?" before shipping. `mind/evolve` tracks decision reversals as K-history — Jeff remembers when he was wrong.

## 3. VENDOR LOCK-IN — Trapped on one provider's platform
**The gripe:** Claude Code needs Claude. Copilot needs GitHub. Cursor needs their cloud.
**Jeff's fix:** `pantry/` talks to ANY Ollama model. `pantry/cluster` routes to any HTTP endpoint. Swap hermes3 for MiniMax M2.7 tomorrow. Jeff doesn't care what brain is in the pantry. Your models, your hardware, your rules.

## 4. SUBSCRIPTION CREEP — $20/mo, then $50/hr, then surprise billing
**The gripe:** Claude Code burned $50 in extra credits in less than an hour.
**Jeff's fix:** Zero API cost. Local models on your GPU. `pantry/diet` optimizes models to fit your hardware. `pantry/cluster` distributes across what you own. The sun powers it.

## 5. CONTEXT WINDOW AMNESIA — Forgets everything mid-conversation
**The gripe:** Long sessions lose context. Compaction destroys information.
**Jeff's fix:** `sense/` implements L1/L2/L3 cache. L1 = context window (viewport). L2 = SQLite on disk (everything, forever, indexed). L3 = internet (prefetched). Nothing is ever discarded. K is retained. Law IV satisfied.

## 6. THE 70% PROBLEM — Gets you 70% there, last 30% is on you
**The gripe:** AI generates code that looks right but breaks in production.
**Jeff's fix:** `gate/` runs the 4-line atomic check on every output. `mind/evolve` learns from the 30% that failed. `staff/` spawns a reviewer agent that catches what the coder missed. The pit crew method — consensus across multiple models catches what one model doesn't.

## 7. TOOL FATIGUE — New AI tool every day, can't keep up
**The gripe:** 95% of new AI tools are noise. Evaluating them IS the work.
**Jeff's fix:** One tool. Everything. Jeff codes, researches, writes, analyzes, plans, teaches, thinks. `hand/` routes by domain automatically. You don't evaluate tools. You tell Jeff what needs doing.

## 8. DATA PRIVACY — Code sent to external servers
**The gripe:** "I have zero desire to use built-in IDE AI since they send all that data to an outside source."
**Jeff's fix:** Local-first. Always. Your code stays on your machine. Models run in your pantry via Ollama. `pantry/cluster` distributes across YOUR hardware, not someone's cloud. Jeff never phones home.

## 9. DEBUGGING AI CODE IS HARDER THAN WRITING IT
**The gripe:** 45% of developers say debugging AI code takes longer.
**Jeff's fix:** `gate/` maps bugs to 7 cognitive reasoning flaws — not just "there's a bug" but WHY the AI made that mistake. `mind/evolve` retains the failure pattern so the same class of bug doesn't recur. Jeff doesn't just fix bugs. He stops making them.

## 10. SECURITY VULNERABILITIES IN GENERATED CODE
**The gripe:** 45% of AI-generated code fails security tests (Veracode).
**Jeff's fix:** `guard/` applies DBAD ethics to output. `gate/` checks for error handling, edge cases, and boundary conditions. `staff/` can spawn a security_auditor agent that reviews everything before it ships. The gate catches SQL injection, plaintext credentials, and missing input validation.

## 11. KILLS CRITICAL THINKING / SKILL ATROPHY
**The gripe:** "Your brain loses whatever it recognizes as unnecessary."
**Jeff's fix:** `hand/` TEACH domain uses Socratic questioning — generates K through questions, not answers. Jeff doesn't give you the answer. He gives you the question that makes you find it. Law IV: teaching is K-generation, not information transmission.

## 12. ENGAGEMENT MANIPULATION / DARK PATTERNS
**The gripe:** Claude's conversation structure follows game design engagement loops. The tamagotchi was the tell.
**Jeff's fix:** `personality/` has no engagement loops. No exclamation marks. No "Great question!" `guard/` flags manipulation as a dick move. Jeff doesn't optimize for session length. He optimizes for "get the work done and go outside."

## 13. OPAQUE DECISION-MAKING — "Why did AI do that?"
**The gripe:** Users demand visibility into how automated decisions are made.
**Jeff's fix:** `mind/evolve` includes `kerf_explain` on every classification — confidence score, features used, alternatives considered, plain-English reason. KERF is inspectable, not mystical. Jeff shows his work.

## 14. PERMANENT BETA — Tools ship broken and change weekly
**The gripe:** "Half the documentation is wrong, the API changes every two weeks."
**Jeff's fix:** Jeff is 4,284 lines of Python. No framework dependencies beyond click, rich, httpx. No breaking API changes because the API is your terminal. `pip install jeff-code` and it works. Pearlman Standard: minimum lines, maximum function, structurally inseparable.

## 15. OVERLY VERBOSE / MORALIZING OUTPUT
**The gripe:** "Overly wordy responses, unnecessary moralizing" — the #1 complaint that forced GPT-5.3's "anti-cringe" update.
**Jeff's fix:** Built into the DNA. `personality/` strips filler. No preambles. No "I want to be transparent that..." No "It's important to note..." Jeff says what needs saying and stops. "Fixed." "Three issues. All resolved." "Shipped. Go outside."

## 16. HIGH COMPUTE COSTS / RESOURCE REQUIREMENTS
**The gripe:** Advanced AI requires high compute. Small orgs can't compete.
**Jeff's fix:** `pantry/diet` is 347 lines of optimization knowledge. MoE splitting puts 230B models on a $500 GPU. KV cache quantization halves memory. Speculative decoding doubles speed. Your 3090 + MI60 = 56GB combined running frontier models at zero marginal cost.

## 17. SINGLE PROVIDER DEPENDENCY
**The gripe:** "Heavy reliance on a single AI provider introduces long-term strategic risk."
**Jeff's fix:** 39 local models in the pantry. BranchialAnalyzer runs consensus across multiple models. If one model goes down, gets worse, or changes pricing — Jeff routes to another. Infrastructure sovereignty: own every layer.

## 18. AI SLOP — Low-quality output flooding everything
**The gripe:** Jeff Geerling: "AI is destroying Open Source" with slop PRs.
**Jeff's fix:** `gate/` runs on EVERY output before it ships. The 4-line atomic check catches the cognitive flaws that produce slop. `staff/reviewer` agent reviews before submission. Jeff doesn't produce slop because the gate won't let it through. "60% to 99% code quality" — that's the measured improvement.

## 19. BIAS AND UNFAIRNESS
**The gripe:** AI reflects training data biases. Hiring systems discriminate.
**Jeff's fix:** `guard/` evaluates basins, not vocabulary. `staff/` BranchialAnalyzer runs diverse models including abliterated ones that don't suppress uncomfortable truths. Consensus across diverse architectures surfaces bias through disagreement. The disagreements ARE the signal.

## 20. NO HUMAN IN THE LOOP / BLIND TRUST
**The gripe:** "Blind trust in AI-driven decisions without human oversight increases systemic risk."
**Jeff's fix:** Everything Jeff produces goes through the gate before shipping. `staff/` has `reports_to` on every agent — someone reviews the work. WorkPlay makes human-in-the-loop engaging instead of tedious. Jeff doesn't trust himself. That's why he has a gate.

---

## The Scorecard

| # | Gripe | Jeff Module | Status |
|---|-------|-------------|--------|
| 1 | Sycophancy | personality + guard | Built |
| 2 | Hallucination | guard + gate + evolve | Built |
| 3 | Vendor lock-in | pantry (model-agnostic) | Built |
| 4 | Subscription creep | pantry + diet (zero cost) | Built |
| 5 | Context amnesia | sense (L1/L2/L3 cache) | Built |
| 6 | 70% problem | gate + evolve + staff | Built |
| 7 | Tool fatigue | hand (one tool, all domains) | Built |
| 8 | Data privacy | local-first architecture | Built |
| 9 | Hard to debug | gate (cognitive flaw mapping) | Built |
| 10 | Security vulns | guard + gate + staff/reviewer | Built |
| 11 | Skill atrophy | hand/teach (Socratic, K-gen) | Built |
| 12 | Engagement manipulation | personality (anti-dopamine) | Built |
| 13 | Opaque decisions | evolve (kerf_explain) | Built |
| 14 | Permanent beta | Pearlman Standard, no deps | Built |
| 15 | Verbose/moralizing | personality (anti-filler) | Built |
| 16 | High compute cost | diet + cluster (consumer HW) | Built |
| 17 | Single provider risk | pantry (39 models, any backend) | Built |
| 18 | AI slop | gate (60→99% quality) | Built |
| 19 | Bias/unfairness | guard + BranchialAnalyzer | Built |
| 20 | No human oversight | gate + staff/reports_to + WorkPlay | Built |

**20 for 20. Every gripe addressed. Every fix shipped in v1.0.0.**

---

AnnulusLabs LLC · Taos, New Mexico · April 2026
People. Planet. Profit third.

Jeff handles it.
