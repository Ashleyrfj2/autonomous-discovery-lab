# Architecture

Status: initial contracts; implementation statuses live in the traceability and ledger.

A modular Python monolith owns durable workflows in SQLite WAL. Versioned Pydantic contracts validate configuration, states, experiments, measurements, provider responses and evidence. Transactions persist state and append evidence together. Conditional worker leases and fencing tokens prevent stale writes; idempotency keys prevent duplicate transitions. External work executes outside SQLite transactions and records stable job identities; recovery reconciles existing artifacts rather than silently replaying completed side effects.

Lifecycle: DISCOVER → RESEARCH → HYPOTHESIZE → PRIORITIZE → DESIGN → PREFLIGHT → EXECUTE → VERIFY → REPLICATE → ASSESS → VALIDATE_MARKET → DECIDE. Each step has typed input/output, preconditions, failure/retry policy, resource records and explicit allowed forward/backward actions. Run status separately supports active/paused/cancelled/failed/completed. Stage failure retains prior state.

Modules: orchestrator (DB, migrations, leases, checkpoints, scheduling); models (Meta/Baseten/mock adapters, router, usage reservations); research (retrieval/provenance/synthesis); hypotheses (falsifiability, trees, ranking); experiments (preregistered plans, trusted subprocess workers); evidence (hash chain, content-addressed artifacts, claims/invalidation); commercial (external-evidence gates); security (authorization, redaction, budgets); reporting (CLI, durable reports and monitoring).

MVP experiments use fixed reviewed implementations, not submitted Python or shell. A subprocess and OS resource limits bound trusted computation. This is not an arbitrary-code sandbox. If a platform cannot enforce required isolation/resource policy, preflight must fail closed. The default demo performs offline, seeded algorithm comparison with training and held-out datasets, independent reference evaluator, baseline, replications and declared metrics.

Provider contract: generate, generate_structured, get_usage, estimate_cost, health_check. Config carries endpoint/model/capabilities and explicit prices; never silently assume a current model or rate. Mock runs use zero-cost deterministic proposals. Router reserves estimated upper costs before calls, settles usage conservatively, records fallback identity and circuit state. Live configuration is opt-in. Research retrieval is explicit network authorization with bounded responses and SSRF controls. Commercial evidence ingestion never contacts buyers.

Durable JSONL logs are sanitized, locked and append-only; checkpoints use atomic replace plus fsync. Evidence chain detects unexpected edits only relative to a trusted anchor; retained export snapshots are needed beyond the local trust boundary. SQLite and local anchors are not immutable against an attacker controlling both.
