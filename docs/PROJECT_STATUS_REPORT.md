# Autonomous Discovery Lab — project status report

**As of:** November 3, 2026  
**Repository:** `/Users/ashley/Code/autonomous-discovery-lab`  
**Verified implementation commit:** `e5338eae56bc303f5be27a59a6dc3849e777d785`  
**Current milestone:** local phase gates 0–5 have passed; Phase 6 is next.  
**Overall status:** working research-loop foundation; full project remains incomplete.

## Goal overview

Build an autonomous research and experimental discovery platform that can investigate problems across industries, retrieve existing knowledge, identify gaps and contradictions, generate falsifiable hypotheses, design and execute authorized experiments, independently evaluate and replicate results, preserve evidence, and use findings to direct subsequent research. Promising discoveries should also receive a separate investigation of their commercial potential.

The intended product must operate for extended periods within explicit limits, recover from interruptions, and remain understandable to a replacement coding agent using the repository's documents, code, logs and checkpoints.

Three outcomes must stay separate:

| Outcome | Evidence required |
|---|---|
| Technical success | A measurable experimental result against predefined criteria and a baseline. |
| Discovery success | A meaningful insight or improvement, with novelty assessed against actual prior work. |
| Commercial success | External evidence of a real problem, an identifiable economic buyer, and credible willingness or ability to pay. |

The current demonstration establishes a bounded technical result. It does not establish scientific novelty or commercial demand. The authoritative scope remains [MASTER_REQUIREMENTS.md](MASTER_REQUIREMENTS.md), with stable requirements in [REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md).

## What has been completed

| Phase | Implemented and locally verified | Evidence |
|---|---|---|
| **0 — Persistent context and environment** | Original brief preserved; charter, architecture, requirements, task ledger, decisions, handoff and operating documents; 42 stable requirement IDs; Python 3.12/uv package; typed default limits; atomic checkpoints and sanitized, locked JSONL logging. | [Phase 0 report](phase_reports/phase-0.md) |
| **1 — Durable orchestration** | Versioned lifecycle contracts; SQLite WAL and migrations; transactional state/evidence writes; idempotency; expiring worker claims and stale-worker fencing; bounded failures; pause, resume and cancellation. A deliberately terminated process recovered its committed step without duplicating it. | [Phase 1 report](phase_reports/phase-1.md) |
| **2 — Provider and spending foundation** | Common inference interface; Meta, Baseten and deterministic mock adapters; structured-response validation; stage routing; explicit fallback records; usage accounting; persistent request caching; cost reservations; run/day budget checks; bounded rate retries and persistent circuit breakers. Provider HTTP behavior was tested with mock transports. | [Phase 2 report](phase_reports/phase-2.md) |
| **3 — Minimum working loop** | CLI command runs all twelve stages, stores hypotheses and preregistered plans, executes a reviewed worker, evaluates held-out cases, replicates twice, saves content-addressed artifacts and produces a report. Committed work survives resumption. Native confinement tests reject host-file reads/writes and network access. | [Phase 3 report](phase_reports/phase-3.md) |
| **4 — Independent verification** | Independent metric and roundtrip recomputation; baseline comparison; held-out cases; strict raw-result schemas; preregistered worker/fixture/evaluator hashes; replication; uncertainty and failure reporting. Adversarial tests reject false success claims, model approvals, altered bytes, missing cases, invalid metrics and changed provenance. | [Phase 4 report](phase_reports/phase-4.md) |
| **5 — External research foundation** | Authorized, bounded HTTPS retrieval with DNS/address and redirect controls; Crossref metadata and primary-document ingestion; source provenance; quote-backed claims; basic source synthesis, method mentions and possible-conflict detection; knowledge search; cascading claim invalidation when supporting content changes; retrieved source IDs included in hypothesis provenance. | [Phase 5 report](phase_reports/phase-5.md) |

The persisted lifecycle is:

`DISCOVER → RESEARCH → HYPOTHESIZE → PRIORITIZE → DESIGN → PREFLIGHT → EXECUTE → VERIFY → REPLICATE → ASSESS → VALIDATE_MARKET → DECIDE`

Having all twelve states implemented does not mean every stage has its full final capability. Prioritization is currently minimal, commercial assessment returns an unvalidated result, and extended research scheduling remains unfinished.

## What currently works end to end

The default offline experiment compares reviewed run-length encoding against raw bytes on seeded synthetic data. It uses 24 training cases, 48 held-out cases and two additional replication runs. The evaluator checks exact reconstruction and a predefined savings threshold. An identity baseline and an adverse alternating-data profile correctly fail their savings criteria.

The default report distinguishes `technical_success=true`, `novelty=unknown`, and commercial `level=0` / `validated=false`.

Live source retrieval has also been exercised through the application: two Crossref publication records and RFC 1951 were retrieved, hashed and recorded, with an exact source-attributed quote. A separate CLI research-and-resume run retrieved three publication records and completed the technical loop with actual source IDs. These were real public-source requests, separate from mocked inference tests.

Evidence is preserved in [the live retrieval record](phase_reports/phase-5-live-retrieval.json), [its retained evidence snapshot](phase_reports/phase-5-evidence-snapshot.json), and the selected public artifacts under [phase_reports/artifacts](phase_reports/artifacts).

## Verification performed for this report

The following checks were rerun against the implementation commit above:

| Check | Result |
|---|---|
| `uv run pytest -q` | **72 passed** across unit, integration, adversarial and end-to-end tests. |
| `uv run ruff check .` | Passed. |
| `uv run pyright` | Zero errors, warnings or informational findings. |
| `uv build` | Wheel and source distribution built successfully. |
| Archived content-addressed evidence | All 16 retained Phase 4/5 artifact hashes verified. |
| Retained Phase 5 snapshot | All five evidence events and the retained anchor verified. |

Recorded provider spend is **$0**. No live Meta or Baseten inference call has been verified. Local tests, real source retrieval, live inference acceptance and production readiness are separate qualifications.

## What still needs to be done

| Priority / phase | Remaining implementation | Required acceptance evidence |
|---|---|---|
| **Next: Phase 6 — Branching discovery** | Persistent hypothesis trees, parent/child history, evidence-driven revision, controlled mutation, candidate ranking, diversity-aware allocation, exploration/exploitation controls, duplicate enforcement and loop/stopping rules. | Explore multiple directions within limits; reject repetitive work; demonstrate a failed hypothesis followed by a justified revision. |
| **Phase 7 — Commercial validation** | Target-user and buyer models, problem severity, alternatives and competition, adoption constraints, buyer reachability, external demand/payment evidence, and enforced evidence levels 0–4. | A technically successful candidate remains commercially unvalidated without qualifying external evidence; synthetic customers cannot raise its level. |
| **Phase 8 — Extended operation** | Durable scheduling and sub-jobs, bounded concurrency, resource/status monitoring, interruption reconciliation, graceful shutdown, and pause/cancel behavior during active work. Existing provider circuits and workflow controls need integration into sustained operation. | Extended bounded runs survive interruptions and respect limits; budget exhaustion stops gracefully; unfinished work is reconciled without silent duplication. |
| **Phase 9 — Monitoring and human controls** | Research monitoring dashboard; active task/discovery views; hypothesis trees; evidence and evaluation status; spend/resource views; human approval interfaces. Evaluate optional remote workers and specialized execution separately. | Operators can inspect and control real persisted research through the interface, including approvals, without relying on raw logs. |
| **Across remaining phases** | Generalize hypothesis and experiment contracts beyond the current encoding family; add reviewed experiment implementations and evaluators for additional research questions while retaining isolation and provenance. | Demonstrate substantive research and experimental capability across different problem types; changing the demo's topic label is insufficient. |
| **Qualification and final audit** | Authorized live-provider tests with current model/pricing/capability configuration; remaining required end-to-end scenarios; fresh-agent recovery audit; complete requirement-by-requirement release review. Confirm hackathon rules only if submission is pursued. | Explicit evidence for every non-deferred requirement, with local, live-integration and production readiness reported separately. |

## Current limitations

- **Experiment scope:** execution and executable hypothesis contracts currently support only reviewed `encoding-v1` experiments. The full cross-industry research mission has not yet been demonstrated.
- **Research depth:** metadata search is bounded; synthesis and conflict detection are basic. Method mentions and title matches do not establish experimental findings, exhaustive prior-art coverage or novelty.
- **Commercial capability:** lifecycle schemas prevent some unsupported assertions, but the full commercial module and evidence collection workflow are still pending.
- **Execution backend:** native confinement was verified on this macOS host. It uses deprecated/private Seatbelt facilities; other platforms fail closed. It is not a production arbitrary-code sandbox. Memory enforcement uses RSS polling and can observe brief sampling overshoot.
- **Recovery scope:** completed committed stages are preserved. Interruptions during unfinished computation can require recomputation; durable sub-job reconciliation belongs to Phase 8.
- **Release status:** no live inference acceptance, production deployment, commercial validation, or hackathon eligibility is established. No merge or deployment has been performed.

There is no current blocker to the next local implementation task. The next action is Phase 6: implement persistent, bounded branching and failure-driven revision, verify it, then proceed through the remaining phase gates. Detailed work remains tracked in [TASK_LEDGER.md](TASK_LEDGER.md); recovery instructions are in [HANDOFF.md](HANDOFF.md).
