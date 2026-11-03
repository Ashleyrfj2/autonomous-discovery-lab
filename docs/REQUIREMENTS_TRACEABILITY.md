# Stable requirements traceability

Origin: MASTER_REQUIREMENTS.md section numbers. No requirement is removed by summaries. Priority: P0 for safety/persistence/core, P1 for subsequent phases. Status starts NOT_STARTED; tests/evidence must identify actual files/results before VERIFIED.

| ID | Requirement | Origin sections | Phase / owner | Priority | Status | Sources | Tests | Evidence | Remaining gaps |
|---|---|---|---|---|---|---|---|---|---|
| REQ-001 | Persistent versioned research state and WAL migrations | 2,4,6,8 | 1 / orchestrator | P0 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-002 | Independent deterministic evaluation and false-success rejection | 1,7,8,12 | 4 / experiments | P0 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-003 | Source and experiment provenance; no fabricated citations | 1,7,13 | 5 / research/evidence | P1 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-004 | Meta/Baseten/mock provider-independent common contracts | 5 | 2 / models | P0 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-005 | Trusted isolated workers; no arbitrary generated code execution | 7 | 3 / experiments/security | P0 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-006 | Reservations, request/token/cost accounting, run/day budgets | 5,11 | 2 / security/models | P0 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-007 | Permanent docs, atomic checkpoints, recovery and drift audits | 2,3,14,15 | 0 / orchestrator/docs | P0 | VERIFIED (phase 0 scope) | config.py; durability.py; redaction.py; docs/* | test_foundation.py | phase_reports/phase-0.md | Later phase regression/audits remain |
| REQ-008 | Hypothesis trees, revision, controlled mutation and duplicates | 7,8 | 6 / hypotheses | P1 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-009 | Separate technical/discovery/commercial gates and levels 0–4 | 1,7 | 7 / commercial | P1 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-010 | Preregistered reproducible baselines/controls/artifacts/metadata | 7,12 | 3 / experiments | P0 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-011 | All lifecycle transitions with schemas/preconditions/errors/retries | 6 | 1 / orchestrator | P0 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-012 | Safe cancel/pause/resume and deliberate crash recovery | 3,8 | 1 / orchestrator | P0 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-013 | Idempotency, fenced worker claims, stale recovery | 8 | 1 / orchestrator | P0 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-014 | Response/schema validation, capability and structured errors | 5 | 2 / models | P0 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-015 | Timeout/rate/retry/fallback and recorded provider identity | 5 | 2 / models | P0 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-016 | No secrets; sanitized locked append-only execution JSONL | 2,3,5,14 | 0 / security/orchestrator | P0 | VERIFIED (phase 0 scope) | config.py; durability.py; redaction.py; docs/* | test_foundation.py | phase_reports/phase-0.md | Later phase regression/audits remain |
| REQ-017 | Hash-chained append-only evidence and independent snapshots | 7 | 3 / evidence | P0 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-018 | Content-addressed bounded artifacts with integrity verification | 4,7 | 3 / evidence | P0 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-019 | Evidence-to-claim relations, transitive invalidation and retrieval | 7 | 5 / evidence/research | P1 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-020 | Research questions, metadata, synthesis and knowledge retrieval | 7 | 5 / research | P1 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-021 | Source/method comparison, contradictions, novelty uncertainty | 1,7 | 5 / research | P1 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-022 | Falsifiable cross-domain proposals and explicit theoretical rejection | 7 | 3 / hypotheses | P0 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-023 | Unseen tests, independent baselines, replication and failure analysis | 7,8 | 4 / experiments | P0 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-024 | CPU/memory/time/output/network/filesystem policy enforcement | 7,11 | 3 / experiments/security | P0 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-025 | Bounded diversity/exploration/exploitation, stopping and replanning | 7,10 | 6 / orchestrator/hypotheses | P1 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-026 | Buyer/user/problem/competition/adoption/reachability models | 7 | 7 / commercial | P1 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-027 | External demand/payment evidence; synthetic evidence excluded | 7 | 7 / commercial | P1 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-028 | Durable scheduler and bounded concurrency/fault recovery | 8 | 8 / orchestrator | P1 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-029 | Circuit breakers, resource monitoring, graceful shutdown/status | 8,11 | 8 / orchestrator | P1 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-030 | Loop/error detection, bounded safe retries and cyclic-task checks | 10 | 6 / orchestrator | P1 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-031 | CLI monitoring/controls/trees/evidence/spend/human approval | 8 | 9 / reporting | P1 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-032 | Unit/integration/adversarial/end-to-end required categories | 12 | 0 / tests | P0 | IMPLEMENTED_UNVERIFIED | config.py; durability.py; redaction.py; docs/* | test_foundation.py | phase_reports/phase-0.md | Later phase regression/audits remain |
| REQ-033 | Local lint/types/package/smoke evidence; no CI-only readiness | 12 | 0 / scripts/docs | P0 | VERIFIED (phase 0 scope) | config.py; durability.py; redaction.py; docs/* | test_foundation.py | phase_reports/phase-0.md | Later phase regression/audits remain |
| REQ-034 | Full original mission and stable traceability/session handoff | 1,2,15 | 0 / docs | P0 | VERIFIED (phase 0 scope) | config.py; durability.py; redaction.py; docs/* | test_foundation.py | phase_reports/phase-0.md | Later phase regression/audits remain |
| REQ-035 | Safe env config, defaults, Python3.12/uv/modular structure | 4,11 | 0 / config | P0 | VERIFIED (phase 0 scope) | config.py; durability.py; redaction.py; docs/* | test_foundation.py | phase_reports/phase-0.md | Later phase regression/audits remain |
| REQ-036 | Current official provider docs; no hardcoded unverifiable rates/models | 5,13 | 2 / models/docs | P0 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-037 | Phase audits/reports/history/checkpoints and honest statuses | 14,15,17,18 | 0 / docs | P0 | IMPLEMENTED_UNVERIFIED | config.py; durability.py; redaction.py; docs/* | test_foundation.py | phase_reports/phase-0.md | Later phase regression/audits remain |
| REQ-038 | No external deploy/merge/spend/credential assumptions | 9,11,12 | 0 / security | P0 | VERIFIED (phase 0 scope) | config.py; durability.py; redaction.py; docs/* | test_foundation.py | phase_reports/phase-0.md | Later phase regression/audits remain |
| REQ-039 | Actual real-source retrieval acceptance separate from mocks | 8,12,18 | 5 / research/tests | P1 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-040 | Extended bounded end-to-end operation and intervention | 8,18 | 8 / orchestrator/tests | P1 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-041 | Optional dashboard/remote/specialized workers evaluated explicitly | 8 | 9 / reporting/docs | P1 | NOT_STARTED | — | — | — | Implementation and acceptance |
| REQ-042 | Hackathon eligibility unconfirmed; no deadline shortcuts | 16 | 0 / docs | P0 | VERIFIED (phase 0 scope) | config.py; durability.py; redaction.py; docs/* | test_foundation.py | phase_reports/phase-0.md | Later phase regression/audits remain |
