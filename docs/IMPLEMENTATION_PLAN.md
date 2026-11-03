# Dependency-ordered implementation plan

The complete phase criteria are in MASTER_REQUIREMENTS sections 8, 16 and 18. Execute tasks in TASK_LEDGER order. Every unit requires requirement linkage, acceptance, code/tests, local verification, records/checkpoint, and a verified commit when appropriate. Do not advance a partially complete gate. Preserve prior functionality; failures require bounded diagnostics, not weakened tests. Detect repeated errors, cyclic dependencies and scope drift before new features.

0: Context, registry, architecture/security, typed limits, packaging, checkpoint/logging; gate: all documents and environment validated.
1: Versioned models/migrations, WAL transitions, leases/idempotency, pause/cancel/recovery; gate: interrupted state resumes without duplicated completed work.
2: Provider protocols/mock/Meta/Baseten, validated outputs, fallback/circuit, reservations and daily usage; gate: deterministic provider contracts and failure accounting. Live acceptance separately unverified.
3: Questions/hypotheses/plans, trusted bounded worker, raw artifacts, deterministic evaluator, reports/CLI; gate: one reproducible complete command.
4: Independent fixtures/baselines/unseen data, replication/failure/uncertainty; gate: false results rejected.
5: Safe real retrieval, metadata/provenance, prior methods/contradictions, retrieval-informed hypotheses; gate: conclusions trace to actual sources.
6: Trees/revisions/mutation, diversity, branch and loop limits; gate: bounded multiple directions without duplicate work.
7: Separate market model, external evidence collection/import, competitor analysis/gates; gate: technically good but unvalidated candidate classified correctly.
8: Durable scheduler, concurrency, circuit/resource monitor, graceful controls/status; gate: interrupted extended bounded runs respect limits.
9: Research monitoring dashboard with active tasks/discoveries, hypothesis trees, evidence/evaluation status, spend/resources and human approval controls. CLI inspection complements the dashboard. Evaluate optional remote workers and specialized experimentation separately; gate: real persisted operations can be inspected and controlled without raw logs.

Phase 8 accepted commit: e1e5ae78731d3d00e6154e0226326cb9ee74f40b. Phase 9 preparation follows this commit; detailed dependency-ordered plan: [PHASE_9_IMPLEMENTATION_PLAN.md](PHASE_9_IMPLEMENTATION_PLAN.md). Plan only in this run; implementation has not started.
