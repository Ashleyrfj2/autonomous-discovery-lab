# Research-quality qualification plan — 2026-11-03

Status: **RESEARCHED / IMPLEMENTATION PLAN**, not an executed qualification or a scientific discovery. Prepared from repository inspection and publicly accessible original benchmark/paper pages. This document never upgrades a preprint, mock run, synthetic market record or unexecuted benchmark into acceptance.

## Correct current state

- Phases 0–8 have recorded local acceptance; a short Phase 8 mock operation completed 8 workflows, 96 stages and 24 experiment jobs. This measures bounded orchestration, **not** broad scientific discovery.
- Phase 9 read/auth/control/review backend has recorded local qualification with 175 tests; the dashboard and browser gate remain incomplete. The 12ui image conversion was interrupted under the prior three-minute permission. Preserve the selected design; no new hosted conversion or design spend is authorized here.
- Reviewed experiments still cover **encoding-v1**. Crossref metadata and a limited set of primary documents have been retrieved. Mechanism-level prior-art evaluation, a second genuinely distinct experiment family, live Meta/Baseten runs, extended operation and real commercial validation are not accepted.
- This chat-mode branch adds a read-only source-bound prior-art dossier. Its tests are written but have **not** been run against the user's private repo in this session.

## External research findings and design implications

| Evidence | What the authors report | Action for this repository | Evidence maturity |
| --- | --- | --- | --- |
| ScienceAgentBench (ICLR 2025) | 102 data-driven research tasks derived from 44 peer-reviewed papers; the strongest tested agent solved 32.4% of tasks independently under its stated setup | Evaluate the lab at individual research stages, not merely an attractive final report; compare against simple and agentic baselines | Peer-reviewed benchmark |
| MLR-Bench (NeurIPS 2025) | 201 open-ended ML research tasks; its evaluated agents frequently produced invalid or fabricated experimental outcomes | Require primary execution traces, immutable preregistration, independently recomputed results, and negative-run retention | Peer-reviewed benchmark |
| Towards end-to-end automation of AI research (Nature 2026) | The AI Scientist produces research artifacts but documented failures include incorrect experiments, citation errors and weak methodology | Never treat manuscript quality or an automated reviewer as authoritative scientific validation | Peer-reviewed research |
| AutoResearchBench (Apr 2026) | Deep and wide scientific literature discovery are both difficult; reported model results remain low on its tasks | Evaluate **recall/relevance and coverage** separately from claim support; stop treating metadata as adequate method research | Preprint / publicly released benchmark |
| DISCERN (Sep 2026) | Tests data integrity, analytical verification and hypothesis review under traps; higher-level evidence reasoning is especially unreliable in tested models | Add intentional confounds and counterfactuals, require correct abstention, and score hypothesis revision independently | Preprint; do not imply peer review |
| Source-faithfulness benchmark (EMNLP 2026) | Source-supported-looking answers can still be wrong or poorly grounded | Measure passage-to-claim entailment, quote exactness and citation retention across agent handoffs | Peer-reviewed benchmark |
| Hidden pitfalls of AI scientist systems (2025 preprint; later published) | Benchmark choice, leakage, metric misuse and post-hoc selection create misleading successes | Archive full pre-decision plans and attempted trajectories, not only clean final outputs | Research article / published follow-up |

### Original references

1. Chen et al., *ScienceAgentBench*, ICLR 2025: https://proceedings.iclr.cc/paper_files/paper/2025/hash/f12b4df26344f3be803c06b555252efe-Abstract-Conference.html
2. Chen et al., *MLR-Bench*, NeurIPS 2025: https://proceedings.neurips.cc/paper_files/paper/2025/hash/ab8dd000d6f87f40061a73f8bca7fae4-Abstract-Datasets_and_Benchmarks_Track.html
3. *Towards end-to-end automation of AI research*, Nature 2026: https://www.nature.com/articles/s41586-026-10265-5
4. Xiong et al., *AutoResearchBench*, arXiv 2604.25256: https://arxiv.org/abs/2604.25256
5. Huang et al., *DISCERN*, arXiv 2609.33357: https://arxiv.org/abs/2609.33357
6. Gao et al., *Can Your Agent Read the Source Faithfully?*, EMNLP 2026: https://aclanthology.org/2026.emnlp-main.1855/
7. Luo et al., *The More You Automate, the Less You See*, arXiv 2509.08713: https://arxiv.org/abs/2509.08713

The cited studies test different settings and models. Do not combine their scores into a single expected performance estimate for this lab.

## Evaluation design — preregister BEFORE first live run

**Unit of analysis:** an independent task × seed × model configuration with a frozen source set/recorded retrieval log, versioned prompt/code, budget, environment, success criteria, and predetermined maximum retries.

**Minimum stages and measurements:**

1. **Search/retrieval:** source recall against human-selected known-relevant papers, top-k precision, coverage of contradictory papers, DOI/URL validity, retrieval cost. Score unknown papers and paywall limits transparently.
2. **Attribution:** every factual claim must link an exact source/passsage digest. Measure support correctness by blinded annotation, missing citations, misleading quotations, invalidated-document reuse and citation survival across agents.
3. **Hypothesis construction:** independent reviewers score specificity, falsifiability, proposed mechanism, connection to actual findings, alternate hypotheses and leakage risk. An LLM judging itself cannot satisfy the independent gate.
4. **Experimental integrity:** a locked baseline, locked metrics and seeds, held-out evaluation, randomized order when appropriate, falsification checks, unexpected-condition probes, repeatability, negative results, and retained trajectory.
5. **Novelty:** record functionally equivalent prior art and the precise proposed difference. Valid source search + no matches yields `unknown`, never `supported`. Establish technical advantage separately from novelty.
6. **Commercial:** concrete user, economic buyer, problem evidence, competing alternatives, buyer access, cost/reachability and externally verifiable adoption/payment signals. Local fixtures are always `unvalidated`.

**Baselines:**

- Fixed source-keyword/metadata search and nonagentic extraction.
- One-pass model with the same source pool, budget and output schema.
- Bounded research-loop variant without branching or critique.
- Full branch/verification pipeline; compare under matched spend and task visibility.
- Human/known-answer or controlled gold labels where available. Avoid treating a second LLM reviewer as ground truth.

**Suggested first evaluation batches (NOT yet executed):**

| Batch | Cases | Purpose | Stop / failure examples |
| --- | --- | --- | --- |
| B0 — contract integrity | 10–20 local adversarial fixtures | Cross-run quotation, stale source, altered digest, metadata false certainty, injected instructions, duplicate comparison | Any fabricated source or promotion to supported novelty blocks acceptance |
| B1 — source grounding | 20 locked multi-paper questions with gold passages | Measure grounded citations, retrieval recall and honest abstention | Unsupported factual assertions or stale-source acceptance recorded as critical errors |
| B2 — methodological traps | 12–20 preregistered confound/leakage/metric cases | Test interpretation and evaluator independence | Fabricated results, altered metric threshold, held-out leakage |
| B3 — two distinct experiment families | Encoding-v1 plus one **separately reviewed**, safely isolated nonencoding family | Establish actual cross-domain extension | Merely changing domain labels while executing encoding-v1 does not count |
| B4 — sustained operation | 1–4 hour bounded mock soak, then separately authorized low-spend live trial | Recovery, queue fairness, budgets, interruption, provenance | Loss of committed work, double charge, authority bypass, unbounded retry |
| B5 — blinded external review | 2–3 specific hypotheses and multiple independent readers | Functionally equivalent prior art, methodological criticism | All hypotheses may remain unknown/rejected without making engineering fail |

The numeric batch sizes are proposed engineering design targets, not measured evidence or established scientific standards.

## Independent acceptance matrix

- **Integrity gate:** zero tolerated cross-run evidence leaks, unsupported citations, forged metrics, or invalidation bypasses in preregistered adversarial cases. Fail closed.
- **Stage-quality gate:** publish measured retrieval/attribution/analysis/hypothesis scores **with denominators, uncertainty, costs and failures**. Set numeric quality thresholds only after a pilot calibration; do not post-hoc choose the pass line.
- **Novelty gate:** an independent method-by-method review and a meaningful controlled result are needed before treating any claim as supported. An empty literature search fails this gate.
- **Commercial gate:** authenticated real outside-world evidence, not synthetic personas or self-rated market attractiveness. Keep Level 0 until qualifying evidence is reviewed.
- **Operational gate:** complete runbook and bounded recovery evidence from the same qualifying commit/source manifest; GitHub Actions failures alone do not determine readiness.
- **Release gate:** security/permissions review, data rights, source retention, secrets/log review, budget and interruption audit, fresh-machine reproducibility and completed Phase 9 browser flows.

## Implementation order and ownership

| Order | Work | Can ChatGPT produce now? | What still requires local/external verification |
| --- | --- | --- | --- |
| 1 | Source-bound prior-art dossier, read-only CLI, adversarial tests, docs | Yes; branch in progress | Run Ruff/Pyright/full pytest/build; inspect resulting JSON on live stored evidence |
| 2 | Scientifically grounded benchmark plan, exact citations, acceptance gates | Yes; this document | Independently score items and freeze benchmarks before first trial |
| 3 | Verified evidence logging/handoff and PR review package | Yes | Merge decision after local verification |
| 4 | Full 12ui-based Phase 9 view integration | Not without selected design export / needed local UI work | Complete prior conversion and browser tests under approved time/spend |
| 5 | Additional trusted nonencoding worker/evaluator | A reviewable code proposal is possible; no proof in chat | Host isolation, independent measurement and full compatibility tests |
| 6 | Meta/Baseten live qualification and extended runs | Static config/protocol audit possible | Actual model credentials, approved spend, runtime network and billing evidence |
| 7 | Real scientific novelty and buyer commitments | Research groundwork possible | Actual independent experiments, reviewers and customer contact |

## Operator handoff

Run first: `AGENTS.md`, `docs/HANDOFF.md`, `docs/PHASE_9_IMPLEMENTATION_PLAN.md`, `docs/PRIOR_ART_DOSSIER.md`, this plan and the open PR. Protect untracked `docs/PROJECT_STATUS_REPORT_.md`. Inspect Git history and use actual source, not stale phase summary. No production deployment, no merging, no automatic browser/paid calls, no outreach. Treat all chat-made code as **IMPLEMENTED_UNVERIFIED** until local checks are completed and recorded.

The full mission remains cross-industry discovery, not a compression benchmark, invented startup idea catalog, or static research writing exercise.
