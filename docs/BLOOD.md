# BLOOD

`jeff/blood` is one file on purpose for now.

Why it stays fused:

- Task state, audit, queueing, authority, and retry logic all mutate the same task graph.
- The runtime loop is the seam that Phase 3.5 MCP work will plug into.
- Splitting it before the relay/tool-bus rewrite would add file boundaries without reducing coupling.

What would justify a later split:

- The audit log gets a second storage backend.
- Queueing/backpressure needs a transport boundary.
- Authority or tool policy becomes reusable outside the runtime loop.

Until one of those is true, the Pearlman answer is to keep the spine in one place.
