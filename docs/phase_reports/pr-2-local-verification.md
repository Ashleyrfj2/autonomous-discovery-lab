# PR 2 local verification

## Checkout and baseline

- Repository: Ashleyrfj2/autonomous-discovery-lab. Branch and PR 2 head both resolved to `eec42c4d1c97f928feefcae7424498223ecfbff4`.
- Original checkout: `/Users/ashley/Code/autonomous-discovery-lab` on `main` at `85fedd8`, with untracked `docs/PROJECT_STATUS_REPORT_.md` (SHA-256 `d530e081360309619ef62badb5006c8446a3b70525ca09f727f2bbec4b34b8ed`). Created a clean linked worktree on the requested branch. PR 1 remains separate.
- Environment: Darwin arm64 27.2, CPython 3.12.15, uv 0.13.1. `uv sync --locked` exited 0. Raw command transcripts and runtime roots are ignored local evidence.
- Examined AGENTS, charter, traceability, architecture, handoff, ledger, decision log, registered-experiment and evaluation protocols, release readiness, and original branch phase report. Inspected the fetched branch diff and PR Git ref. GitHub CLI metadata was unavailable without authentication.

| Baseline command at `eec42c4` | Exit | Result |
| --- | ---: | --- |
| `uv run ruff check .` | 1 | I001 unsorted imports and UP040 legacy type alias in registry.py |
| `uv run pyright` | 1 | 9 errors, 0 warnings. Registry passed optional family name, encoding test used a union without narrowing, and team/portfolio tests indexed object-typed values. |
| `uv run pytest -q tests/integration/test_registered_experiments.py tests/unit/test_model_team_portfolio.py` | 0 | 14 passed, 0 failed, 0 skipped |
| `uv run pytest -q` | 0 | 189 passed, 0 failed, 0 skipped. One existing Starlette TestClient deprecation warning. |
| `uv build` | 0 | Wheel and sdist built |
| `uv run autodiscover --root runtime/audit-encoding demo` | 0 | Run `dfd33efb-5d34-4cab-b2e4-454b539ee26e` |
| `uv run autodiscover --root runtime/audit-allocation allocation-demo --topic "regional resource allocation" --algorithm dynamic` | 0 | Run `c38c3544-4896-40b1-95fa-c9912e628bac` |
| `uv run autodiscover --root runtime/audit-greedy allocation-demo --topic "regional resource allocation" --algorithm greedy` | 0 | Run `8264a3d7-1301-4295-a214-b7c31f55e4c0` |

## Audit checkpoint

- AUD-001 confirmed. Branch-introduced lint and type failures.
- AUD-002 under test. Preregistered evaluator hash was unchecked at preflight, and requested replica indices were not bounded by the plan.
- AUD-003 under test. Greedy evidence can substitute optimum selections, and allocation branch results are not tied to a completed job of the same run.
- AUD-004 under test. Provider response identity and source context need tests for route mismatch and source selection changing between reads.
- AUD-005 under test. Portfolio subtraction can round away a cost or time charge at a budget boundary.

At `da1e5eff9887878402652727fc4705e13211f315`, Ruff, Pyright, build, 21 focused tests and 201 full tests passed. Native CLI inspection showed the dynamic candidate correctly receives two credits under the default Director quota. Inspection of both preregistrations exposed AUD-006. The second allocation replayed the exact first replication's fixtures because the Director's ordinal seed increment equaled the replica seed increment. The targeted regression reproduced with 1 failure and 9 deselected. Both runtime roots and the failing transcript were retained.

## Findings and repairs

No Critical findings. The following issues were repaired.

| ID | Severity | Confirmed defect and repair | Regression evidence |
| --- | --- | --- | --- |
| AUD-001 | Low | Ruff import and type-alias findings plus nine Pyright findings. Updated the registry and narrowed test values without removing assertions. | Final Ruff exit 0 and Pyright exit 0 with 0 findings. |
| AUD-002 | Medium | Preflight omitted evaluator identity and accepted malformed in-memory plan fields. The registry now validates the matching plan class and checks all three fixed code hashes. Runner and job admission reject replica indices outside the plan. | Wrong evaluator, wrong plan class, excess memory, filename injection, unknown family and replica 3 of a two-replica plan reject. |
| AUD-003 | High | Optimal selections relabeled as greedy could pass, and the Director accepted allocation evidence from a different run. The independent evaluator now checks the declared greedy selection and rejects invalid replicas. The Director binds allocation reports to completed same-run job evidence. | Rejected relabeled output, cross-run evidence, duplicate/overweight indices, injected success, wrong case ID and digest mismatch. |
| AUD-004 | High | A second source selection could include unchecked private material. Provider responses could name a different model and still be accepted. Source rendering now uses the checked IDs, commit checks run ownership and validity, and routing rejects mismatches while settling usage. Review packets are sanitized and their hashes checked by chain verification. | Mock private-source selection race, mismatched route, credential checks, invented references, invalid verdicts, one-event replay, no jobs or stages, and tampered review artifact. |
| AUD-005 | Medium | Binary subtraction rejected a candidate that fit the stated decimal time limit. Decimal precision could also round away a small charge. Time admission is exact for the decimal representation of input seconds, and money is bounded to nine whole and nine fractional digits. Exclusions have stable ordering. | Fractional boundary, uncertainty ranking, duplicate/provenance checks, sub-nanodollar rejection, and a read-only CLI run. |
| AUD-006 | Medium | Two durable allocation rounds used overlapping fixture streams. Allocation plans now use distinct ordinal seeds below the fixture replication stride. | `uv run pytest -q tests/integration/test_registered_experiments.py -k repeated_allocation` exited 1 before the fix with 1 failed and 9 deselected, then exited 0 with 1 passed and 9 deselected. |

Repair commits are `da1e5eff9887878402652727fc4705e13211f315` (AUD-001 through AUD-005) and `3e95766904d289077f05d703d8f2f0a123576711` (AUD-006). Source and test manifest from `git ls-files -s -- src tests uv.lock pyproject.toml | shasum -a 256` is `5c981d095b276a1d34553cbcebbdae18b3285fd87c70d5f6fbe771307b6df507`.

Files examined include `experiments/{registry,runner,allocation_worker,allocation_contracts,allocation_fixtures,allocation_evaluator,contracts,worker,datasets,evaluator}.py`, `orchestrator/{lab,jobs,store,durability}.py`, `hypotheses/{allocation,director,portfolio,proposals}.py`, `models/{teams,router,providers}.py`, `research/catalog.py`, `evidence/{chain,artifacts,branches,jobs}.py`, `security/{budget,redaction,processes}.py`, `cli.py`, and related tests and retained Phase 8 evidence.

Regression sequence recorded under `runtime/pr-2-audit/`:

- The focused command at the fetched head with seven new regressions exited 1 with 7 failed and 14 passed. Diagnostics are in `audit-repro.log`.
- The first combined regression run exited 1 with 1 failed and 42 passed. The failure was a test matching Pydantic's decimal-place message when its total-digit check fired first. Matching the rejected field preserves validation. `repair-focused.log` retains the diagnostic.
- `uv run pytest -q tests/integration/test_registered_experiments.py tests/unit/test_model_team_portfolio.py tests/integration/test_durable_jobs.py tests/integration/test_experiment_runner.py tests/end_to_end/test_research_loop.py tests/integration/test_providers.py` exited 0 with 62 passed before the seed fix. Allocation worker start crash was reconciled once and retried once. Pause and cancel reaped the worker without consuming a retry. Time and output limits stopped real workers, and a simulated over-limit RSS reading exercised cleanup of a real worker. Existing retry, lease and encoding recovery regressions also passed.
- The first manual evidence script assumed a single dynamic allocation and exited 1. The persisted Director history showed two credits. The final replay inspects all plans, jobs and replica artifacts. It additionally exposed the seed overlap tracked as AUD-006.

## Final verification at `3e95766904d289077f05d703d8f2f0a123576711`

| Exact command | Exit | Result |
| --- | ---: | --- |
| `uv run ruff check .` | 0 | All checks passed |
| `uv run pyright` | 0 | 0 errors, 0 warnings, 0 informations |
| `uv run pytest -q tests/integration/test_registered_experiments.py tests/unit/test_model_team_portfolio.py` | 0 | 22 passed, 0 failed, 0 skipped, 22 total |
| `uv run pytest -q` | 0 | 202 passed, 0 failed, 0 skipped, 202 total in 19.15 s |
| `uv build` | 0 | Wheel and sdist built |
| `uv run autodiscover --root runtime/audit-qualified-encoding demo` | 0 | Technical pass, 1 primary and 2 replications |
| `uv run autodiscover --root runtime/audit-qualified-allocation allocation-demo --topic "regional resource allocation" --algorithm dynamic` | 0 | Technical pass, 2 primaries and 4 replications |
| `uv run autodiscover --root runtime/audit-qualified-greedy allocation-demo --topic "regional resource allocation" --algorithm greedy` | 0 | Negative control completed with a failed technical evaluation and retained evidence |
| `uv run autodiscover --root runtime/audit-planner-unused portfolio-plan runtime/pr-2-audit/portfolio.json` | 0 | A and B selected within $0.10 and 0.3 s. C excluded. Execution authority false and root absent. |
| `uv run python runtime/pr-2-audit/verify-runs.py` | 0 | 10 fresh result artifacts independently replayed and 24 historical reports recomputed |

The sole full-suite warning was the pre-existing Starlette TestClient deprecation for `httpx`. The final CLI status, tree, and jobs commands used each actual run ID. All three exited 0 for each run. The commands `uv run autodiscover --root runtime/audit-qualified-<name> snapshot runtime/pr-2-audit/qualified-<name>-snapshot.json` and `uv run autodiscover --root runtime/audit-qualified-<name> integrity --anchor runtime/pr-2-audit/qualified-<name>-snapshot.json` each exited 0 for `encoding`, `allocation`, and `greedy`.

| Run | ID | Held-out evidence | Chain |
| --- | --- | --- | --- |
| Encoding | `a7b1944e-f1da-48cf-8ffe-bd20cfaf8eca` | 48 held-out cases per job. Minimum savings 82.03%, 82.81%, and 84.38%. | 35 events, anchor `7271977e97f19a3d6628bbf9c7f4a8cd77b16444d94e8f43bb14b25e48ff9123` |
| Allocation dynamic | `f5d00ece-98e3-445f-ac59-08785b5c4653` | 12 held-out cases per job. All 72 hit exact optimum 20. Greedy references were 13, 14 or 15, with minimum normalized gain 25% against 15% required. Two rounds each retained both replications. | 54 events, anchor `293a14ae5167a4ce3e3a95f892ffcfc9f18c3194909f0a040906afc759e76a62` |
| Allocation greedy | `813398e0-a1ad-48c3-b12a-ce3a0b103cfe` | 12 held-out cases. Zero gain, failed verdict, retained raw and report. No replication or market stage was reached. | 19 events, anchor `3036ce9da9f236109ff09036823d32e3e6a7025c58c81fb101f437b837389adf` |

Raw evidence has macOS Seatbelt provenance, native worker PIDs, matching preregistration and job digests, distinct fixture streams for each dynamic round and replica, and matching worker, fixture and evaluator hashes. A bit-mask enumeration and exact-ratio greedy recomputation corroborated the allocation evaluator. Novelty remained unknown in all three runs. Positive runs had commercial level 0 and no external validation. All runs settled $0. Encoding made one local mock request. Allocation made zero model requests. A separate mock team replay produced one review event across four mock requests with $0 charged and no experiment admission.

The retained historical Phase 8 snapshot verified 712 events and 73 artifact digests. All 24 archived encoding reports recomputed against their original preregistrations. Encoding contract, fixture, worker and evaluator Git blobs match main. Director orders allocation counts and family before within-family score, and the cross-family test exercises both plans in the same search.

A separate clean local clone at the same SHA repeated locked environment sync, Ruff, Pyright, the full suite, the build and all three CLI commands with exit 0. The clone had 202 passes, 0 failures, 0 skips and the same warning. The three clone run IDs were `141bfe9e-1492-4e07-b4f7-87c26374c25d` (encoding), `2244468a-24e3-4844-9a6f-84ce24978f6f` (dynamic), and `a3284dd6-64ea-46f7-a58d-3f4a17a6bca0` (greedy). The respective chain counts were 35, 54 and 19.

## Remaining limits

- The qualification covers reviewed local workers under macOS Seatbelt. Darwin RSS monitoring samples usage, and the forced over-limit observation was simulated. A production isolation assessment requires a separate runtime and threat-model qualification.
- Allocation fixtures share the same synthetic trap structure. Independent seeds establish repeatability for this protocol. Broader conclusions require separately preregistered representative cases.
- Pre-repair allocation plans retain their original artifacts and evaluator identity. Fresh execution or re-evaluation under the repaired protocol requires fresh preregistration. Historical encoding evidence remains compatible.
- The portfolio accepts a syntactically valid calibration digest as a reference supplied by the caller. Authenticating calibration evidence would require a trusted artifact source before any production use of those estimates. The planner is advisory.
- Provider role behavior was tested with mocks. Live provider identity, alias behavior, pricing and sharing policy require separately authorized qualification. Novelty and external demand require their own evidence.

**LOCALLY VERIFIED** for the requested scope. No local blocker remains. Ready for human review.
