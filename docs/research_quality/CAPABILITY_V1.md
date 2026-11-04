# Capability-v1: AI-native invention and open exploration

This is an additive policy of the shared Discovery-v2 engine, selected by `DiscoverySpec.capability`. Historical v1 and v2 specifications without that policy retain their original prompt, provider-manifest and cache identity behavior. No historical packet is migrated or rewritten. [Full requirements](../AI_NATIVE_REQUIREMENTS.md), DEC-026 and [acceptance report](../phase_reports/AI_NATIVE_DISCOVERY_2026-11-04.md) define this milestone.

## Execution and contracts

`config/discovery-capability-v1.json` defines the mission and tracks. The two session-capability profiles embed that same specification; the manifest is `config/discovery-capability-meta.json`. `Discovery.execute` passes the mission, configured tracks and bounded prior research into `CapabilityPlan`. Each direction records a track and selection/change rationale. `ResearchPriority` keeps gap importance, evidence, AI suitability, distinctiveness, plausibility, information gain, experimental feasibility, prior-art uncertainty, usefulness, research cost and historical progress separate. The allocation score is advisory; it cannot establish validity or authorize work. Model estimates can be wrong and require calibration.

The top two directions each receive independent source-domain, target-domain and equivalent-mechanism/product prior-art searches. Both public indexes remain available through the existing allowlist. Captures retain question, direction, retrieval stage, exact spans, access limitations and failures. Two sources per search keep context balanced; bounded retrieval can miss relevant literature. Repeated normalized or near-identical queries are suppressed. A source's domain is not established by its query alone: the extractor must name its actual domain and the critic assesses its substantive support.

Extraction accepts supported limitations, methods and observations independently in each domain. It does not require a published trial of the proposed combination. `GapAnalysis` links a target need and observed constraints to findings, distinguishes speculative constraints and challenges AI against software, process and human alternatives. `CapabilityProposal` adds a versioned `Opportunity` to the existing hypothesis/claims/bridge contract. Its high-reasoning stage deepens AI suitability, alternatives and mechanism analysis. Source and target findings must bind independently for cross-domain transfer. Missing transfer trials remain explicit uncertainty.

An AI-native proposal requires target need evidence, a plausible AI advantage, component support, an explicit bridge, unsupported assumptions, measurable prediction, comparator, minimum effect and falsifier. Independent `CapabilityReview` must support the empirical premises, need, AI suitability and bridge before it is retained for external review. Known equivalent prior art is recorded and does not advance as a novel candidate. Close prior art remains a comparator; an empty search never establishes novelty. No-AI or uncertain-usefulness scientific proposals can remain eligible in Track B. Track B does not require a buyer or demonstrated user problem.

## Epistemic and validation boundaries

1. **Source finding:** exact, owned, substantive captured passage; an extracted statement remains unreviewed until separately assessed. Literal binding is not semantic proof. Review-supported findings are tracked separately.
2. **Proposed mechanism:** explicitly unverified bridge with assumptions and mismatches. A shared keyword is insufficient; a critic can find the transfer unsupported.
3. **Testable hypothesis:** metric, comparator, meaningful effect, falsifier and experiment. It can reach independent critique without prior transfer proof. A retained candidate is `evidence_grounded_hypothesis`, with epistemic state `testable_hypothesis`.
4. **Validated result:** requires qualifying independently evaluated experiments or external evidence under the existing experiment/evidence contracts. Critic enthusiasm cannot produce it.

Opportunity generation is constrained to `validation_status=unverified_idea`, `technical_feasibility=untested`, `scientific_novelty=unverified` and `commercial_validation=unvalidated`. The deterministic candidate gate can label an evidence-grounded hypothesis; it cannot label an experimentally supported, independently replicated or commercially validated result. Those latter statuses require the separate experiment, replication and attested commercial evidence pathways. The current capability workflow does not execute arbitrary proposed experiments or attach automatic validated-opportunity certificates. This is an explicit authority boundary, not an incomplete live experiment claim.

## Progress and recovery

Direction notes retain their own question, gap, issues, sources and child identity. Historical report projections reconstruct these associations from the unchanged child packet. Raw publication and excerpt counts are diagnostic only. Stagnation resets on new critic-supported findings, a distinct provisional candidate, a new critique outcome or a useful reviewed negative result. Unreviewed extraction alone does not count as established knowledge. Duplicate mechanisms and searches remain bounded; lexical similarity can miss paraphrases and semantic equivalence still needs review.

One targeted recovery is allowed per branch. New IDs/passages first justify examining the retrieval; an actual revision requires a newly bound finding in a relevant domain with a different observation and must cite new evidence. A narrower hypothesis then faces independent critique again. An irrelevant source or restatement cannot make recovery successful. Source/target relevance is partly a model judgment, not a universal deterministic semantic verifier. Missing substantive evidence may legitimately close a branch with zero hypotheses.

## Twelve required repair sentinels

| Scenario | Executed regression |
| --- | --- |
| 1. Both supported domains without transfer trial | `test_independent_domains_without_transfer_trial_reach_critique` |
| 2. Title-only empirical support | `test_unsafe_or_unjustified_candidates_do_not_advance[title]` |
| 3. Unmeasured alleged AI superiority | `[advantage]`; validation status remains unverified |
| 4. Defensible provisional AI mechanism | Positive control and `test_two_distinct_provisional_mechanisms_receive_two_critiques` |
| 5. Ordinary software is preferable | `[ordinary]`, `[critic_no_ai]`; open science remains separately eligible |
| 6. Existing equivalent AI product | `[prior_art]`; source-bound equivalent recorded |
| 7. No real user problem/demand | `[no_need]`, open-science-without-user-problem control, prohibited model status promotion |
| 8. No plausible bridge | `[no_bridge]`, `[critic_no_bridge]` |
| 9. Irrelevant new papers | `[irrelevant]` and targeted-recovery irrelevant case |
| 10. Relevant evidence narrows hypothesis | targeted-recovery positive case |
| 11. Different simultaneous evidence gaps | direction-bound summary test and authentic copied qualification replay |
| 12. Different articles without advancement | new-articles stagnation unit test, bounded session stop and accelerated 90-minute run |

The cases are authored structural sentinels. Positive controls make rejecting everything a failure; negative controls make accepting everything a failure. The authentic historical packet and externally annotated SciFact tests remain separate evidence. Independent blinded semantic review remains pending.

## Comparative evaluation

A runs the preserved Discovery-v2 path without capability policy; B uses staged capability research with low reasoning; C uses the same staged inputs with the proposed medium/high allocation. Scripted outputs, corpus and reviewer judgments are matched through schema projections. A can retain a scientifically provisional idea without classifying AI suitability or user need; its broader remit must not be mistaken for an AI-opportunity false acceptance. B and C enforce the new AI-specific scope. The ten matched cases are supplemented by the recovery, summary and stagnation sentinels above. Existing historical twelve-case A/B/C results remain unchanged in BENCHMARK_V1.md.

B and C produce the same decisions by construction. Mock token counts and zero spend are fixture inputs. No real high-reasoning improvement, latency, truncation rate or cost advantage is established. Live measurement must record admissible hypotheses, component grounding, invalid claims, substantive critiques, truncations, latency, reasoning tokens, cost and recovery; never reward answer length or idea volume. Both 4,096 and 8,192 completion settings are exercised through strict simulated Meta HTTP responses. Real sufficiency remains a qualification question.

## Candidate low/medium qualification v2 after timeout — 2026-11-04

The preceding comparison is historical; it does not validate a reasoning optimum. New immutable configuration files `discovery-capability-medium-v2.json`, `discovery-capability-meta-medium-v2.json` and `session-capability-qualification-medium-v2.json` select low planning/extraction, medium gap/proposal/critique and 90/45/60/90/90s stage bounds. AI suitability and mechanistic analysis remain substantive parts of the medium proposal call. Completion limits remain 4,096 for planning/extraction/gap and 8,192 for proposal/critique, inclusive of hidden reasoning. No evidence currently establishes medium superiority, live latency or output sufficiency. The mission, independent cross-domain retrieval, provisional requirements, source verification and independent critique are unchanged.

Both historical live qualifications are preserved, including the first ambiguous planning request in `controlled-capability-wRPtYg`. Never resume either; keep the uncertain $0.077408 hold unresolved. See the current [runbook](../LONG_SESSION_RUNBOOK.md) for provider-record investigation and new-root commands and the [repair report](../phase_reports/META_MEDIUM_QUALIFICATION_2026-11-04.md) for exact local acceptance. The next gate is controlled live Meta qualification, not the 90-minute session.
