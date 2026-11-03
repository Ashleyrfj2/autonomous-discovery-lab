PHASE: 8 — Extended autonomous operation
STATUS: LOCALLY_VERIFIED; required milestone commit identified by exact message below

IMPLEMENTED:
- SQLite migrations 7–8: durable experiment jobs and fair persistent queue, transactional transitions/events, stable run/stage/replication identity, fenced ownership and cached completed results.
- Bounded foreground scheduling, one stage per dispatch, queue restart/backoff, admission constrained by the lowest active/requesting experiment policy. Queue status, worker results and resources are inspectable through CLI reports.
- Local coordinator PID plus creation-time identity, expiring leases, heartbeat, stale-owner rejection, orphan reconciliation and bounded pure-computation retries. Completed replications survive interruption. Legacy/remote identities require lease expiry.
- Active worker pause/cancel, SIGINT/SIGTERM shutdown, deadline interruption and resume. Worker wall/CPU/output/filesystem/network limits and RSS monitoring remain enforced.
- Absolute inference caller deadline, bounded transport threads, cooperative cancellation and rate backoff. Unknown remote outcomes retain conservative reservations; local cancellation does not establish remote cancellation or zero billing.
- Run/topic/policy, stage, job and queue projection audits; selected mock/public evidence retained with content addresses and independent snapshots. Legacy records lacking topic/release anchors are explicitly identified.

DEFECTS REPAIRED:
- B023: bind each cancellation callback's stage version; multi-iteration, released-owner, pause/resume and cancel regression coverage.
- Reconciliation could kill a worker whose lease renewed after initial selection: re-read identity/fence/status/expiry under a write transaction before termination.
- Queue mutation could overwrite inconsistent projection state before its audit: verify integrity before synchronization/admission. Jobs also audit before admission/cache reuse.
- Rate-limit backoff could delay cancellation: interruptible bounded wait prevents another call/reservation after a stop request.

VERIFICATION:
- Exact command: `uv run python scripts/qualify_phase8.py --root runtime/phase8-final --output docs/phase_reports/phase-8-acceptance`
- Run: 2026-11-03T10:50:09.652467+00:00 to 2026-11-03T10:50:31.126546+00:00; total 21.473948 seconds, including checks.
- `uv run ruff check .`: passed.
- `uv run pyright`: 0 errors, 0 warnings, 0 informational findings.
- `uv run pytest -q`: 143 passed in 9.49 seconds.
- `uv build`: wheel and source distribution succeeded.
- Focused integration/adversarial/state/budget selection: 78 passed in 6.06 seconds. Exact arguments, timestamps, outputs and case names are retained in acceptance/validation.json and targeted-tests.xml.
- Fresh operation: eight workflows, 96 committed stages, 24 completed jobs; two stage workers, peak one experiment; 3.757361 seconds; zero provider spending. Coordinator restarted after 16 stage dispatches; each run had progressed; all job attempts remained one. Final batch used 94 dispatches, including admission contention.
- Independently recomputed all 24 job results. Observed maximum worker RSS 17,432,576 bytes. Technical success true; novelty unknown; market level 0/unvalidated.
- Verified 712 hash-chained events and projections against the fresh retained anchor; 73 archived artifacts verified by SHA-256. Six retained historical/current snapshots also verified during final audit.
- Focused tests exercise killed queue/job coordinators, preserved first replica, no second execution of cached jobs, two simultaneously authorized native workers, default global limit, stale-owner rejection, reused PID protection, renewed-lease race, signal shutdown, active pause/cancel/deadline, budget rejection, uncertain timeout/cancel accounting, evidence manipulation, runtime/output enforcement and RSS supervisor rejection. The forced RSS observation is simulated; no claim of a hostile native memory stress test.

SOURCE IDENTITY:
- Base commit: 8a182e712ea042b8379672936153bcbd281f4e87.
- Final source/tests/config/scripts/dependencies manifest SHA-256: 58aba75623694c0fbf86b227d7a5a6f95f8e2b054057cad2bb84b2f66bb4fb21.
- Source bytes checked unchanged before/after qualification and again before staging. Documentation is bound by the milestone commit, avoiding a self-referential commit hash.
- Snapshot file SHA-256: 9cf69f8710cd3f06f81cd09d03035d2d72c886f45d76b6610b95c5e201f6437f.
- Anchor: sequence 712, e00f398ad260ea9c97c049ab83613edefd4faeace89f7d279becd691762e80f0.
- Authoritative evidence: phase-8-acceptance/{acceptance.json,source-manifest.json,validation.json,targeted-tests.xml,bounded-operation.json,evidence-snapshot.json,artifacts/}.
- Earlier phase-8-bounded-operation.json and phase-8-evidence-snapshot.json remain historical and are not acceptance evidence for the final source.

REQUIREMENT AUDIT:
| Requirement / capability | Local acceptance evidence | Remaining qualification |
|---|---|---|
| REQ-028 durable scheduling/concurrency/recovery | jobs.py, scheduler.py; durable-job and scheduled-operation tests; fresh eight-run record | Single-host SQLite backend; no distributed execution claim |
| REQ-029 circuits/resources/shutdown/status | providers/router, runner, CLI jobs/queue/status; provider/resource/signal/deadline tests | No long-duration soak or live-provider qualification |
| REQ-012/013 controls/fencing/idempotency | active pause/cancel, replacement owner, killed coordinator, cached-job and preserved-replica tests | Incomplete pure computation can be retried explicitly |
| REQ-006/015/024 budgets/provider failures/resource bounds | budget/provider tests, deadlines/backoff and native worker tests | Accurate configured rates required; uncertain billing retained; RSS polling can overshoot |
| REQ-007/017/032/033/034/037 context/evidence/checks | repository records, checkpoint, snapshot/CAS, 143-test suite, all required local checks | Phase 9 and full-project/fresh-agent release audit remain |

ACCEPTANCE CHECKLIST:
- [x] Phase 8 durable jobs, scheduling, local lifecycle/recovery, controls, resources and status implemented.
- [x] B023 repaired with regression coverage; Ruff, Pyright, full tests and packaging pass.
- [x] Fresh bounded operation and source identity recorded; historical evidence preserved.
- [x] Interrupted recovery, replication preservation, fairness/concurrency, pause/cancel/termination and budgets qualified locally.
- [x] Persistence/evidence audits and independent evaluation pass; context, operations, decisions and traceability updated.
- [x] Known limits recorded; staged content reviewed for intended files and secret exclusions before commit.
- [x] Acceptance tied to exact final source manifest; committed Git object manifest checked after commit.

LIMITATIONS / RISKS:
This is a short mock-provider qualification, not a long-duration soak or production acceptance. Execution is reviewed encoding-family code on this macOS host, using private/deprecated Seatbelt; unsupported platforms fail closed. RSS polling can overshoot between observations. Cleanup depends on local OS process/signal behavior and permissions, and may fail closed for an unkillable worker. A reconciliation wait is bounded to two seconds; native supervisor cleanup waits to reap its killed child. SQLite may wait up to ten seconds for a writer. Scheduling time is an admission/cancellation deadline, not a guarantee that all cleanup or authorized retrieval returns by that instant. Public retrieval follows its own bounded network timeouts and drains before stage commit; it is not provider-side cancelable. Transport daemon threads are capped at eight per process and may outlive the caller until transport completion; no guarantee of remote cancellation or no late charge. No arbitrary-code, live-inference, distributed, novelty, real market, deployment or production claim.

DESIGN DECISIONS: DEC-013 (durable jobs/fair queue/local process identity), DEC-014 (caller cancellation and conservative uncertain accounting), DEC-015 (projection audits and exact source qualification).
BLOCKERS: none for accepted local Phase 8 scope. External/live/production qualifications remain distinct.
LAST VERIFIED COMMIT: commit with exact message `feat: complete and verify phase 8 durable execution`; previous verified head 8a182e712ea042b8379672936153bcbd281f4e87. Exact milestone SHA is recorded in HANDOFF after commit.
NEXT TASK: only after the successful required commit, prepare a Phase 9 implementation plan; no Phase 9 implementation in this run.
