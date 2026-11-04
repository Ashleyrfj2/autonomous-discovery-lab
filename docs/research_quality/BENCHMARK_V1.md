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