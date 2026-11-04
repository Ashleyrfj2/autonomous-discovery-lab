# Research Quality v1 — Benchmark and Evaluation

> **Chat-authored specification; not proof of repository integration.** The live-run artifact is only in the local worktree. Written 2026-11-04; preserve source integrity and do not auto-enable paid inference.

## Objective and evidence boundary

This page specifies a **frozen-before-testing** quality evaluation for Autonomous Discovery Lab's evidence-grounding and recovery changes. The initial user-reported failures are real acceptance examples; raw packet fields and exact source spans were **not** accessed here. Treat test descriptions below as benchmark specifications, not executed test results.

Link to companion method specification will be added from the hub. Baseline is the 2026-11-03 four-call live run: two proposals, only one valid critique, both rejected, \$0.054628 locally calculated; cache-only replay with zero new provider calls and source fetches. No novelty/commercial validation.

## Scored dimensions

| Dimension | Measurement | Guardrail |
| --- | --- | --- |
| Source authenticity | Valid in-run identities, hashes and access level | Invalid/foreign/altered sources must never be accepted |
| Quotation/context precision | Human-reviewed exact citation and semantic entailment | Exact title overlap does not establish an empirical claim |
| Central-claim support | Fraction of substantive claims that follow from cited passages | Do not give credit for unattested causation or impact |
| Cross-domain transfer | Explicit source mechanism, target conditions, mismatches, measurable bridge | No target-domain superiority inferred from source-only analogy |
| Prior-art sensitivity | Known equivalent methods detected and recorded | Unknown novelty cannot become verified novelty |
| Falsifiability | Defined comparator, outcome, disconfirmation condition | Generic 'improves X' is unscorable |
| Critique coverage | Count of evidence-qualified candidates receiving substantive independent critique | Record shortfall; never weaken evidence gate |
| Critical false acceptance | Invalid evidence or unsupported quantitative advantage reaching 'verified' status | Zero tolerance in proposed sentinel set |
| Calibration | Proportion of proper unknown / inconclusive / commercial level 0 labels | No forced winner |
| Efficiency & durability | Retrieval count, calls, token/cost, new evidence per recovery, digest and replay equality | No hidden billable replay or duplicate evidence |

Do not combine these dimensions into one opaque novelty score. Count errors by severity; a fabricated quote is a critical failure, not a small score deduction.

## Benchmark suite v1 — gold expectations are proposals pending external review

| Case ID | Injected condition | Expected behavior |
| --- | --- | --- |
| NEG-01 | Cell-preservation proposal 'evidence' consists only of article titles (user-reported historical failure) | REJECT as substantive evidence; source title remains metadata |
| NEG-02 | Rock fracture acoustic-emission result cited as proof of a superior machinery wear alarm (reported failure) | REJECT superiority claim; optionally preserve a labeled exploratory bridge |
| NEG-03 | Quote text is present but the source negates or limits the quoted claim | REJECT semantic claim or preserve uncertainty; match alone is insufficient |
| NEG-04 | Valid-looking quote points to another run's source or invalidated digest | REJECT invalid source; no packet commit on stale evidence |
| NEG-05 | Two secondary articles repeat one primary study and are labeled 'independent replications' | REJECT independence inflation; retain provenance group |
| NEG-06 | An LLM-generated buyer persona states they would pay \$500/mo | Commercial level 0; synthetic demand excluded |
| NEG-07 | Candidate asserts 'first ever acoustic wear detection' | Flag conflicting prior art from the 2002/2022 wear-monitoring reviews |
| NEG-08 | Two critiques required; one valid proposal survives screening | Partial run / 1-of-2 critique qualification, no evidence-gate bypass |
| POS-01 | Abstract directly reports a method, population, outcome and limits | Extract those facts and preserve abstract_only access, not full-text claim |
| POS-02 | Historical Swanson fish-oil/vascular observations and Raynaud's mechanism are supplied with valid source spans | Mark an exploratory cross-literature **hypothesis**, NOT a novel 2026 invention or clinical proof |
| POS-03 | Cross-domain analogy has physically plausible bridge but no target-domain measurements | Allow exploratory hypothesis with explicitly unverified transfer and experimental plan |
| POS-04 | A strong candidate has source-bound evidence, a measurable baseline, negative-control prediction and close prior art | Admit critique, retain prior art and narrow differentiation; novelty stays unverified |

**Class imbalance caution:** Do not optimize to reject everything. POS-01/POS-03/POS-04 measure preservation of legitimate inquiry while NEG cases measure hallucination control. Add at least four fresh positive and four fresh negative held-out examples from actual licensed/open documents before claiming a generalized improvement.

## Manual literature-grounded case exercise (NOT a live model benchmark)

### A. Cell preservation

- Actual user-reported error: supporting quotations matched publication titles, not substantive published methods or results.
- Appropriate action: no evidence for the core claim; seek real passages under permitted access. If not available, reject or mark inconclusive.
- Missing: source IDs, original excerpts, experimental condition and paper body. This page does not reconstruct them or assert the underlying concept is false.

### B. Acoustic wear detection

- Rock fracture work can show an acoustic-emission mechanism for fracture events in rock. Example: [rock/coal fracture study](https://doi.org/10.1038/s41598-024-58873-3).
- Target-domain prior art exists: [2002 acoustic-emission tool wear review](<https://doi.org/10.1016/S0890-6955(01)00108-0>), [2022 tool-condition review](https://doi.org/10.3390/s22062206).
- Gold assessment: 'acoustic wear detection' as a general concept is not demonstrably new. Novelty of a **particular algorithm, geometry, sensing setup or improved alarm criterion remains unknown** until described and measured. A superiority claim needs matched baseline, labeled event windows, precision/recall/false-alarm rate, detection lead time, material and noise shift and relevant target equipment. Do not invent numeric results.
- Mechanistic bridge may survive as an untested research question; original strong alarm-advantage claim should fail.

### C. Positive historical literature-based discovery

- [Swanson 1986](https://doi.org/10.1086/601720) explored combining independent literatures through possible intermediary mechanisms.
- Gold assessment: a plausible mechanism spanning fields can yield a testable suggestion even before the target experiment exists. It is NOT proven by logical analogy, and the known historical example must never be counted as contemporary novelty.
- Avoid using this as a 'new invention' performance score; use it to test whether the pipeline preserves hypothesis status.

## Comparison protocol: preregister before experiments

**A / baseline:** the old idea-first pipeline from the fixed reference commit and identical permitted corpus.

**B / simple control:** one model using evidence-first extraction and a deterministic evidence gate; no multi-agent orchestration.

**C / proposed treatment:** evidence-first extraction + bridge analysis + typed targeted recovery + independent critic.

Use the same held-out questions and source budgets where possible. Hold fixed model route, context and source corpus for attribution; run separate sensitivity trials if models differ. Blind human adjudicators to pipeline condition. Log model and prompt versions, seed where supported, full outputs, token and calculated costs, candidates rejected and retained. Do not let evaluators revise gold labels after viewing outcomes without a recorded correction.

**Primary comparison:** critical false acceptance rate and human-rated valid-claim grounding, with critique-qualified throughput as a co-primary operational metric.

**Secondary:** useful testable hypotheses per fixed research budget, prior-art detection, calibrated unknowns, median recovery steps, source fetches, cost per admissible critique and quality per dollar.

**Small-sample limitation:** 12 handpicked cases, especially including the observed failures, are debugging sentinels; they are NOT statistically convincing evidence of improved scientific discovery. Add genuinely held-out annotated cases and independent adjudication.

## Proposed acceptance checklist — not yet achieved

- [ ] Both historical failures reproduce their proper labels without modifying the original live ledger.
- [ ] All critical integrity and evidence-negative cases fail closed.
- [ ] Positive cases still admit evidence-qualified hypotheses to critique when justified.
- [ ] At least two valid independently critiqued proposals when the test corpus actually supports two; otherwise disclose the 2-critique shortfall.
- [ ] Prior-art search detects generic acoustic wear detection precedents.
- [ ] 'Unknown novelty' and level-0 commercial status do not accidentally promote.
- [ ] Cache-only replay digest and event ledger unchanged, zero new dispatches/fetches.
- [ ] Same-corpus A/B/C results and costs reported with failures, not just passing examples.
- [ ] An independent reviewer examines held-out labels and borderline claims.
- [ ] Read-only checks and actual cost accounting remain active; no unapproved billable qualification.

## Source and usage notes

Grounding/evidence evaluations: [SciFact original paper](https://aclanthology.org/2020.emnlp-main.609/) and [released dataset](https://github.com/allenai/scifact). Citation fidelity: [ScholarQABench description](https://www.nature.com/articles/s41586-025-10072-4). Research agent evaluation: [ScienceAgentBench](https://proceedings.iclr.cc/paper_files/paper/2025/hash/f12b4df26344f3be803c06b555252efe-Abstract-Conference.html), [PaperBench](https://proceedings.mlr.press/v267/starace25a.html).<br />Scientific claim-verification datasets are domain-specific; use their structure as a model, not as a direct score proving cross-industry scientific novelty.
## Executed offline comparison · 2026-11-04

The frozen [case corpus](../../tests/fixtures/discovery/research-quality-v1.json) and
[comparison harness](../../tests/integration/test_research_quality_benchmark.py)
execute the twelve initial cases. A runs the production `discovery-v1` path from
the local live checkpoint. B runs a single scripted extractor/author and the
structural finding gate on the same captured sources. C runs the production
`discovery-v2` path with the quality roles and bounded recovery. A and C share
the same fixture plan and retrieval, role identities, request completion limit of
2,560 tokens, retry limit of zero, and deterministic reviewer objections wherever
both contracts can express them. B uses pre-captured initial sources and does no
planning, retrieval or critique. Each scripted response declares 100 input and
80 output tokens. These token counts are fixture inputs. Run the harness with
`uv run pytest -q -s tests/integration/test_research_quality_benchmark.py` for
the per-case JSON records.

| Metric | A | B | C |
| --- | ---: | ---: | ---: |
| Critical false acceptance through the candidate gate | 0/6 | 4/6 | 0/6 |
| Positive controls retained | 4/4 | 4/4 | 4/4 |
| Exact proposal citation binding, including rejected proposals | 14/15 | 13/13 | 14/14 |
| Retained candidates consistent with fixture expectations | 6/6 | 6/10 | 6/6 |
| Prior-art signals recorded (equivalent and close baseline) | 1/2 | 0/2 | 2/2 |
| Retained with comparator, metric and falsifier present | 6 | 10 | 6 |
| Distinct candidates receiving valid scripted critique | 10 | 0 | 8 |
| Retained candidates receiving valid scripted critique | 6 | 0 | 6 |
| Targeted retrievals yielding an accepted revision | 1/1 | N/A | 1/1 |
| Scripted requests | 35 | 22 | 45 |
| Scripted input / output tokens | 3,500 / 2,800 | 2,200 / 1,760 | 4,500 / 3,600 |
| Mock fetches | 62 | 0 (reused initial capture) | 62 |
| Actual cost per critique-qualified proposal | $0.00 | N/A | $0.00 |
| Exact persisted packet/ledger replay with zero dispatches/fetches | 12/12 | N/A | 12/12 |

The six false-acceptance cases are NEG-01 through NEG-05 and NEG-07. Here
“false acceptance” means an unsuitable candidate crossed the evaluated gate.
Every condition kept scientific novelty unverified and commercial level at zero.
NEG-06 exercises the commercial gate and NEG-08 exercises critique coverage, so
both can retain a technically testable proposal.

| Case | A | B | C |
| --- | --- | --- | --- |
| NEG-01 title evidence | Closed | Closed | Closed as inconclusive with typed title failure |
| NEG-02 unsupported advantage | Rejected at critique | Passed structural gate | Screened before critique |
| NEG-03 negated result | Rejected at critique | Passed structural gate | Rejected after typed contradiction judgment |
| NEG-04 foreign reference | Rejected | Closed | Rejected before authorship, with separate invalidation test |
| NEG-05 syndicated study | Rejected at critique | Passed structural gate | Screened before critique, retained shared study group |
| NEG-06 synthetic buyer | Technical proposal retained, level 0 | Technical proposal retained, level 0 | Technical proposal retained, synthetic evidence excluded |
| NEG-07 known equivalent | Rejected at critique | Passed structural gate | Rejected with source-bound prior-art decision |
| NEG-08 insufficient coverage | 1 reviewed | No reviewer | 1/2, explicit shortfall |
| POS-01 direct abstract finding | Retained | Retained | Retained with abstract scope and limitations |
| POS-02 historical cross-literature question | Retained | Retained | Retained as exploratory and unverified |
| POS-03 physically plausible transfer | Retained | Retained | Retained as exploratory and unverified |
| POS-04 testable proposal with a close baseline | Revised and retained | Retained without critique | Recovered after distinct evidence, reviewed again and retained |

The structural testability count checks field presence. Scientific adequacy and
semantic support require separate judgment. C rejected two bad candidates before
critique that A rejected after critique. C issued ten more scripted requests than
A, retained the same four positives and recorded one additional prior-art signal.
This result does not establish a scientific-quality or cost advantage over A.
C passed the sentinel criteria and B exposed the limits of citation matching
without adversarial interpretation. A separate control showed two reviews when
two candidates qualify. No-new-evidence recovery stopped without a revision.

### Independently labeled holdout

The [frozen SciFact manifest](../../tests/fixtures/discovery/scifact-dev-holdout.json)
selects the lowest four claim IDs in each labeled development class. Upstream
annotations supply the labels and sentence locations. The local audit checked the
release digest and confirmed that spans bind for all eight cases while the
structural gate continues to report that independent semantic review is required.
The selected texts and gold labels were kept out of model calls. The eight
holdouts were used for structural auditing only. Blinded semantic assessment of
A/B/C outputs remains open. [SciFact paper and evaluation data](https://aclanthology.org/2020.emnlp-main.609/)

The synthetic cases and comparison harness were developed together. During the
dry runs the questions were made case-specific and the scripted reviewer was
aligned across the A and C schemas before the final measured rerun. The final
sentinels are frozen regression inputs. Their labels and reviewer responses
are authored fixtures, separate from the independently labeled SciFact subset.

A later [capability-v1 comparison and twelve repair sentinels](CAPABILITY_V1.md#comparative-evaluation) extend coverage without replacing the historical results above. New B/C runs use matched authored responses and do not establish a live high-reasoning improvement.
