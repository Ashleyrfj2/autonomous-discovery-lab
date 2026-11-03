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
Next action: create required feat: complete and verify phase 8 durable execution commit, verify contents, then Phase 9 planning only


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
