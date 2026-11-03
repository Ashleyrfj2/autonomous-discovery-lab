# Chat implementation handoff: reviewed experiment families and research roles

Date: 2026-11-03
Repository: Ashleyrfj2/autonomous-discovery-lab
Branch: chat/registered-experiments-20261103
Base: main @ 85fedd8b854393096a77a065461fbb69eb1dd0bb
Status: **IMPLEMENTED_UNVERIFIED; DO NOT MERGE without local qualification**

## User authorization and scope

User requested implementation of proposed experiment-plugin registry, second reviewed experiment family, multi-model research criticism and cost-aware search planning. Existing Phase9 UI remains incomplete. No secrets, cloud deployments, paid inference, physical sensors, arbitrary generated-code execution, provider spend or buyer outreach was authorized or performed. Previous draft PR #1 for the source-bound prior-art dossier is a *separate unmerged branch* and is not a dependency of these changes.

## Direct GitHub changes

- New modules: `experiments/{registry,allocation_contracts,allocation_fixtures,allocation_worker,allocation_evaluator}.py`, `hypotheses/{allocation,portfolio}.py`, `models/teams.py`.
- Existing integration points changed: `experiments/runner.py`, `hypotheses/{director,proposals}.py`, `orchestrator/{lab,jobs}.py`, `cli.py`, `reporting/{views,reports}.py`.
- Tests authored: `tests/integration/test_registered_experiments.py` and `tests/unit/test_model_team_portfolio.py`, including intentional negative/control cases.
- Protocol: `docs/REGISTERED_EXPERIMENTS.md`. Branch-specific DEC-021 and task ledger updates follow.

## Safety and compatibility decisions

- Retain existing encoding worker/fixture/evaluator source unchanged. Registry uses fixed reviewed files only.
- Allocation worker runs with existing host sandbox and resource bounds; no generated or foreign code.
- New evaluator independently enumerates all bounded subsets and checks locked held-out cases. Existing encodings keep the original evaluator.
- Prior-art and commercial classifications stay independently unknown/unvalidated. The new known algorithm does not demonstrate any novelty.
- Model critique uses three separate configured model identities, but model critique is not experimental verification. Private source text and credential-bearing prompts are blocked from automatic model dispatch.
- Cost-aware portfolio is advisory, not an execution admission mechanism, and uses provenance-discounted estimates.
- Prior raw plan/source digests remain attributed to original checked-in code; actual resumed historical run compatibility requires local regression.

## Tests and verification status

No local `uv run ruff check .`, `uv run pyright`, `uv run pytest -q`, `uv build` or macOS native-worker run could be executed through this private GitHub connector. The code and test files exist, and their commits were acknowledged by GitHub. This is NOT equivalent to tests passing.

A separate local arithmetic check of shuffled bounded allocation traps confirmed that the chosen greedy baseline is suboptimal and a dynamic-programming optimum reaches 20 on 300 generated variants. This is an **algorithm sanity check only**, not execution of the repository worker, native sandbox, database or CI.

## Exact first handoff actions

1. Inspect `git status --short --branch` and protect untracked `docs/PROJECT_STATUS_REPORT_.md`.
2. Fetch and inspect the branch, PR diff and relevant original source hashes. Do not accidentally merge the separate prior-art PR during this review.
3. Run Ruff, Pyright, two focused test modules, full pytest and package build on Python 3.12/macOS. Fix failures while preserving original encoding worker/evaluator identities.
4. Run `allocation-demo --algorithm dynamic` and negative `--algorithm greedy` on **fresh** roots. Confirm actual evidence hashes, stage transitions, replication and market level 0.
5. Test external interruption/recovery and cross-family job admission; record exact qualifying SHA, source manifest, test commands/counts and artifacts.
6. Only after local qualification make an explicit merge decision. GitHub Actions is not the acceptance gate.

## Open scope

- Actual static/type/runtime verification and any needed repairs.
- Arbitrary model-generated code: **deliberately NOT enabled**. A production-grade sandbox is a separate high-risk design.
- Third or later experiment families, physical sensors, cloud inference and calibrated cost models: not claimed.
- Existing Phase9 dashboard/12ui conversion and browser gate: remains incomplete.
- Scientific novelty, independent publication review and real commercial buyer evidence: NOT established.

## Context recovery

Read `AGENTS.md`, `docs/PROJECT_CHARTER.md`, `docs/HANDOFF.md`, `docs/REGISTERED_EXPERIMENTS.md`, this report, `docs/DECISION_LOG.md`, `docs/TASK_LEDGER.md`, and the current draft PR. Never infer production readiness or scientific success from a synthetic test or a remote GitHub commit.

Follow-up code-review improvement: research-team output is retained in the existing local artifact store with an append-only non-authoritative event, replay deduplicated by digest. Source validity is rechecked at event commit. An additional unit assertion for readback/idempotent replay is authored but not locally run.
