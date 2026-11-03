# Autonomous Discovery Lab — project status report

**As of:** November 3, 2026
**Repository:** `/Users/ashley/Code/autonomous-discovery-lab`
**Milestone:** Phase 8 locally accepted and committed as `e1e5ae78731d3d00e6154e0226326cb9ee74f40b`; recovery in [HANDOFF.md](HANDOFF.md). Previous milestone: `8a182e712ea042b8379672936153bcbd281f4e87`.
**Source identity:** `58aba75623694c0fbf86b227d7a5a6f95f8e2b054057cad2bb84b2f66bb4fb21` (source/tests/config/scripts/dependency manifest).
**Overall status:** working local research prototype; phases 0–8 have recorded local acceptance. Phase 9 implementation has not started. The full project is incomplete.

## Goal overview

Build an autonomous research and experimental discovery platform that investigates scientific, technical, creative, consumer and commercial problems across industries. It should retrieve prior knowledge, identify gaps and contradictions, generate falsifiable hypotheses, design and execute authorized isolated experiments, independently evaluate and replicate results, preserve evidence, and use findings to select subsequent research. Candidate applications should receive a separate investigation of commercial potential.

The platform must operate within explicit spending and resource limits, recover from interruptions, support human intervention, and preserve enough context for a replacement agent to resume from the repository alone.

| Outcome | Required evidence | Current demonstration |
|---|---|---|
| Technical success | Measured experimental performance against preregistered criteria and a baseline | Demonstrated for a bounded encoding benchmark |
| Discovery success | Meaningful insight or improvement with novelty assessed against actual prior work | Novelty remains unknown |
| Commercial success | External problem evidence, an identifiable economic buyer, and credible willingness or ability to pay | Unvalidated; actual demo remains level 0 |

The authoritative scope is [MASTER_REQUIREMENTS.md](MASTER_REQUIREMENTS.md). All 42 stable requirements remain tracked in [REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md). A successful benchmark alone satisfies neither novelty nor commercial demand.

## Completed and locally verified

| Phase | Completed capability | Recorded acceptance evidence |
|---|---|---|
| 0 — Persistent context | Original brief, charter, architecture, requirement registry, decisions, ledger, handoff, security/operating documents; Python 3.12/uv package; sanitized logs and atomic checkpoints | [Phase 0](phase_reports/phase-0.md) |
| 1 — Durable orchestration | SQLite WAL and migrations; persisted lifecycle; transactional transitions; leases, fencing and idempotency; pause/cancel/resume; interrupted-workflow recovery | [Phase 1](phase_reports/phase-1.md) |
| 2 — Model integration and budgets | Common Meta/Baseten/mock contracts; structured validation and stage routing; explicit fallback; usage accounting, request caching, conservative reservations, run/day limits and provider circuits | [Phase 2](phase_reports/phase-2.md); HTTP contracts tested with mock transports |
| 3 — Minimum research loop | One-command twelve-stage workflow; preregistered plans; reviewed isolated worker; held-out evaluation, two replications, evidence artifacts and reports | [Phase 3](phase_reports/phase-3.md) |
| 4 — Independent verification | Metric/reconstruction recomputation; baselines; worker/fixture/evaluator hashes; strict result schemas; rejection of fabricated success, altered measurements and provenance manipulation | [Phase 4](phase_reports/phase-4.md) |
| 5 — External research | Bounded authorized HTTPS retrieval; Crossref/public-document provenance; source comparison and conservative synthesis; exact quotations; dependent-claim invalidation when evidence changes | [Phase 5](phase_reports/phase-5.md), [actual retrieval record](phase_reports/phase-5-live-retrieval.json) |
| 6 — Branching discovery | Persistent hypothesis trees, parent/child history, duplicates, diversity-aware allocation, exploration/exploitation controls, bounded stopping and justified failure-driven revision | [Phase 6](phase_reports/phase-6.md) |
| 7 — Commercial validation gates | Separate user/buyer/opportunity models; alternatives, competition and adoption information; source-bound evidence with human review; levels 0–4; synthetic demand excluded; withdrawal/invalidation lowers current classification | [Phase 7](phase_reports/phase-7.md); positive commercial levels tested with local fixtures only |

The persisted lifecycle is:

`DISCOVER → RESEARCH → HYPOTHESIZE → PRIORITIZE → DESIGN → PREFLIGHT → EXECUTE → VERIFY → REPLICATE → ASSESS → VALIDATE_MARKET → DECIDE`

The default executable experiment compares reviewed run-length encoding with identity encoding on synthetic data, including 48 held-out cases and two replications. A failed identity candidate can produce an evidence-backed revision without relaxing its comparator, data or success threshold. Generic quantitative proposals can be retained across domains, but execution remains limited to the reviewed encoding family.

Real public-source retrieval has been exercised through the application, including Crossref publication records and RFC 1951. This is distinct from live model inference, which has not been verified.

## Phase 8 — completed local acceptance

Durable experiment sub-jobs and a fair persistent queue now support bounded foreground scheduling, concurrency admission, cached completed results, interrupted replication recovery, local coordinator/worker identity checks, fenced ownership, active-worker pause/cancel, deadline interruption, signal shutdown and resumption. Provider callers have absolute deadlines and cooperative cancellation/backoff; uncertain remote outcomes retain conservative reservations. Run, stage, job and queue projections are audited against evidence.

The B023 callback binding defect was repaired with a regression covering multiple stage versions and pause/resume. The audit also repaired a lease-renewal reconciliation race and prevented queue mutation from covering inconsistent state. See [Phase 8 report](phase_reports/phase-8.md) and [fresh acceptance record](phase_reports/phase-8-acceptance/acceptance.json).

Fresh qualification completed **8 workflows, 96 committed stages and 24 experiment jobs**, using two stage workers with a peak of one experiment, in **3.757361 seconds**, with **$0 provider spend**. The coordinator was restarted after 16 dispatches; all runs had progressed and no completed job reran. All 24 results were independently recomputed. A 712-event snapshot and 73 content-addressed artifacts were retained and hash-verified.

This is a short bounded local mock-provider qualification, not a long-duration soak. Earlier phase-8-bounded-operation.json and phase-8-evidence-snapshot.json remain historical; the final source is qualified by phase-8-acceptance/.

## Verification against final Phase 8 source

| Check | Actual result |
|---|---|
| `uv run ruff check .` | Passed |
| `uv run pyright` | 0 errors, warnings or informational findings |
| `uv run pytest -q` | **143 passed in 9.49 seconds** |
| `uv build` | Wheel and source distribution succeeded |
| Focused recovery/concurrency/control/provider/budget/evidence tests | **78 passed in 6.06 seconds**; exact selection and results retained |
| Source, artifacts and retained anchors | Exact manifest unchanged through qualification; 73 fresh artifact hashes and six current/historical snapshots verified |

Exact commands, UTC start/end times, results, source manifest, focused case names and runtime observations are recorded in [phase-8-acceptance](phase_reports/phase-8-acceptance/acceptance.json). Technical success remains distinct from unknown novelty and commercial level 0. No live Meta/Baseten inference, real buyer/payment validation, hosted deployment or production qualification is established.

## Remaining work, in priority order

| Priority | Work still needed | Evidence required before acceptance |
|---|---|---|
| 1 — Phase 9 interface | Monitoring dashboard for active work, discoveries, hypothesis trees, evidence, evaluation, spend and resource usage; human approval and research controls | Operators inspect and control real persisted research without relying on raw logs; interface and control flows verified |
| 2 — Broader research execution | Add reviewed experiment implementations, plans and independent evaluators for additional problem types; deepen source interpretation and prior-work assessment | Substantive research/experiments across different problem types; changing topic labels does not demonstrate this |
| 3 — Live integration qualification | Authorized provider configuration with current model capabilities/prices and explicit spending limits; small bounded integration tests | Actual provider responses, usage, failure and budget evidence, separate from mock HTTP tests |
| 4 — Final requirements audit | Reconcile all requirements and phase gates; test fresh-agent recovery; review security/operations and release readiness; document justified optional deferrals | Evidence for every non-deferred acceptance criterion, with local, live-integration and production status kept separate |

Actual novelty and commercial success depend on future research and external evidence. They cannot be manufactured to close a software milestone. Commercial levels 1–4 require qualifying real evidence and truthful human review; current tests establish enforcement behavior only. No buyer outreach or paid service usage is implied by this report.

## Material limitations

- Execution and automated experimental revision cover one reviewed encoding family. The full cross-industry discovery mission remains undemonstrated.
- Retrieval and synthesis are bounded and conservative. Metadata matches, method mentions and possible conflicts do not establish findings or exhaustive prior-art coverage.
- Worker confinement is locally tested on macOS using deprecated/private Seatbelt facilities; unsupported platforms fail closed. RSS monitoring permits possible sampling overshoot. This is not a production arbitrary-code sandbox.
- Interrupted unfinished computation may be explicitly retried; committed completed results are preserved. A caller timeout/cancellation does not prove provider-side cancellation or zero billing, so uncertain reservations remain.
- Optional remote/distributed workers and physical experimentation remain deferred pending need and authorization. Hackathon eligibility is unconfirmed.

There is no known local blocker. Phase 8 is committed; [the Phase 9 plan](PHASE_9_IMPLEMENTATION_PLAN.md) was prepared afterward. Phase 9 dashboard/backend implementation is outside this run's scope. Detailed task state remains in [TASK_LEDGER.md](TASK_LEDGER.md), with recovery instructions in [HANDOFF.md](HANDOFF.md).
