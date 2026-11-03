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
Status: VERIFIED
Files: src/autodiscover/orchestrator/{contracts,store}.py
Tests: tests/unit/test_state.py; tests/integration/test_recovery.py
Verification: docs/phase_reports/phase-1.md; 11 tests total passed
Blockers: none
Next action: P2-PROVIDERS


## P1-RECOVERY
Task ID: P1-RECOVERY
Phase: 1
Description: Leases/fencing/idempotency and pause/cancel/resume; acceptance: killed process recovery no duplicate commits
Dependencies: P1-STATE
Status: VERIFIED
Files: src/autodiscover/orchestrator/{contracts,store}.py
Tests: tests/unit/test_state.py; tests/integration/test_recovery.py
Verification: docs/phase_reports/phase-1.md; 11 tests total passed
Blockers: none
Next action: P2-PROVIDERS


## P2-PROVIDERS
Task ID: P2-PROVIDERS
Phase: 2
Description: Mock/Meta/Baseten protocols, docs, structured validation and routing; acceptance: HTTP contracts/failures
Dependencies: P1-RECOVERY
Status: VERIFIED
Files: models/{contracts,providers,router}.py; security/budget.py; orchestrator/{store,migrations}.py; test_providers.py; test_budget.py; test_migrations.py
Tests: uv run pytest -q: 26 passed; uv run ruff check . passed; uv run pyright 0 errors; uv build wheel/sdist passed
Verification: phase_reports/phase-2.md
Blockers: none
Next action: P3-LOOP: implement preregistered trusted worker, content-addressed evidence and full CLI research cycle


## P2-BUDGET
Task ID: P2-BUDGET
Phase: 2
Description: Reservations/token/day/run/circuit accounting; acceptance: exhaustion/concurrent refusal/unknown cost
Dependencies: P2-PROVIDERS
Status: VERIFIED
Files: models/{contracts,providers,router}.py; security/budget.py; orchestrator/{store,migrations}.py; test_providers.py; test_budget.py; test_migrations.py
Tests: uv run pytest -q: 26 passed; uv run ruff check . passed; uv run pyright 0 errors; uv build wheel/sdist passed
Verification: phase_reports/phase-2.md
Blockers: none
Next action: P3-LOOP: implement preregistered trusted worker, content-addressed evidence and full CLI research cycle


## P3-LOOP
Task ID: P3-LOOP
Phase: 3
Description: Question/hypothesis/plan/worker/evidence/CLI; acceptance: full reproducible offline cycle
Dependencies: P2-BUDGET
Status: VERIFIED
Files: experiments/{contracts,datasets,worker,runner,evaluator}.py; evidence/{artifacts,chain}.py; hypotheses/engine.py; orchestrator/lab.py; cli.py; security/redaction.py; tests/{unit,integration,adversarial,end_to_end}; docs/phase_reports/phase-3-evidence-snapshot.json
Tests: uv run pytest -q: 35 passed; Ruff passed; Pyright 0 errors; uv build wheel/sdist passed; autodiscover demo completed with technical_success=true, novelty=unknown, commercial level=0, cost USD 0; snapshot export verified
Verification: phase_reports/phase-3.md
Blockers: none
Next action: P4-VERIFY: harden raw-result schemas and preregistered code identity; reject metric/fixture/claim manipulation; verify replication and uncertainty


## P4-VERIFY
Task ID: P4-VERIFY
Phase: 4
Description: Independent held-out evaluator/replication/uncertainty; acceptance: falsified results rejected
Dependencies: P3-LOOP
Status: VERIFIED
Files: experiments/{contracts,runner,evaluator}.py; evidence/chain.py; orchestrator/lab.py; tests/adversarial/test_evaluation_manipulation.py; tests/unit/test_hypotheses.py
Tests: uv run pytest -q: 55 passed; Ruff passed; Pyright 0 errors; uv build wheel/sdist passed; v2 demo completed locally with no provider spend
Verification: phase_reports/phase-4.md
Blockers: none
Next action: P5-RESEARCH: safe bounded real-source retrieval, metadata/provenance, source comparisons, contradictions, knowledge and claim invalidation


## P5-RESEARCH
Task ID: P5-RESEARCH
Phase: 5
Description: Safe retrieval/provenance/comparison/claim invalidation; acceptance: actual sources traced + adversarial tests
Dependencies: P4-VERIFY
Status: VERIFIED
Files: research/{retrieval,catalog,intelligence}.py; hypotheses/engine.py; orchestrator/{lab,migrations}.py; evidence/chain.py; cli.py; test_research_intelligence.py; test_retrieval_security.py; phase-5-live-retrieval.json; phase-5-evidence-snapshot.json; selected public acceptance CAS archives
Tests: uv run pytest -q: 72 passed; Ruff passed; Pyright 0 errors; uv build passed; actual HTTPS retrieval and full CLI research/resume passed separately from mock tests
Verification: phase_reports/phase-5.md
Blockers: none
Next action: P6-BRANCH: persistent hypothesis trees/revisions, diversity-aware bounded allocation, duplicate and loop detection, justified failure-driven replanning


## P6-BRANCH
Task ID: P6-BRANCH
Phase: 6
Description: Trees/mutation/diversity/loop/stopping/replanning; acceptance: bounded branches and justified failure revision
Dependencies: P5-RESEARCH
Status: VERIFIED
Files: hypotheses/{director,proposals}.py; orchestrator/{lab,loops,migrations,contracts,store}.py; evidence/{chain,branches}.py; models/router.py; security/budget.py; config.py; cli.py; test_branch_director.py; test_progress_guards.py; recovery/adversarial/end-to-end tests; phase-6 evidence artifacts
Tests: uv run pytest -q: 92 passed; Ruff passed; Pyright 0 errors; uv build wheel/sdist passed; autodiscover explore completed three bounded allocations, preserved negative results, cost USD 0; archived hashes and snapshot verified
Verification: phase_reports/phase-6.md
Blockers: none
Next action: P7-MARKET: separate buyer/user/opportunity models, external evidence provenance/review, competition/adoption analysis and enforced commercial levels0–4


## P7-MARKET
Task ID: P7-MARKET
Phase: 7
Description: External market import/models/gates; acceptance: technical success cannot assert commercial success
Dependencies: P6-BRANCH
Status: VERIFIED
Files: commercial/{contracts,service}.py; evidence/{markets,chain}.py; research/{catalog,retrieval}.py; orchestrator/{lab,contracts,migrations}.py; security/redaction.py; cli.py; test_commercial_validation.py; test_commercial_evidence.py; COMMERCIAL_VALIDATION.md; phase-7 acceptance artifacts
Tests: uv run pytest -q: 110 passed; Ruff passed; Pyright 0 errors; uv build wheel/sdist passed; full demo classified technical=true, novelty=unknown, commercial level 0, cost USD0; public demo artifacts and retained snapshot saved
Verification: phase_reports/phase-7.md
Blockers: none
Next action: P8-OPERATE: durable scheduler/sub-jobs, bounded concurrency, interruption reconciliation, resource monitoring and active-worker pause/cancel/shutdown controls


## P8-OPERATE
Task ID: P8-OPERATE
Phase: 8
Description: Durable jobs/scheduler, bounded concurrency, circuits/resources/status and interrupted recovery/controls. Acceptance: all Phase 8 checks and fresh exact-source qualification.
Dependencies: P7-MARKET
Status: VERIFIED
Files: orchestrator/{jobs,scheduler,lab,store,migrations}.py; experiments/runner.py; security/{processes,cancellation,budget}.py; evidence/{jobs,runs,scheduling,chain}.py; models/{providers,router,contracts}.py; cli.py; scripts/qualify_phase8.py; associated tests/docs/evidence
Tests: 143 full tests; 78 focused tests; Ruff passes; Pyright clean; wheel/sdist builds
Verification: phase_reports/phase-8.md; phase_reports/phase-8-acceptance/; fresh eight workflows/96 stages/24 jobs, peak 1 experiment, zero provider spend, 712-event snapshot and 73 artifacts verified; exact source manifest recorded
Blockers: none in local Phase 8 scope; no live/distributed/production acceptance
Next action: completed and committed as e1e5ae78731d3d00e6154e0226326cb9ee74f40b; Phase 9 plan prepared after commit, implementation next session only


## P9-INSPECT
Task ID: P9-INSPECT
Phase: 9
Description: CLI dashboard/tree/evidence/spend/approval; acceptance: inspection/control without raw logs; evaluate optional extensions
Dependencies: P8-OPERATE
Status: IN_PROGRESS
Files: docs/PHASE_9_IMPLEMENTATION_PLAN.md (plan only; P9-READ code now verified)
Tests: P9-READ150 pass; remaining auth/UI/control/review/browser qualification pending
Verification: phase_reports/phase-9-read.md (read task only)
Blockers: none
Next action: next implementation session P9-READ shared non-persisting read service; see PHASE_9_IMPLEMENTATION_PLAN.md


## P5-STATUS-REPORT
Task ID: P5-STATUS-REPORT
Phase: 5
Description: User-requested overview of the full goal, completed work, remaining work and qualification limits; REQ-007/034/037.
Dependencies: P5-RESEARCH
Status: VERIFIED
Files: docs/PROJECT_STATUS_REPORT.md; KNOWN_ISSUES.md; IMPLEMENTATION_PLAN.md; HANDOFF.md; RELEASE_READINESS.md; DEVELOPMENT_HISTORY.md
Tests: Existing implementation reverified: 72 tests; lint/types/build; 16 artifact hashes; five-event retained snapshot. Report inspected against code, ledger, master requirements and phase evidence.
Verification: docs/PROJECT_STATUS_REPORT.md
Blockers: none
Next action: P6-BRANCH; full implementation goal remains active


## STATUS-REPORT-REFRESH
Task ID: STATUS-REPORT-REFRESH
Phase: 8
Description: User-requested goal, completed-work and remaining-work report refreshed against current source, ledger, phase evidence and actual verification commands.
Dependencies: existing phases 0–7 records and Phase 8 worktree
Status: VERIFIED
Files: docs/PROJECT_STATUS_REPORT.md; HANDOFF.md; RELEASE_READINESS.md; TASK_LEDGER.md; DEVELOPMENT_HISTORY.md
Tests: Report records 134 passing tests, clean types/build and the open Ruff B023 failure; no implementation edited.
Verification: docs/PROJECT_STATUS_REPORT.md
Blockers: none for historical report refresh; Phase 8 subsequently accepted, see P8-OPERATE
Next action: historical report refresh superseded by Phase 8 acceptance; follow current handoff


## P9-PREPARE
Task ID: P9-PREPARE
Phase: 9
Description: Post-Phase8-commit implementation plan only; no Phase9 application changes.
Dependencies: P8-OPERATE accepted and committed
Status: VERIFIED
Files: docs/PHASE_9_IMPLEMENTATION_PLAN.md; HANDOFF.md; IMPLEMENTATION_PLAN.md; TASK_LEDGER.md
Tests: Plan reviewed against existing service/report/control/review contracts and master Phase9 scope; documentation links and source identity checked.
Verification: Phase8 milestone commit confirmed before plan creation.
Blockers: none for local plan; external deployment/spend/permissions remain separately authorized
Next action: P9-READ in next implementation session; no implementation in this run


## P8-RECHECK
Task ID: P8-RECHECK
Phase: 8
Description: Reconcile repeated completion request with existing accepted milestone and final-source evidence.
Dependencies: P8-OPERATE; P9-PREPARE
Status: VERIFIED
Files: docs/HANDOFF.md; DEVELOPMENT_HISTORY.md; TASK_LEDGER.md; phase_reports/phase-8-recheck.md
Tests: Fresh Ruff passes; Pyright 0 findings; 143 tests passed in 9.88s; wheel/sdist builds. Accepted source/Git objects,73 artifacts and 712 events reverified.
Verification: phase_reports/phase-8-recheck.md
Blockers: none; unrelated PROJECT_STATUS_REPORT_.md untouched
Next action: Phase9 P9-READ in next implementation session; planning only for this request


## P9-READ
Task ID: P9-READ
Phase: 9
Description: Shared read-only report and typed bounded snapshot views for REQ-031, preserving CLI persistence and scientific classifications.
Dependencies: P8-OPERATE
Status: VERIFIED
Files: reporting/{reports,views}.py; orchestrator/{store,lab}.py; read-only artifact/service adapters; tests/integration/test_read_views.py
Tests: 150 full tests; seven read-view regressions;78 focused Phase8 tests; Ruff and Pyright clean; wheel/sdist built
Verification: phase_reports/phase-9-read.md; phase-9-read-regression/
Blockers: none for local read service
Next action: P9-AUTH local authenticated adapter; full Phase9 remains in progress


## P9-AUTH
Task ID: P9-AUTH
Phase: 9
Description: Local authenticated read adapter/session/CSRF/Host/Origin boundary for REQ-031/016/038; no dashboard mutations yet.
Dependencies: P9-READ
Status: VERIFIED
Files: reporting/web.py; cli.py; pyproject.toml; uv.lock; tests/integration/test_operator_api.py
Tests:163 full tests pass;13 operator tests including real loopback HTTP; Ruff/Pyright/build pass; one upstream TestClient deprecation warning
Verification: phase_reports/phase-9-auth.md; phase-9-auth/ evidence
Blockers: none for local read API; paid12ui dashboard generation needs spending authorization
Next action: P9-CONTROL backend while design authorization is pending; no paid calls


## P9-CONTROL
Task ID: P9-CONTROL
Phase: 9
Description: Authenticated version/fence-checked and idempotent pause/resume/cancel, preserving worker recovery and budget authority.
Dependencies: P9-READ; P9-AUTH
Status: VERIFIED
Files: orchestrator/store.py; reporting/web.py; tests/integration/test_operator_controls.py
Tests:175 full tests, six control and six review tests,78 targeted Phase8 tests; Ruff/types/build pass; one upstream TestClient deprecation
Verification: phase_reports/phase-9-backend.md; phase-9-backend-regression/
Blockers: no backend blocker; mandatory paid UI design needs explicit spending cap
Next action: backend accepted; UI/browser interactions await completed design export


## P9-REVIEW
Task ID: P9-REVIEW
Phase: 9
Description: Source-bound operator review/withdrawal backend with authenticated authority, explicit confirmation, ownership, cursor/digest guards and idempotent event writes. Browser interface remains separate.
Dependencies: P9-READ; P9-AUTH
Status: VERIFIED
Files: commercial/service.py; reporting/{views,web}.py; test_operator_review.py
Tests: six review regressions;175 full tests; lint/types/build; source validation inside writer-lock probe
Verification: phase_reports/phase-9-backend.md; phase-9-backend-regression/
Blockers: none for backend; no real market validation obtained
Next action: connect explicit operator browser review without automatic attestations

## P9-VIEW
Task ID: P9-VIEW
Phase: 9
Description: Real-state operator dashboard and interactive views, using mandatory12ui design workflow.
Dependencies: P9-READ; P9-AUTH
Status: IN_PROGRESS
Files: docs/design/phase-9-overview-reference.png; phase-9-design-provenance.json; runtime/phase9-design/ records
Tests: four generated candidates inspected; strongestA selected; no completed HTML export or browser UI yet
Verification: phase_reports/phase-9-backend.md; design provenance
Blockers: authorized three-minute design window exhausted; conversion terminated at177.07s; extending it requires user direction
Next action: resume existing conversion under an extended allowance, integrate with verified APIs and run browser/visual qualification; do not repurchase draft


## P9-VIEW-CONTINUE
Task ID: P9-VIEW-CONTINUE
Phase: 9
Description: Continue saved12ui conversion under existing three-minute cap, without repurchasing draft.
Dependencies: P9-VIEW
Status: IN_PROGRESS
Files: docs/design/phase-9-design-provenance.json; runtime/phase9-design/resume-current.json; continuation-1.json
Tests: design-only continuation; no source changes or fresh backend tests. Existing resume refuses needs-reconciliation; isolated same-image local attempt returns no HTML before cutoff.
Verification: phase_reports/phase-9-design-continuation.md
Blockers: overall window exhausted without planner result; pending user response for one uninterrupted10-minute local attempt
Next action: await explicit longer allowance; no new draft/API fallback and no removal of interrupted ledgers
