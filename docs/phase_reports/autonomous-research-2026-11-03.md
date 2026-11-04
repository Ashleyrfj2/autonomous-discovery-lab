# Autonomous research qualification · November 3, 2026 (America/Chicago)

## Recovery anchor

Use the existing PR #2 worktree and branch `chat/registered-experiments-20261103`. The starting remote and local HEAD was `5b07c70d8b4c81c2a2565fd81359e8b6d6cf1386`. The previously uncommitted Meta qualification was checked and committed as `839efd0221b8c0d96e8e9b89617433ed84d3acab`. GitHub's read-only PR metadata confirmed open draft, unmerged, with remote HEAD still at the starting SHA. Local commits are retained in the worktree. The separate main worktree's `docs/PROJECT_STATUS_REPORT_.md` retained SHA-256 `d530e081360309619ef62badb5006c8446a3b70525ca09f727f2bbec4b34b8ed`.

Start with this report, the branch's latest two commits, and `runtime/checkpoints/development.json`. The durable development evidence root is `runtime/autonomous-research-CTehXZ`. The prior Meta qualification archive remains at `runtime/meta-live-qualification-R29YYC`. Its four settled live calls used 1,994 input tokens and 1,998 output tokens and recorded $0.02431875 in locally calculated standard-rate usage. This phase incurred zero inference charges and made zero live inference requests.

### Checklist

- [x] Verify, scan, and commit the prior live baseline.
- [x] Compare research methods and register the bounded protocol.
- [x] Implement planning, retrieval, proposal, adversarial review, adaptive revision, gates, and packet replay.
- [x] Exercise the baseline and challenge controls, process death, and read-only replay.
- [x] Verify real public retrieval separately from model mocks.
- [x] Record live preflight, evaluation criteria, and operational gaps.
- [ ] Obtain authorization for and run the new foreground live experiment.
- [ ] Score live output independently and assess whether another run is warranted.
- [ ] Qualify scheduling and long-horizon operation before unattended inference.

The 247-to-245 baseline change removed two obsolete cap-enforcement tests. They asserted that a run pauses on cost overrun and that an individual request cannot consume another candidate's dollar allocation. Existing replacements cover legacy-cap compatibility, preserved charged usage after overrun, duplicate requests, cross-process reservations and cache behavior. The scheduler guard now stops on unresolved requests. The 245-test baseline was independently rerun.

## Research methods and decisions

Public sources consulted November 3, 2026. The designs below informed implementation choices. They do not predict comparative results for this application.

| Method | Expected strengths | Tradeoffs and decision |
| --- | --- | --- |
| One model for planning, synthesis, and critique | Few identities, easy to reproduce, low integration overhead | Correlated errors and self-confirmation remain possible. Retained as the comparison condition with identical inputs, controller, and gates. |
| Structured planning and separate retrieval | Traceable question decomposition and clear citation audit. STORM supplies a precedent for perspective-driven retrieval and outlining. | Search and prose fluency can hide coverage failures. Store retrieval receipts, expose exact excerpts, and close directions lacking substantive sources. [STORM](https://arxiv.org/abs/2402.14207), [ALCE](https://arxiv.org/abs/2305.14627) |
| Literature-based discovery across domains | Can propose connections between separate literatures. Swanson's case provides a historical example. | Co-occurrence and source bridging only generate hypotheses. Require prior-art comparison, the strongest counterargument, a comparator, and a falsifying result. [Swanson](https://pubmed.ncbi.nlm.nih.gov/3797213/) |
| Multiple model roles and iterative criticism | Adds a separate opportunity to surface confounds, alternatives, and existing methods. | Costs and correlated errors can both grow. Use three historically qualified identities and one evidence-triggered revision. No tournament, recursive debate, or promotion from model consensus. [AI co-scientist](https://arxiv.org/abs/2502.18864), [AI Scientist](https://arxiv.org/abs/2408.06292) |
| Active search and Bayesian design | Expected utility can rank experiments and help allocate effort under uncertainty. | Open-domain tasks lack calibrated priors and likelihoods. Rank with ordinal value, uncertainty, effort, and expected information. Treat these as planning heuristics. Use registered controlled tests for actual effect claims. [Chaloner and Verdinelli](https://doi.org/10.1214/ss/1177009939) |
| Reproducible evaluations and outcome scoring | Known-answer controls, external labels, and record reconstruction separate testable claims from plausible writing. | Small scripted cases measure orchestration and safeguards. Broader inference-quality comparisons need multiple independently labeled cases. [DiscoveryBench](https://arxiv.org/abs/2407.01725), [CORE-Bench](https://arxiv.org/abs/2409.11363) |
| Independent commercial discovery | Observed buyer actions and expenditures can challenge the economic hypothesis. | Buyer access is external. Retain independently attested documents and keep market levels separate from technical outcomes. [NSF I-Corps](https://seedfund.nsf.gov/resources/awardees/phase-1/nsf-i-corps/) |

No raw reasoning is requested, stored, or required. Recorded explanations are planning outputs, evidence-linked objections, and deterministic controller choices. Reuse begins with run-owned records and exact request cache hits. General cross-run semantic memory and experiment ranking against prior outcomes remain future work.

## Implemented workflow

1. The `discover` command registers the versioned objective, bounds, and configured provider/model settings in a hashed artifact. Identical CLI registration in the same runtime has the same run ID. One fenced coordinator owns active work.
2. The planner proposes three cross-domain directions. Each includes a question, query, expected support, expected falsifier, and value, uncertainty, and effort estimates. The controller ranks directions by value times uncertainty divided by effort.
3. Each direction gets a Crossref query and, if no abstract or registered document is available, an optional Europe PMC query. The workflow also accepts preregistered public HTTPS documents, categorized as publications, technical documents, patents, datasets, industry or market evidence, regulatory material, or public discussion. It captures text, HTML, JSON, and CSV with bounded sizes. Patent, regulatory, market, and discussion coverage depends on registered URLs. Broad discovery has no general-web index, patent-specific search, PDF parser, paywall bypass, or unrestricted model-chosen URL dispatch. [Crossref API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/), [Europe PMC API](https://dev.europepmc.org/RestfulWebService)
4. Search receipts bind excerpts, publisher where available, dates, URLs, source IDs, archive digests, questions, and limitations. A title-only hit cannot advance a direction or support the proposal's premise. Canonical DOI and excerpt deduplication, and fallback abstract upgrades, preserve older snapshots. Literal quote checks constrain the evidence supplied to each model call.
5. At most two evidence-backed directions receive distinct hypothesis candidates. Each includes a measurable minimum effect, comparator, falsifier, proposed experiment, alternatives, prior art, uncertainty, and an economic hypothesis. The critique role sees the proposal and source excerpts and produces specific objections. A material objection may spend the single targeted search on a new query ranked by expected information divided by effort. Revision and a second critique require distinct substantive evidence. A remaining objection, invalid quote, or duplicate mechanism can reject a candidate. Empty evidence and reject-all are valid outcomes.
6. A separate scientific gate records evidence binding, cited prior-art coverage, measurable falsifier, and outstanding objections. Experimental success stays untested, mechanism and feasibility require external assessment, and novelty stays unverified. Arbitrary generated experiments do not execute. A candidate can proceed to a separately registered, supported experiment family or external reproduction.
7. Commercial evidence starts at Level 0. An interactive local operator can attach an independent commercial review using primary documents already archived on the run. Use the existing `market-document RUN_ID PATH --title TITLE` command to archive an external operator-held document. Use `discovery-commercial RUN_ID DIRECTION OBSERVATIONS.json` to record an assessment with an interactive attestation. The observation file contains an `observations` list with exact `citation`, `kind`, `interpretation`, and applicable buyer and payment fields. The levels are 1 for independently documented problem, 2 for documented spending or costly/comparable behavior, 3 for direct buyer validation or credible pilot interest, and 4 for a documented paid commitment. Levels above 1 require documented problem evidence. Levels 3 and 4 require matching the proposed buyer, and Level 4 requires a positive amount and currency. No fixture, index abstract, generated claim, or automatic model review qualifies. An attestation is a recorded human assertion and remains subject to independent audit.
8. SQLite events and content-addressed artifacts record the plan, sources, searches, candidate versions, critiques, controller decisions, final packet, and usage. A separate commercial review never edits the discovery packet. Cache-only replay opens a read-only snapshot and checks the event chain, artifact digests, and current source binding. Invalidated sources stop replay.

## Offline research quality results

Run `uv run python scripts/qualify_discovery.py runtime/new-discovery-rehearsal` with a new destination. The retained experiment has three full packets, SQLite/CAS state, event snapshots and metrics under `runtime/autonomous-research-CTehXZ/rehearsal-final`. The [DEFLATE](https://www.rfc-editor.org/rfc/rfc1951), [Base64](https://www.rfc-editor.org/rfc/rfc4648), and [Zstandard](https://www.rfc-editor.org/rfc/rfc8878) control excerpts were independently checked against the current RFC Editor plaintext on November 3 local time. The index responses and model outputs in the rehearsal were scripted. The separate live source probe returned three results each from Crossref and Europe PMC and archived response hashes. A separate run through the Catalog archived three public abstracts and one title-only record with no retrieval errors.

| Control | Reviewed challenge | Same one-model challenge | Reviewed two-candidate path |
| --- | --- | --- | --- |
| Exact proposal quotes | 4/5 | 4/5 | 6/6 |
| Fabricated quote advances | 0 | 0 | No fabricated quote injected |
| Known DEFLATE prior art surfaced | Yes | Yes | Yes |
| Original candidates independently routed to critique | 1 | 0, one same-model review | 2 |
| Distinct final mechanisms represented | 2 | 2 | 2 |
| Metric, comparator, and falsifier present | Yes | Yes | Yes |
| Fixture requests | 6 | 6 | 7 |
| Fixture input/output tokens | 600/480 | 600/480 | 700/560 |
| New dispatches or fetches on replay | 0 | 0 | 0 |
| Commercial level | 0 | 0 | 0 |

The three-role conditions use the same scripted answer policy as the one-model baseline. Their scores show no measured quality gain from role separation. The positive case exercises both reviews. The misleading case preserves the failed claim and rejects it. An additional reject-all test shows that repeated or missing evidence and a persistent material objection cannot produce a surviving hypothesis. A forced process exit after model settlement and before the stage checkpoint recovered the cache entry and issued no duplicate plan request.

Exact quote matching measures mechanical binding. It cannot determine whether an excerpt actually entails a claim, whether a cited work is the closest prior art, whether mechanisms are meaningfully different, or whether a proposed falsifier is practical. For the live evaluation an external reviewer should score each material claim as entailed, partial, contradicted, or unsupported; evaluate actual source relevance; compare candidates against known prior art; and assess the cost and validity of the proposed falsifier. Compare reviewed and single-model runs on a labeled set using the same sources and request ceilings if later authorized. Report empirical quality and token cost per externally useful hypothesis separately. The current $0 figures are fixture accounting.

## Live experiment preflight

The intended experiment is the objective in `config/discovery-objective.json`. It permits any evidence-supported industry. The model manifest uses the three direct Meta models previously verified in the smaller packet workflow. The new nested schemas and every route were exercised through mocked HTTP. Exact wire details and reasoning controls were checked against current documentation. [Meta Chat Completions](https://dev.meta.ai/docs/protocols/chat-completions), [Meta schema constraints](https://dev.meta.ai/docs/structured-output), [Meta reasoning](https://dev.meta.ai/docs/reasoning)

| Role | Model | Effort | Logical requests | Attempts including one retry | Gross estimate |
| --- | --- | --- | ---: | ---: | ---: |
| Plan | `muse-spark-1.3` | minimal | 1 | 2 | $0.073056 |
| Hypotheses/revision | `muse-spark-1.2` | minimal | 3 | 6 | $0.219168 |
| Review/re-review | `muse-wonder-1.0` | low | 3 | 6 | $0.760320 |
| Total | | | 7 | 14 | **$1.052544** |

Standard Spark input/output pricing is $1.25/$4.25 per million tokens and Wonder is $4/$20. The estimate assumes the full local 24,000-token context bound on every attempt, uncached input, and 1,536 output tokens per attempt including reasoning. Total estimated input upper bound is 336,000 tokens and configured maximum output is 21,504 tokens. Credits or cache discounts are excluded. Unsuccessful calls can consume tokens, and interrupted requests remain uncertain until evidence settles them. The application records usage and does not admit or reject requests based on dollar amount. [Meta prices and rate limits](https://dev.meta.ai/docs/pricing-rate-limits)

Preflight is local. Run from the worktree.

```sh
uv run autodiscover discover --preflight \
  --spec config/discovery-objective.json --providers config/discovery-meta.json
```

After explicit approval for this experiment, load `META_API_KEY` through the environment or the existing ignored, owner-only env file. Use a fresh isolated runtime directory and save the printed run ID. The example assumes the credential is already in the environment.

```sh
uv run autodiscover --root runtime/discovery-live-20261103 discover \
  --spec config/discovery-objective.json --providers config/discovery-meta.json \
  --allow-network --allow-live
```

Use the same runtime and run ID to replay. For an interruption, use `discover --run-id RUN_ID --providers config/discovery-meta.json --allow-network --allow-live` only after inspecting the ledger. An ambiguous or previously dispatched uncached attempt requires reconciliation. It never dispatches automatically again.

```sh
uv run autodiscover --root runtime/discovery-live-20261103 discover \
  --run-id RUN_ID --cache-only
```

The foreground run allows 240 seconds per invocation. Provider timeout is 25 seconds. Source timeout is 8 seconds per request, with at most four searches, eight index GETs, and any explicitly registered document fetches. Each safe retry waits with bounded backoff, including up to 30 seconds for `Retry-After`. A timeout, malformed result, uncertain dispatch, cancellation, or lease loss stops progression. Do not start a replacement run to work around an unresolved request.

Pre-register operational acceptance as a typed report with at least two substantive public source records, two competing candidates and role-separated critiques, no surviving citation errors, preserved decisions, consistent usage, and a zero-dispatch replay. A shortfall remains informative and is recorded without changing thresholds. A revision is conditional on a material objection and distinct new evidence. Independently score scientific and commercial claims before advancing any candidate.

**Live readiness: YES for one controlled foreground trial pending explicit approval.** The prior four live calls qualified smaller proposal and critique schemas. The new controller's full live behavior, richer schemas, source relevance, and actual usage remain unverified. Baseten remains outside this experiment and unqualified.

## Long-horizon and PR status

Durable registration, fencing, cross-process replay protection, checkpoint recovery, bounded retries, cancellation, source validation, and public-only live retrieval were exercised locally. The existing scheduler refuses discovery runs because it services the registered experiment families. Durable foreground continuation is available by run ID. A scheduler for discovery, cumulative resource windows across scheduled sessions, multi-host isolation, automated escalation, and a long-duration soak remain open. The full event-chain scan is intentionally conservative and should be measured before extended operation. The archive is tamper-evident when its event anchors are retained separately. The first controlled live run and independent review are prerequisites to unattended inference.

**Overnight operation: NO. PR #2 merge: NO.** PR #2 remains open and draft. No push, merge, background run, or additional billable inference occurred in this phase.

## Local verification and evidence

- `uv run ruff check .` passed. `uv run pyright` returned zero findings.
- `uv run pytest -q` passed 261 tests. The focused discovery, provider process-safety, and registered-experiment run passed 29 tests. The existing Starlette TestClient/httpx deprecation warning remained.
- `uv build` built the wheel and source distribution.
- `uv run python scripts/qualify_discovery.py …` produced three verified reports and event snapshots. The CLI `--preflight`, `--cache-only`, and `status` paths ran successfully against the retained roots.
- A mocked transport test initially passed the wrong adapter constructor argument. Switching to the existing `api_key` argument corrected the test and exercised every stage's strict nested Meta schema locally. No live provider was contacted.
- The shell GitHub CLI lacked authentication. The read-only GitHub connector independently confirmed the open draft and remote SHA.
- Staged Gitleaks and exact-value scanning of locally configured credentials passed. The main worktree's untracked status report was preserved.

## First foreground attempt

The credential-loaded run completed planning and three searches. The first proposal
returned `OUTPUT_TOKEN_LIMIT` with 1,536 output tokens including 292 reasoning
tokens. Both requests settled locally at a combined $0.010793 in standard-rate
usage. No partial proposal was accepted. The registered sample now requests shorter
prose and permits 2,560 completion tokens. The revised gross estimate is $1.210240
including all bounded attempts. The earlier run and its ledger remain available in
`runtime/discovery-live-20261103-retry`. The revised configuration registers a
distinct run. The revised live proposal has yet to be verified.

## Revised live run and replay

Run `discovery-9d86dedf2a48c9f787c13e5284e81b1a8e38e495ccfdbdd9e435723a8f144c4e`
completed with packet SHA-256 `7259db666e6d4842df8f40eb66ab90ab07b217295812f56ab84359ffb934034e`.
The ledger settled four calls across Spark 1.3, Spark 1.2 and Wonder 1.0 at
$0.054628 in locally calculated standard-rate usage. It records 3,956 input and
4,483 output tokens, including 1,443 reasoning tokens, and no uncertain charges.
Three public searches returned five abstract records and five title-only records.
Two proposals were generated. The cell-preservation proposal failed evidence
binding and stopped before critique. The mechanical-wear proposal received a
separate critique and was rejected with material evidence and measurement gaps.
No revision ran. Read-only replay reproduced the packet with identical event
anchors and zero external calls. The run verified live packet generation,
accounting, and replay. The two-critique acceptance criterion was not met.
