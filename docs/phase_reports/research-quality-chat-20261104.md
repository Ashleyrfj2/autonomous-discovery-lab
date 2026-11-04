# Chat-mode research quality v1 — implementation checkpoint (2026-11-04)

Status: **OFFLINE IMPLEMENTATION COMMITTED ON ISOLATED BRANCH; NOT WIRED TO LIVE DISCOVERY**.

## Repository authority

- New isolated branch: `chat/research-quality-v1-20261104`.
- Branch derived from remote `chat/registered-experiments-20261103` at `9bbf427c2d69a688d73db7b4e81303867ac6fa74`.
- The later user-reported local run commit `72304b5` is **not available on the remote**. We did not modify PR #2, main, live checkpoints, existing budgets or runtime evidence.
- Source: `src/autodiscover/research/quality.py`.
- CLI: `src/autodiscover/research/quality_cli.py`.
- Tests: `tests/unit/test_research_quality.py`.
- Specs: `docs/research_quality/EVIDENCE_FIRST_V1.md` and `docs/research_quality/BENCHMARK_V1.md`.

## What was implemented

1. Five versioned instruction strings: source finding extraction, cross-domain bridge analysis, hypothesis author, independent critic and recovery controller.
2. Typed `AtomicFinding` and `MechanismBridge` contracts; claim flags preserve experimental status.
3. Offline `screen_evidence`: fail closed for invalid source, invented quote, title-only evidence, wrong access level, reused IDs, unknown bridge IDs and unjustified cross-domain superiority.
4. Offline `decide_recovery`: hard invalid claims reject, distinct new evidence required to revise, query loops and exhausted revisions end inconclusively.
5. Offline CLI emits only status/codes, not source passages. No retrieval, inference or event ledger mutation.
6. Focused tests cover both reported failure patterns **using synthetic stand-ins**, not the actual user run packet.

## Verification boundary

- **20 focused tests passed (initial and post-format isolated runs; final command used `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` to disable unrelated globally installed pytest plugins)** on isolated Python 3.13/Pydantic 2.x in this chat's container with contract stand-ins matching the remote `Citation`, `Evidence` and `Record` fields; local Python compileall also passed.
- Long lines were adjusted to at most 100 characters in the committed files.
- This is **not** the full repo's Python 3.12/uv/Ruff/Pyright/full pytest/build acceptance. Those remain unexecuted.
- Source files were fetched back from GitHub and confirmed present. No CI outcomes are used as proof.
- Semantic support, external prior-art equivalence, source ownership rechecks and real commercial evidence **remain distinct human/independent gates**.

## Before any merge or live wiring

1. On the Mac, inspect `git status`, preserve local commit `72304b5` and immutable original packet.
2. Integrate or cherry-pick only after reconciling with the newer local code; do not overwrite PR #2.
3. Run `uv run ruff check .`, `uv run pyright`, `uv run pytest -q tests/unit/test_research_quality.py`, `uv run pytest -q`, `uv build` and record exact SHA and outputs.
4. Reconstruct actual run failures using archived source snapshots; do not treat synthetic fixtures as the live transcript.
5. Wire source-bound finding extraction and review as immutable checkpoints, retaining existing catalog ownership/digest validation and zero-dispatch replay behavior.
6. Perform frozen A/B/C comparative evaluation with independent semantic annotations. No billable calls without explicit permission.

**Current live qualification:** unchanged. **Novelty:** unverified. **Commercial validation:** level 0. **PR #2:** unmerged. **Overnight operation:** not qualified.

Recovery: read the two `docs/research_quality` files, this report and actual local `AGENTS.md`, `docs/HANDOFF.md`, live packet and git history. Related [Notion handoff](https://app.notion.com/p/40eec84d128b8133a0cbc94fb267d760?pvs=204).

## Integration and local verification

Branch `integration/research-quality-v1`. The tested implementation is
`0d1e3ace4be01e0cdfa99a8dfc7d73bc67488a31`. Integration merge
`5e04c23f50e47513a03db56f479014763e0f84c4` preserves both exact parents.

| Input | Commit | Disposition |
| --- | --- | --- |
| Latest local live-research checkpoint | `72304b5d9b53cb96c742b2554ccabcb74f9718fe` | Used as the first parent. It adds the historical live-run receipt to the published live implementation. |
| Published Chat research-quality v1 | `e11b2fe9bf268a21841a29000b4aa84d478854ce` | Merged without file conflicts. Six added files supply the offline module, CLI, tests and specifications. |
| Shared base and PR #2 remote head | `9bbf427c2d69a688d73db7b4e81303867ac6fa74` | PR #2 remained open, draft and unmerged. |
| Local and remote main | `85fedd8b854393096a77a065461fbb69eb1dd0bb` | Main's untracked `docs/PROJECT_STATUS_REPORT_.md` remained in its original worktree. |

Reconciliation found no newer local commit on either worktree. The older
prior-art qualification branch remains separate. The integration worktree
contains no credentials or accepted runtime records. The original PR #2
worktree and its ignored runtime were preserved.

### Implementation and phase boundaries

| Boundary | Evidence and next action |
| --- | --- |
| Reconciled at merge `5e04c23` | Compared both local worktrees and upstream refs. The imported baseline passed 281 tests and built. Pyright found three type errors in the imported fixture factories. Next action was wiring the quality module. |
| Protocol wired | Added versioned extraction, findings, claims, bridge, advisory critique, typed recovery and packet traces to discovery. Fixed fixture annotations. The first focused run passed 36 tests. Next action was authentic replay and fixture comparison. |
| Sentinels and history | Ran A/B/C through the frozen harness and both authentic historical cases. Fixed the typed packet projection when replay exposed a mismatch between extended and compatibility review fields. The nested strict schema was then scoped to v2 responses after two existing research-team wire tests caught a broad normalization change. Next action was full verification. |
| Verified at `0d1e3ac` | All applicable checks passed. Next action is blinded semantic assessment and preregistration of any authorized live trial. |

The atomic checkpoint and sanitized append-only boundary log are under
`runtime/checkpoints/development.json` and `runtime/logs/development.jsonl`.
The worktree preserves detailed tool output under `runtime/research-quality/`.
Commit `0d1e3ac` contains the changed source, fixtures and tests listed by
`git show --stat 0d1e3ac`. The documentation commit records the same verified
implementation tree.

### Historical failures

Replayed original run `discovery-9d86dedf2a48c9f787c13e5284e81b1a8e38e495ccfdbdd9e435723a8f144c4e`
from a disposable copy of `runtime/discovery-live-20261103-retry` in the original
PR #2 worktree. The packet digest matched
`7259db666e6d4842df8f40eb66ab90ab07b217295812f56ab84359ffb934034e`, the
event-chain anchors remained identical and CLI replay output matched byte for
byte. Regression tests use the actual recorded citations and captured excerpts.

- **Cell preservation.** Both citations match titles within records that also
  include abstracts. The v2 screen assigns zero substantive findings to those
  spans. The missing evidence is an observed mammalian survival outcome under
  the proposed desiccation and rehydration conditions. A distinct query for
  experimental methods and outcomes can justify targeted retrieval. An
  unproductive query closes the attempt as inconclusive. A separate mock test
  exercises successful early recovery when a new substantive source appears.
- **Acoustic wear detection.** The packet contains a title-only citation and
  an abstract span about acoustic-emission measurements during uniaxial
  phyllite compression. The original proposal raised a lead-time question
  and disclaimed experimental success. It received one critic response and
  was rejected. The regression keeps the authentic record separate from
  an injected assertion of established advantage. It rejects that assertion
  and preserves a narrower, explicitly provisional bridge through damage-related
  elastic waves. A defensible comparison would pair acoustic and vibration
  alarms on the same independently labeled wear events and measure lead time
  at a fixed false-alarm rate. Load, rotational speed, lubrication and sensor
  mounting are candidate confounders. Published prior art includes turning-tool
  monitoring and bearing-rig studies with speed and lubrication effects. Those
  precedents leave the proposed field comparator and effect unverified.
  [2002 tool wear review](https://www.sciencedirect.com/science/article/pii/S0890695501001080),
  [2022 tool-condition review](https://pmc.ncbi.nlm.nih.gov/articles/PMC8950983/),
  [2021 roller-bearing study](https://wes.copernicus.org/articles/6/367/2021/wes-6-367-2021.html),
  [2025 bearing-lubrication study](https://www.sciencedirect.com/science/article/pii/S0043164825001085)

No original source artifacts, packet or evidence ledger were modified. The
historical run remains at one received critique against two required. Its
four model calls and $0.054628 in locally calculated usage are historical.

### Verification at the implementation commit

| Command or check | Result |
| --- | --- |
| `uv run ruff check .` | Passed |
| `uv run pyright` | 0 errors, 0 warnings |
| `uv run pytest -q` with historical and SciFact inputs | 302 passed, 0 failed, 0 skipped. Existing Starlette/httpx deprecation warning. |
| Focused quality, discovery, comparison, historical and holdout tests | 57 passed |
| `uv run pytest -q -s tests/integration/test_research_quality_benchmark.py` | 17 passed including 12 A/B/C cases, strict wire simulation and additional recovery and replay checks |
| `uv build` | Wheel and source distribution built |
| CLI smoke | Discovery preflight and historical replay, quality preflight, encoding demo, allocation dynamic and greedy demos passed |
| Regression scope | Reviewed experiment families, ownership, invalidation, citation binding, checkpoint resume, cancellation, concurrent dispatch, retry and accounting, credential redaction and replay passed locally |

The scripted comparison results are in the [benchmark](../research_quality/BENCHMARK_V1.md#executed-offline-comparison--2026-11-04).
A and C each had zero critical false acceptances and retained all four positive
controls. B passed four unsupported candidates. C recorded two prior-art
signals to A's one and issued 45 scripted requests to A's 35. Independent
review and paid comparison remain open, so scientific quality relative to A is
inconclusive. No actual inference provider was contacted and no model spend
occurred. Public literature and the SciFact release were consulted outside
the offline comparison.

### Recovery instructions

From the integration worktree, copy the saved live runtime from its original
location into an ignored directory. Use `ADL_HISTORICAL_DISCOVERY_ROOT` to
point at that copy. The original run location is the `runtime/discovery-live-20261103-retry`
directory within the local PR #2 worktree described in the task. Set
`ADL_SCIFACT_ARCHIVE` to a local copy of the frozen archive identified by
`tests/fixtures/discovery/scifact-dev-holdout.json`. The two optional suites
skip when those inputs are absent. For this verification both inputs were set.

```sh
uv run ruff check .
uv run pyright
uv run pytest -q
uv build
uv run pytest -q -s tests/integration/test_research_quality_benchmark.py
uv run autodiscover discover --preflight --spec config/discovery-quality-v1.json \
  --providers config/discovery-meta.json
```

The role prompts and run registration are versioned. Resume only under the
recorded protocol and model configuration. For completed packets use
`autodiscover discover --cache-only --run-id RUN_ID` against the copied root.

### Authorization boundary for a live A/B/C comparison

The offline verdict authorizes no live execution. A later authorization
request should identify frozen questions and a permitted public corpus,
the exact model routes, per-arm prompt and completion limits, retry limits,
wall-clock bounds, provider manifest, run IDs and review rubric. A live control
runner for B needs its own isolated rehearsal. To attribute workflow differences,
hold a common model identity and identical retrieval corpus for a controlled
comparison, then register a separate three-identity reviewer sensitivity run.
Use fresh context for the critic and blinded external adjudication for claim
support, prior-art equivalence and adequacy of falsifiers. Count the two-critique
shortfall explicitly if a corpus supplies fewer eligible candidates.

Current v2 preflight describes at most 10 logical calls, 20 attempts with one
retry per call, 480,000 conservative input tokens, 51,200 completion tokens
including reasoning, four searches and 240 seconds per invocation. The
configured gross estimate is $1.45552 for that single manifest and spec.
It is an estimate for review. No dollar admission caps were restored. Live
qualification also needs an actual provider wire check, provider usage
reconciliation and approved stop conditions. Overnight operation needs
separate authorization and qualification of unattended scheduling, cancellation,
budget accounting and ambiguous dispatch recovery.

| Decision | Verdict |
| --- | --- |
| Research-quality implementation | PASS locally |
| Full local regression | PASS |
| Offline comparative evaluation | PASS for fixture and replay acceptance. Generalized improvement over A is inconclusive. |
| Live A/B/C qualification | NO-GO pending live-control preparation, blinded review plan and explicit authorization |
| Overnight autonomous research | NO-GO pending live qualification, operational soak and authorization |
| PR #2 merge | NO-GO. Draft remains unmerged. |

### Specification and handoff references

[Evidence-first discovery method](https://app.notion.com/p/40eec84d128b8161aa88f88dd345414f),
[adversarial benchmark](https://app.notion.com/p/40eec84d128b81238ea4c93caa3edb1e),
[recovery anchor](https://app.notion.com/p/40eec84d128b8133a0cbc94fb267d760),
[main handoff](https://app.notion.com/p/40dec84d128b81868c97f4ca1e9bb9ed).
