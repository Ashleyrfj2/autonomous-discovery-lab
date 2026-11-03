PHASE: 4
STATUS: LOCALLY_VERIFIED

IMPLEMENTED: Strict raw-result/byte/case schemas; v2 preregistered worker/fixture/evaluator SHA-256 identities; independent baseline/held-out reference recomputation; code-change refusal; deterministic per-case thresholds, repeated seeds, bounded-fixture uncertainty and failure analysis. Evidence-chain verification now reconciles mutable step projections against their authoritative events before recovery or reporting.

VERIFIED: Sixteen adversarial mutations rejected: model success/metric/critic claims, missing cases, duplicated IDs, corrupt/negative/bool/nonfinite bytes, oversized encodings, wrong plan/replication/code, invalid rows and infinite timing. Opposite data profile fails despite exact reconstruction. Persisted step-output tampering is detected against its hash-chained event. Two replications preserve raw artifacts and independent evaluations.

TESTS: uv run pytest -q: 55 passed; Ruff passed; Pyright 0 errors; uv build wheel/sdist passed; v2 demo completed locally with no provider spend

FILES: experiments/{contracts,runner,evaluator}.py; evidence/chain.py; orchestrator/lab.py; tests/adversarial/test_evaluation_manipulation.py; tests/unit/test_hypotheses.py

DECISIONS: DEC-008: v2 preregistration records code identity and strict result provenance

BLOCKERS: No local blocker. Live providers remain unauthorized/unverified.

LIMITATIONS: Evaluator covers the reviewed encoding experiment family and finite synthetic fixtures, not universal scientific verification. Archived phase-3 v1 evidence remains historical; v1 plans cannot execute under v2 code without explicit redesign/reverification. Phases 5–9 remain.

LAST VERIFIED COMMIT: commit containing this phase report (git log --grep="phase 4"); previous verified head 7249653478197c5bb3d0e12635a4c7991712a4f5

NEXT TASK: P5-RESEARCH: safe bounded real-source retrieval, metadata/provenance, source comparisons, contradictions, knowledge and claim invalidation
