# Task ledger

Allowed status: NOT_STARTED, IN_PROGRESS, BLOCKED, IMPLEMENTED_UNVERIFIED, VERIFIED, DEFERRED. Task acceptance is in Description and the phase gate in IMPLEMENTATION_PLAN. Per-feature tests and evidence must be linked before VERIFIED.

## P0-CONTEXT
Task ID: P0-CONTEXT
Phase: 0
Description: Persistent docs/registry/original brief; acceptance: all required docs and stable IDs exist
Dependencies: none
Status: VERIFIED
Files: AGENTS.md, docs/*
Tests: tests/unit/test_foundation.py (4 passed)
Verification: docs/phase_reports/phase-0.md
Blockers: none
Next action: P1-STATE


## P0-ENV
Task ID: P0-ENV
Phase: 0
Description: Package/config/checkpoints/sanitized logs; acceptance: checks + packaging + atomic recovery tests
Dependencies: P0-CONTEXT
Status: VERIFIED
Files: AGENTS.md, docs/*
Tests: tests/unit/test_foundation.py (4 passed)
Verification: docs/phase_reports/phase-0.md
Blockers: none
Next action: P1-STATE


## P1-STATE
Task ID: P1-STATE
Phase: 1
Description: Versioned WAL DB/migrations/transitions; acceptance: invalid/valid transitions tested
Dependencies: P0-ENV
Status: NOT_STARTED
Files: pending
Tests: pending
Verification: pending
Blockers: none
Next action: implement after dependencies verify


## P1-RECOVERY
Task ID: P1-RECOVERY
Phase: 1
Description: Leases/fencing/idempotency and pause/cancel/resume; acceptance: killed process recovery no duplicate commits
Dependencies: P1-STATE
Status: NOT_STARTED
Files: pending
Tests: pending
Verification: pending
Blockers: none
Next action: implement after dependencies verify


## P2-PROVIDERS
Task ID: P2-PROVIDERS
Phase: 2
Description: Mock/Meta/Baseten protocols, docs, structured validation and routing; acceptance: HTTP contracts/failures
Dependencies: P1-RECOVERY
Status: NOT_STARTED
Files: pending
Tests: pending
Verification: pending
Blockers: none
Next action: implement after dependencies verify


## P2-BUDGET
Task ID: P2-BUDGET
Phase: 2
Description: Reservations/token/day/run/circuit accounting; acceptance: exhaustion/concurrent refusal/unknown cost
Dependencies: P2-PROVIDERS
Status: NOT_STARTED
Files: pending
Tests: pending
Verification: pending
Blockers: none
Next action: implement after dependencies verify


## P3-LOOP
Task ID: P3-LOOP
Phase: 3
Description: Question/hypothesis/plan/worker/evidence/CLI; acceptance: full reproducible offline cycle
Dependencies: P2-BUDGET
Status: NOT_STARTED
Files: pending
Tests: pending
Verification: pending
Blockers: none
Next action: implement after dependencies verify


## P4-VERIFY
Task ID: P4-VERIFY
Phase: 4
Description: Independent held-out evaluator/replication/uncertainty; acceptance: falsified results rejected
Dependencies: P3-LOOP
Status: NOT_STARTED
Files: pending
Tests: pending
Verification: pending
Blockers: none
Next action: implement after dependencies verify


## P5-RESEARCH
Task ID: P5-RESEARCH
Phase: 5
Description: Safe retrieval/provenance/comparison/claim invalidation; acceptance: actual sources traced + adversarial tests
Dependencies: P4-VERIFY
Status: NOT_STARTED
Files: pending
Tests: pending
Verification: pending
Blockers: none
Next action: implement after dependencies verify


## P6-BRANCH
Task ID: P6-BRANCH
Phase: 6
Description: Trees/mutation/diversity/loop/stopping/replanning; acceptance: bounded branches and justified failure revision
Dependencies: P5-RESEARCH
Status: NOT_STARTED
Files: pending
Tests: pending
Verification: pending
Blockers: none
Next action: implement after dependencies verify


## P7-MARKET
Task ID: P7-MARKET
Phase: 7
Description: External market import/models/gates; acceptance: technical success cannot assert commercial success
Dependencies: P6-BRANCH
Status: NOT_STARTED
Files: pending
Tests: pending
Verification: pending
Blockers: none
Next action: implement after dependencies verify


## P8-OPERATE
Task ID: P8-OPERATE
Phase: 8
Description: Durable workers/concurrency/circuits/resource/status; acceptance: interruption/long bounded loops/controls
Dependencies: P7-MARKET
Status: NOT_STARTED
Files: pending
Tests: pending
Verification: pending
Blockers: none
Next action: implement after dependencies verify


## P9-INSPECT
Task ID: P9-INSPECT
Phase: 9
Description: CLI dashboard/tree/evidence/spend/approval; acceptance: inspection/control without raw logs; evaluate optional extensions
Dependencies: P8-OPERATE
Status: NOT_STARTED
Files: pending
Tests: pending
Verification: pending
Blockers: none
Next action: implement after dependencies verify
