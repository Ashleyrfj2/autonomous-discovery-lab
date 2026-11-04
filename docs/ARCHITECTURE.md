# Architecture

Status: phases 0–8 implemented and locally verified; detailed scope/evidence remains in traceability and ledger. Phase 9 interface is unimplemented.

A modular Python monolith owns durable workflows in SQLite WAL. Versioned Pydantic contracts validate configuration, states, experiments, measurements, provider responses and evidence. Transactions persist state and append evidence together. Conditional worker leases and fencing tokens prevent stale writes; idempotency keys prevent duplicate transitions. External work executes outside SQLite transactions and records stable job identities; recovery reconciles existing artifacts rather than silently replaying completed side effects.

Lifecycle: DISCOVER → RESEARCH → HYPOTHESIZE → PRIORITIZE → DESIGN → PREFLIGHT → EXECUTE → VERIFY → REPLICATE → ASSESS → VALIDATE_MARKET → DECIDE. Each step has typed input/output, preconditions, failure/retry policy, resource records and explicit allowed forward/backward actions. Run status separately supports active/paused/cancelled/failed/completed. Stage failure retains prior state.

Modules: orchestrator (DB, migrations, leases, checkpoints, scheduling); models (Meta/Baseten/mock adapters, router, usage reservations); research (retrieval/provenance/synthesis); hypotheses (falsifiability, trees, ranking); experiments (preregistered plans, trusted subprocess workers); evidence (hash chain, content-addressed artifacts, claims/invalidation); commercial (external-evidence gates); security (authorization, redaction, budgets); reporting (CLI, durable reports and monitoring).

MVP experiments use fixed reviewed implementations, not submitted Python or shell. A subprocess and OS resource limits bound trusted computation. This is not an arbitrary-code sandbox. If a platform cannot enforce required isolation/resource policy, preflight must fail closed. The default demo performs offline, seeded algorithm comparison with training and held-out datasets, independent reference evaluator, baseline, replications and declared metrics.

Provider contract: generate, generate_structured, get_usage, estimate_cost, health_check. Config carries endpoint/model/capabilities and explicit prices; never silently assume a current model or rate. Mock runs use zero-cost deterministic proposals. Router reserves estimated upper costs before calls, settles usage conservatively, records fallback identity and circuit state. Live configuration is opt-in. Research retrieval is explicit network authorization with bounded responses and SSRF controls. Commercial evidence ingestion never contacts buyers.

Durable JSONL logs are sanitized, locked and append-only; checkpoints use atomic replace plus fsync. Evidence chain detects unexpected edits only relative to a trusted anchor; retained export snapshots are needed beyond the local trust boundary. SQLite and local anchors are not immutable against an attacker controlling both.

Phase 8 adds two durable projections: experiment_jobs (stable run/stage-version/replication identity, plan digest, lease/fence, process identity and accepted raw artifact) and work_queue (one-stage fair foreground dispatch). Job commits and their evidence are atomic; a completed replica is independent of the enclosing stage's later completion. The worker supervisor checks durable authority and shutdown controls during execution. Recovery audits evidence, verifies current identity/expiry under the writer lock, terminates only an abandoned matching process, and records bounded pure-computation retry. Coordinator identity is single-host PID plus creation time. Queue controls derive from durable run status. Evidence readers audit run, stage, job and queue projections; legacy missing topic/release anchors remain explicit.

Inference caller deadlines/cancellation use trusted context local to a stage. Network transport is bounded separately and may outlive the caller; unknown reservations remain conservative budget consumption. No remote side-effect exactly-once guarantee is inferred. CLI queue/jobs/status/tree expose durable scheduling, resource and scientific state; Phase 9 UI remains unimplemented.

## Reviewed cross-family extension (unmerged / unverified)

An additive remote branch introduces a fixed `encoding-v1` / `allocation-v1` experiment registry with separate vetted worker/fixtures/evaluators, sharing the existing macOS fenced job supervisor and event chain. Director and Lab accept typed allocation hypotheses and assign family-aware allocations without comparing incomparable raw scores. Three opt-in, distinct model roles propose/explore/criticize as input to scientific work; critic assertions are not evaluator verdicts. Separate estimated-cost portfolio is advisory only and does not write to the scheduler or provider budget ledger. This section documents IMPLEMENTED_UNVERIFIED branch work, not a new accepted architecture gate or a replacement for the Phase9 dashboard.

## Bounded autonomous discovery

The foreground `discover` workflow registers a versioned objective and uses the existing Store,
provider Router, cancellation scope, Catalog, and artifact store. It ranks a typed three-direction
plan, captures bibliography and registered public sources, and advances up to two source-backed
hypotheses. A separate model reviews each viable hypothesis. At most one targeted search and one
revision follow when an objection and new evidence justify the additional work. A run can finish
with zero surviving candidates.

SQLite events checkpoint every stage with a content digest. Lease fencing controls publication.
Stable request identities reuse the existing provider cache and accounting ledger. The packet
records model identities, exact excerpts, hypotheses, criticisms, decision reasons, and usage.
Read-only replay checks source validity and digest integrity without external access.
Technical results, novelty, and independently attested commercial evidence have separate gates.
See the [autonomous research qualification](phase_reports/autonomous-research-2026-11-03.md).

## Long-session controller

The `session` CLI sequences the existing bounded Discovery-v2 runs as
session-owned branches. Session registration, branch intent, query and proposal
admission, branch outcomes and stop reasons are SQLite events. Parent and child
leases reuse existing fencing and recovery. A fixed admission envelope is
calculated before each branch and reservation checks run under the writer lock.
Session controls and branch state remain authoritative in SQLite. The reviewed
experiment scheduler retains its existing responsibilities.

The controller uses a bounded evidence-linked planning context, durable
query fingerprints, cited-passage fingerprints and approximate mechanism
matching. The complete source and candidate records stay in their child
packets and content-addressed archives. The [runbook](LONG_SESSION_RUNBOOK.md)
records the scope of offline and live acceptance.

## Capability-v1 extension

The current optional `DiscoverySpec.capability` policy selects typed track-aware planning, balanced source/target/prior-art retrieval, gap and AI/non-AI analysis, versioned opportunity proposals and independent capability critique within the same Discovery-v2 engine. Per-stage GenerationRequest reasoning/output/timeout fields are part of request identity; absent fields preserve historical identity serialization. Extended branches renew the existing short lease at checkpoints. Candidate validation remains provisional; experiment and commercial authorities remain separate. Direction notes are associated by trace index, including read-only projections of old reports. Stagnation uses reviewed findings/critique/negative outcomes and distinct candidates rather than retrieval volume. See research_quality/CAPABILITY_V1.md for contracts and limitations, and LONG_SESSION_RUNBOOK.md for the current profiles and bounds.

The new `*-medium-v2.json` qualification profiles preserve the capability-v1 contracts and request ledger. Request timeout overrides now also reach httpx operation bounds, while the independent caller deadline, branch/session cancellation, model identity checks and uncertain-reservation rules remain in force. Profiles belonging to saved sessions are immutable. See DEC-028 and the current runbook; changing reasoning policy is not evidence of research improvement.
