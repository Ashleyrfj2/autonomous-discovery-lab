# Long-session readiness · 2026-11-04

## Baseline and implementation

Branch `integration/long-session-readiness` starts from published research-quality
HEAD `40d88cf15ae3752412fb851402b96f4ccc5596af`, which contains verified
implementation `0d1e3ace4be01e0cdfa99a8dfc7d73bc67488a31`. The original
worktrees and accepted artifacts were preserved. PR #2 remains an open draft.

Verified implementation commit: `7e1720e8f38b3b613e42ec4242fd84d3a7517956`

The existing experiment queue advances reviewed Lab stages. The new foreground
controller composes existing Discovery-v2 runs, using SQLite events, run
leases, transactional request reservations, the source catalog and
content-addressed packets. It introduces no background service. A branch
receives a rotating research objective and at most three evidence-linked notes
from prior branches. Model-suggested priority uses value, uncertainty and
effort, and candidate admission also prefers available evidence. The lanes
ask for information gain, consequential problems, feasibility, comparator
quality and diverse sources. The planner's judgments are advisory.

The session records normalized query identities before retrieval, groups
similar mechanisms and problems before critique, and allows one revisit of a
similar proposal when distinct substantive evidence supports it. Candidate
similarity is lexical and misses some paraphrases. The progress calculation
tracks new publication and excerpt fingerprints, distinct provisional
candidates, negative outcomes, repeated queries and source failures. Different
wording alone does not increase the reported source count when the captured
publication and passage match. Stagnant branches can close and the next branch
can choose another direction. Both the full sources and the scored child
packets remain available for audit.

The controller admits branches against whole-branch request, token and optional
aggregate cost envelopes. It records model calls and reasoning accounting in
the existing reservations. A paid request already in flight may finish after
a local stop. Any uncertain or abandoned reservation blocks further dispatch
and automatic resume. The optional aggregate ceiling is disabled in both
shipped profiles. The existing dollar-cap removal remains in effect.

## Research quality

The previous 12-case offline A/B/C comparison was rerun in the focused suite.
Critical false acceptance stayed 0/6, 4/6 and 0/6 respectively, and all three
retained the four positives. There is still no demonstrated scientific
advantage over A. See the [original comparative results](../research_quality/BENCHMARK_V1.md#executed-offline-comparison--2026-11-04).

The authentic historic cell and wear packets remained replayable byte for byte.
The saved cell citations bind to metadata and supply no empirical survival
evidence. The rock passage reports the phyllite measurement context and
supports only a provisional transfer to machinery. This task confirmed the
structural checks and prepared semantic adjudication. A later reviewer must
assess causal claims, contextual negation, actual comparator adequacy and
equivalence of proposed mechanisms to prior work.

The blinded packet generator combines the eight existing SciFact cases, four
additional previously unused development items (53, 56, 57 and 115), and two
historical candidate packets. It pins the upstream release digest, randomly
orders opaque candidate IDs, and emits passages, claims, comparison details,
a scoring rubric and answer form. Gold labels and condition/lineage information
are written to a separate restricted-directory map. The generated packet and
answer form have 14 matching IDs. Share those two files with the reviewer and
keep the map separate until scores are locked. The original passages and
independent upstream labels establish a semantic reference for SciFact. Actual
blinded review of model claims remains pending. [SciFact source](https://aclanthology.org/2020.emnlp-main.609/)

```sh
uv run python scripts/prepare_semantic_review.py \
  --scifact ../integration/runtime/research-quality/scifact-data.tar.gz \
  --historical-root ../integration/runtime/research-quality/historical-retry \
  --output runtime/session-readiness/blinded-review
```

Use a new output directory if rerunning. Additional Discovery packet exports
can be included with repeatable `--packet FILE` flags. These artifacts and
original accepted runtime data remain outside Git.

### Component ablations

The tests isolate one component on matched scripted cases. The selected
missing-link and missing-bridge variants of positive controls deliberately
remove required fields. Costs below are scripted call counts. Each response
reports 100 input and 80 output tokens, and there were zero billable calls.

| Component ablated | Full → ablated calls across matched cases | Observed effect |
| --- | ---: | --- |
| Atomic extraction replaced by direct spans | 10 → 7 | Same accept/reject behavior on two positives and title metadata. This small sample showed an equivalent simpler control. |
| Claim link check | 5 → 6 | An empirical assertion with no finding ID advanced after the ablation supplied a fallback ID. The foreign-source guard still rejected its case. |
| Mechanistic bridge requirement | 6 → 7 | A cross-domain candidate missing its bridge advanced. The separate established-advantage gate still rejected superiority. |
| Targeted recovery | 9 → 6 | The valid POS-04 revision was lost, while the title-only negative stayed rejected. |
| Independent critique | 15 → 9 | A negated claim advanced. The scripted prior-art signal was held fixed. The material objection that drove POS-04 recovery was also lost. |
| Prior-art check | 11 → 11 | A known equivalent advanced and both prior-art signals disappeared. |

The ablations establish fixture-specific behaviors. They do not determine
optimal model cost or semantic performance on live questions. Scientific
validation remains external, novelty unverified and commercial level zero.

## Offline execution and fault recovery

| Check | Evidence |
| --- | --- |
| Accelerated four-hour profile | Virtual clock crossed 14,400 seconds. Two concurrent workers executed distinct branches, with bounded historical context, multiple completed packets, at least one valid critique, duplicates and deadline termination. |
| Fresh process dry run | Four completed branches, one provisional candidate and one critique. Seven duplicate queries and two duplicate candidates avoided repeated downstream work. Eleven mock requests, 1,100 input and 880 output tokens, 165 reported reasoning tokens, zero unresolved reservations and $0. |
| Real wall-clock process soak | 12.02 seconds across 33 fresh CLI processes, 132 completed branches and 363 mock requests. All runs stopped normally. |
| Known failures | A malformed response closed one branch without corrupting a subsequent branch. A known-zero rate failure retried within its allowance. Source retrieval failures were isolated. Consecutive errors and stagnation stopped further exploration. |
| Separate-process controls | An in-flight scripted request reached a checkpoint after a pause request. A second coordinator could not claim the active session. Resume reconstructed the existing branch without repeating dispatch. Cancel prevented continuation. |
| Abrupt exits | Tested crash after provider settlement before plan checkpoint, after child completion before the parent receipt, and during an unresolved dispatch. Cached state resumed with identical request totals. The unresolved case retained one `RESERVED` row, refused resume and issued no additional call. |
| Ambiguous timeout | Preserved an `UNCERTAIN` row and stopped admission. |
| Launch path with HTTP mock | Both exact authorization flags, strict wire requests and live-path configuration exercised. Qualification paused after branch one and resumed. Seven mock requests reported 105 reasoning tokens and $0.00479 in simulated tariff accounting. No real inference occurred. |

Child stage checkpoints are persisted immediately. Session checkpoints also
record branch closure, pauses and terminal state. Read-only dossiers use
packet hashes and the same evidence verification as standalone replay.

## Verification and provider status

| Check | Result |
| --- | --- |
| `uv run ruff check .` | Passed |
| `uv run pyright` | 0 errors, 0 warnings |
| `uv run pytest -q` | 324 passed with historical and SciFact inputs. One existing Starlette/httpx deprecation warning. |
| Focused session, discovery, source, quality and provider suite | 134 passed |
| `uv build` | Wheel and source distribution built |
| Existing provider and scheduler regression scope | Concurrent dispatch, retry, cancellation, token accounting, redaction, crash recovery and both reviewed experiment families passed in the full suite |
| CLI smoke | Preflight, dry run, authorization refusal, start through HTTP mock, status, pause, resume, cancel, report and historic replay passed |
| Read-only Meta catalog | All three configured model IDs returned healthy through authenticated GET. This verifies visibility only. |
| Real public-source capture | Six bearing-monitoring records, three substantive, zero retrieval errors on the probe. No model call. |

```sh
export ADL_HISTORICAL_DISCOVERY_ROOT=../integration/runtime/research-quality/historical-retry
export ADL_SCIFACT_ARCHIVE=../integration/runtime/research-quality/scifact-data.tar.gz
uv run ruff check .
uv run pyright
uv run pytest -q
uv run pytest -q tests/integration/test_research_session*.py tests/integration/test_discovery.py \
  tests/integration/test_research_quality*.py tests/unit/test_research_quality.py \
  tests/integration/test_providers.py
uv run pytest -q -s tests/integration/test_research_session_ablations.py
uv build
```

The authenticated catalog and a public retrieval probe were the only application
network checks. Zero paid inference requests ran. No long session was launched.
Gross configuration estimates are $1.45552 for 20 attempts and 531,200 tokens
in qualification, and $46.57664 for 640 attempts and 16,998,400 tokens in the
four-hour profile. The estimates use standard Meta rates and include configured
completion limits. They do not substitute for provider billing.
[Meta catalog](https://dev.meta.ai/docs/api-reference/models/list-models) ·
[Meta pricing](https://dev.meta.ai/docs/pricing-rate-limits)

## Recovery and decisions

The durable boundary log and checkpoints are under `runtime/logs/` and
`runtime/checkpoints/`. Exact local outputs are retained in
`runtime/session-readiness/`. Restore the checked-out branch, then follow the
[operator runbook](../LONG_SESSION_RUNBOOK.md). The next external action is
operator-authorized short Meta qualification, including pause/resume, real
retrieval and cache-only child replay. Human semantic scoring can proceed in
parallel. No unattended scheduling was enabled.

| Readiness | Verdict |
| --- | --- |
| Controlled live qualification | **GO** for an operator who explicitly supplies authorization and the verified Meta environment. Live inference itself remains pending. |
| Supervised four-hour session | **CONDITIONAL GO** after the controlled real-provider pathway and billing reconciliation pass. Local limits and recovery are verified. |
| Fully unattended overnight | **NO-GO** pending supervised live operating evidence, billing reconciliation and unresolved-reservation operating procedures. |
| PR #2 merge | **NO-GO**. The draft remains separate and unmerged. |

Provider availability and schema behavior can change. Catalog access does not
prove that a real Discovery-v2 response fits the configured completion cap.
A supervised run may stop early for repeated evidence, a provider error
boundary or lack of useful hypotheses. The four-hour limit is an operating
bound, not a discovery target. Blinded semantic review, field experiment
validation and genuine demand evidence remain separate.
