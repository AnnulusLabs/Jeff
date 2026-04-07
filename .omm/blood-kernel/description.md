# blood — Production Hardening

The circulatory system. Carries state discipline, audit trails,
spawn controls, backpressure, and error contracts to every module.

Key principle: agents CANNOT execute without human approval.
The kernel stops at APPROVED and returns to the caller.
Only actor="human" can transition to EXECUTING.

10 production fixes in one module:
1. Task state machine  2. Spawn limits  3. Audit log
4. Backpressure  5. Gate voting  6. Evolution safety
7. Tool sandbox  8. Context budget  9. Error contracts
10. Human authority enforcement
