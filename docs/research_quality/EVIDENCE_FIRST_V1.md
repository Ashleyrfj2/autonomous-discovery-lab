# Research Quality v1 — Evidence-first Discovery and Recovery

> **Chat-authored specification; not proof of repository integration.** The live-run artifact is only in the local worktree. Written 2026-11-04; preserve source integrity and do not auto-enable paid inference.

## Status and scope

**Status: DESIGN SPECIFICATION — not implemented in repository.** Prepared 2026-11-03 from the user-reported 2026-11-03 live research run and public research sources. The underlying local packet was not inspected through Notion; its precise source spans, model outputs and event IDs need to be checked against the actual repository artifact before code edits.

**User-reported live checkpoint:** four provider calls, locally calculated \$0.054628, typed research packet persisted, replay showed zero additional model calls/source fetches and unchanged digest/event ledger. Two proposed hypotheses were rejected: cell preservation failed source-evidence screening before critique; acoustic wear detection was critiqued and rejected. Only one critique completed versus the two-critique acceptance criterion. No verified novelty or market demand.

Related hub: [Autonomous Discovery Lab — Chat implementation handoff (2026-11-03)](https://app.notion.com/p/40dec84d128b81868c97f4ca1e9bb9ed).

## Decision RQ-001 — Evidence-first pipeline (proposed)

**Replace idea-first persuasion with traceable evidence assembly.** This is a hypothesis about a better workflow, not yet a measured improvement. Keep the current evidence gate, source provenance, replay and actual research packet persistence.

Recommended stage sequence:

1. Register question and scope; define what would count as evidence, disconfirmation and a useful result.
2. Retrieve authentic sources; store snapshots or content hashes, dates, identifiers, source access level and search provenance.
3. Extract atomic findings (method, observation, result, uncertainty, limitation) from actual abstract/body passages **before** asking for a new proposal.
4. Assemble cross-source relations, explicitly classifying observation, association, causal mechanism, analogy and unsupported transfer.
5. Generate competing hypotheses from evidence IDs; tag each claim as directly supported, inferred, or unverified.
6. Perform cheap structural and source-span checks; send only evidence-eligible proposals to independent critique.
7. Route recoverable failures to targeted retrieval; reject speculative/hard failures; record every attempt.
8. Critic checks rival explanations, specific prior art, target-domain evidence, benchmark alternatives and falsification.
9. Record advance / investigate / reject / inconclusive separately from scientific novelty and commercial validation.
10. Persist typed packet and cache-only replay; no silent overwrites or duplicate evidence events.

**Important:** An evidence-qualified hypothesis is only eligible for critique. It is NOT independently verified, novel, feasible, or commercially validated.

## Proposed canonical evidence contracts

### Source record

- source_id (stable, run-local), URL/DOI and canonical identity; retrieval timestamp; source type (primary, review, patent, secondary, forum), publication date.
- access_level = title_only / abstract / excerpt / full_text / dataset / code; retrieved_content_sha256; extraction method and exact boundaries.
- authors/publisher, version/retraction/correction status where obtainable; source limitations and independence group. Never claim full-text coverage from an abstract.
- Maintain source ownership by run and source invalidation semantics; revalidate before packet commit.

### Atomic finding record

- finding_id, source_id, literal source_span or position, location (abstract/results/discussion/metadata), method/design, population or material, experimental conditions.
- outcome and direction (if observed), effect/units only where explicitly stated, uncertainty, limitations, directly_supported_claim, interpretation, contradictory evidence IDs.
- support_class = directly_observed / source_interpretation / external_inference / speculative; evidence_relation = supports / contradicts / background / unrelated.
- Do not turn article titles, keyword lists or hypothetical statements into measurements. A matching quotation is not proof that the claim is true: the passage must actually entail the proposition in context.
- Extraction can return **no findings** with an explicit reason.

### Mechanistic bridge record

- bridge_id, finding_ids_from_domain_A, target_problem_and_domain_B, proposed_shared_mechanism, variables and operating conditions.
- supports_in_domain_A, direct_target_domain_evidence, mismatched_materials_or_scale_or_noise, competing_explanations, missing_link, falsifiable_transfer_prediction.
- classification = direct_target_evidence / plausible_transfer_requires_test / superficial_analogy / contradicted / already_known.
- Cross-domain connections must explicitly state where inference starts and what is still uncertain.

### Proposal record

- proposal_id, revision, evidence_ids, bridge_ids, mechanism, target population/system, proposed measurable outcome, existing baseline, competing hypothesis, falsification experiment.
- novelty_status = unknown / existing_close_prior_art / externally_reviewed; commercial_validation_level = 0..4 with provenance requirements.
- claim register with claim_id, text, claim_type (empirical / inferred / proposed / commercial), evidence_ids, entailment status.
- Never promote scientific novelty or commercial status on the basis of one model's rating.

## Gate design (proposed)

| Gate | Required check | Outcome if missing |
| --- | --- | --- |
| G0 source integrity | Source belongs to run, actually fetched, valid digest, not invalidated | INVALID_SOURCE / reject |
| G1 substantive evidence | At least one actual result or method passage substantiates each central empirical claim | NEED_TARGETED_EVIDENCE or reject |
| G2 passage entailment | Exact quotation, context, negation, scope, population and claim meaning line up | MISMATCH / reject |
| G3 mechanism bridge | Explicit common variable and target-domain assumptions; no automatic transfer of an effect | HYPOTHESIS_ONLY / investigate |
| G4 experimentability | Independent outcome metric, comparator and failure criterion | NEED_EXPERIMENT_DESIGN |
| G5 prior art | Search functional equivalents; log queries, sources and closest matches | NOVELTY_UNKNOWN (not reject solely for uncertainty) |
| G6 market | Named user/buyer and real evidence separated from synthetic assumptions | COMMERCIAL_LEVEL_0 (no promotion) |

Distinguish **hard structural rejection** (fake or invalid source, invented quote), **unsupported central claim** (can sometimes recover), and **novelty unknown** (hypothesis may still be researched). A legitimate exploratory idea may proceed as a hypothesis with explicit uncertainty, but must never be reported as an established improvement.

### Acoustic example: transport test

Source domain A: rock fracture acoustic emission used to detect crack evolution under specified lab loading. Domain B: machine wear alarm and its purported advantage. Rock fracture results do not directly establish detection accuracy, time-to-warning, false alarm rate or cost advantage in machine wear. Shared principle: elastic waves accompanying material changes; important mismatches include materials, operational loading, sensor placement, backgrounds, type of wear, signal processing and required lead time.

A historical [2002 review of acoustic-emission tool wear monitoring](<https://doi.org/10.1016/S0890-6955(01)00108-0>) and a [2022 review of tool condition monitoring](https://doi.org/10.3390/s22062206) show that **general acoustic-emission wear monitoring has prior art**. That does not settle novelty for an unspecified narrower method or prove that any proposed alarm improves existing methods. A credible narrow hypothesis requires a named target condition, specific comparator (e.g., current acoustic baseline or vibration), noise setting, pre-registered detection metric, false alarm metric and held-out evaluation.

## Recovery routing policy RQ-002 (proposed)

| Failure | Recommended action | Terminal status |
| --- | --- | --- |
| Title/metadata quoted as empirical result | Look for valid body/abstract evidence in permitted source; never reinterpret title as result | REJECT if unavailable |
| Exact quote invented, negated or wrongly attributed | Fail closed; log claim and source-span mismatch; fresh evidence retrieval can support a *new* revision | REJECT revision |
| Valid source, irrelevant domain | Targeted search in actual target domain; do not recast irrelevant source as direct evidence | NEED_TARGET_EVIDENCE / reject |
| Reasonable cross-domain analogy, missing bridge | Retrieve primary target-domain work, model constraints and comparison baseline; leave inference tagged | EXPERIMENTAL_HYPOTHESIS / reject |
| Existing equivalent method found | Preserve prior art; search only explicitly claimed differentiation | ALREADY_KNOWN / NARROWER_UNVERIFIED |
| Contradictory findings | Retain both and identify moderators, methods, target populations; no cherry-picking | CONFLICTED |
| Claims rely on synthetic buyer testimony | Disallow commercial promotion | COMMERCIAL_LEVEL_0 |
| Diminishing return or loop | Stop after a registered bounded number of distinct recovery paths; report inconclusive | INCONCLUSIVE |

Proposed experimental default (not a current code configuration): maximum **one targeted recovery query batch per failure type and one proposal revision per candidate**, with change-of-evidence required. The bound should be configurable and evaluated, rather than silently retrying until two critiques appear. Each rescue attempt logs reason, new sources, revision, incremental tokens, calculated cost and outcome.

**Quality-vs-coverage rule:** Two evidence-qualified critiques remains an acceptance target. If only one proposal qualifies, report partial qualification. NEVER bypass G0–G2 to meet critique count.

## Role instructions (implementation-ready prompt drafts)

### EVIDENCE_EXTRACTOR

You are extracting evidence, not brainstorming ideas. You may use only provided source documents and quoted spans. For each atomic finding, return source ID, precise passage/location, what was actually studied, variables, result, limitations and whether the passage directly entails the claim. Treat titles and bibliographic metadata as metadata, not experimental results. If an abstract lacks the necessary method/results, return insufficient_evidence. Preserve negation and conditional statements. Do not infer effect sizes or cite source sections you have not seen.

### BRIDGE_ANALYST

Given a source-bound finding set and target problem, identify a possible common mechanism, operating conditions, domain mismatches, nearest target-domain prior art, and one falsifiable transfer prediction. Categorize the proposed transfer as directly_supported, provisional_or_testable, superficial_analogy, or contradicted. Explicitly identify which link is NOT observed. Multiple domains sharing a noun is not a mechanism.

### HYPOTHESIS_AUTHOR

Produce up to N competing hypotheses using only finding IDs and explicitly marked inferences. For each: target, intervention/mechanism, comparator, predicted measurable outcome, causal assumptions, counterhypothesis, cheapest disconfirming test and status. A candidate may be interesting without being supported. Never invent quotations, empirical results, novelty or customer demand. Return no candidate if no defensible hypothesis exists.

### ADVERSARIAL_REVIEWER

Independently check the proposal against the actual linked passages and newly retrieved counterevidence, not merely the author's summary. Check context, target-specificity, prior art, alternative explanations, measurement definition and expected failure modes. Classify unsupported central claims and specify a source ID or new research query that could resolve them. Review does not constitute scientific validation, even if a separate model produced it.

### RECOVERY_CONTROLLER

Given a typed failure code, candidate revision lineage, prior searches and remaining research allowance, select TARGETED_RETRIEVAL / REVISE / REJECT / INCONCLUSIVE. Never relabel invalid evidence as sufficient, never repeat identical queries after no progress, and never spend merely to satisfy a critique quota. Explain the chosen branch in an auditable short decision record.

## Evidence supporting this design (public, not a completed system validation)

- [EXHYTE review: exploration → hypothesis → testing](https://pmc.ncbi.nlm.nih.gov/articles/PMC13674306/) (Patterns, 2026): highlights the weakness of the handoff from generated hypotheses to executable validation and retained human judgment.
- [Swanson, Undiscovered Public Knowledge](https://doi.org/10.1086/601720) (1986): historical literature-based discovery; a connection suggests a testable hypothesis, not proof.
- [SciFact, Wadden et al.](https://aclanthology.org/2020.emnlp-main.609/) (2020): scientific claims, supporting/refuting rationales and evidence selection.
- [Synthesizing scientific literature with retrieval-augmented language models](https://www.nature.com/articles/s41586-025-10072-4) (2026): measures citation relevance/necessity and recall rather than mere presence.
- [Human evaluation of LLM-generated research ideas](https://proceedings.iclr.cc/paper_files/paper/2025/hash/ea94957d81b1c1caf87ef5319fa6b467-Abstract-Conference.html) (ICLR 2025): feasibility, self-evaluation and diversity challenges justify controls and blinded assessment.
- [ScienceAgentBench](https://proceedings.iclr.cc/paper_files/paper/2025/hash/f12b4df26344f3be803c06b555252efe-Abstract-Conference.html) (ICLR 2025): external expert-reviewed tasks, executable outcomes and costs rather than self-declared discovery.
- [PaperBench](https://proceedings.mlr.press/v267/starace25a.html) (ICML 2025): detailed execution rubrics and separate reproduction/grading environments.

**Research coverage limitation:** This is a focused synthesis from available abstracts, repositories and open research text, not a systematic review of every relevant paper. The protocol is a design recommendation requiring controlled comparison, not a proven optimal architecture.
## Discovery integration · 2026-11-04

`config/discovery-quality-v1.json` selects protocol `discovery-v2` in the existing
`autodiscover discover` command. Existing `discovery-v1` specifications and
saved packets remain readable and replayable. Prompt version `research-quality-v1`
is bound to the new run registration and inference requests. The same three
routes handle planning and evidence extraction, authorship and bridge analysis,
and adversarial critique. The recovery decision is deterministic. Its prompt
guides the critic's candidate query, and the controller enforces the policy.

Captured source ownership, raw/text hashes, access scope, metadata and
invalidation are checked against the catalog. Atomic findings preserve literal
spans and known limitations. Metadata, wrong access scope and context rows
cannot become empirical support. An empirical claim links to valid finding IDs
and receives a separate critic judgment. Critique is advisory and unresolved
material objections or empirical uncertainty prevent advancement. Factual
claims of established advantage and independent replication require external
verification. Proposals with plausible transfer can proceed to external
review as testable, unverified hypotheses when the bridge, assumptions,
comparator, outcome unit, prediction and falsifier are present.

The run permits one targeted search and one revision attempt total across up
to two candidate directions. It skips repeated queries and requires a distinct
substantive source, an extracted new finding and its use in the revision. It
stores original and revised typed attempts and recovery receipts. Unrecoverable
or unresolved cases are rejected or marked inconclusive. Critique coverage
counts distinct candidates with valid review and reports shortfalls against two.
Per-stage usage and recovery calls remain traceable through the run's existing
request ledger and checkpoint keys. The packet retains the original commercial
and scientific authority boundaries.
