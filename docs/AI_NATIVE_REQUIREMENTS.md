# CODEX — Autonomous Discovery Lab: AI-Native Discovery, Research Quality Repair, and Final Long-Session Qualification

## PRIMARY OBJECTIVE

Complete the next implementation and verification milestone for Autonomous Discovery Lab.

The system is already capable of retrieving scientific literature, generating research directions, preserving evidence, and running durable research sessions.

However, the first live Meta qualification revealed an important limitation: it retrieved seven substantive publications but generated zero hypotheses and zero critiques.

We have also identified a mismatch between the project's intended purpose and its current research objectives.

**The primary goal is to discover important gaps in what people, businesses, existing software, and technology can currently accomplish, then investigate whether AI could fill those gaps in a genuinely new way.**

This includes discovering capabilities that do not yet exist, not merely automating existing tasks or adding AI to an established workflow.

The system should use scientific investigation, cross-disciplinary reasoning, technical experimentation, and evidence-based evaluation to develop and test these ideas.

This is not simply an AI startup idea generator.

It is an autonomous invention and discovery system intended to identify new AI-enabled capabilities, investigate how they might work, and determine whether they represent meaningful technical or commercial opportunities.

### Required outcome

Finish implementing and verifying:

1. Explicit AI-native opportunity discovery.
2. Evidence-grounded gap identification.
3. Research into genuinely new AI-enabled mechanisms.
4. Correct separation of hypotheses from validated findings.
5. Improved cross-disciplinary research and retrieval.
6. Stage-specific Meta reasoning configuration.
7. Better research prioritization and candidate evaluation.
8. Repair of the first live qualification's identified weaknesses.
9. Full offline regression and long-session verification.
10. A new, controlled Meta qualification ready to launch.

**I want to be able to run a supervised four-hour autonomous research session after this implementation and its controlled live qualification.**

Do not start the four-hour session during this task.

Do not make paid inference calls without explicit authorization.

Implement everything feasible locally without waiting for further instructions.

---

# 1. RECOVER THE EXISTING PROJECT

Repository:

`Ashleyrfj2/autonomous-discovery-lab`

Most recent verified long-session branch:

`integration/long-session-readiness`

Verified implementation commit:

`7e1720e`

Published HEAD:

`ba17f0d`

Existing verification:

- 324 full tests passed.
- 134 focused tests passed.
- 22 session tests passed.
- Ruff and Pyright passed.
- Package build passed.
- Four-hour accelerated offline simulation passed.
- Separate-process crash recovery passed.
- 33 CLI processes, 132 branches, and 363 mock requests completed during the wall-clock soak.
- Session CLI implements preflight, dry run, start, status, pause, resume, cancel, and report.
- Existing Discovery-v1 and Discovery-v2 replay compatibility must be preserved.

Current operator runbook:

`docs/LONG_SESSION_RUNBOOK.md`

Current phase report:

`docs/phase_reports/LONG_SESSION_READINESS_2026-11-04.md`

Read:

- `AGENTS.md`
- `docs/MASTER_REQUIREMENTS.md`
- `docs/PROJECT_CHARTER.md`
- `docs/ARCHITECTURE.md`
- `docs/TASK_LEDGER.md`
- `docs/DECISION_LOG.md`
- `docs/HANDOFF.md`
- Research-quality documentation
- Latest implementation and qualification reports

Notion recovery handoff:

https://app.notion.com/p/40eec84d128b8133a0cbc94fb267d760

Inspect the latest local and remote state.

Determine whether any newer changes exist before editing.

Preserve all verified work, existing artifacts, and uncommitted changes.

Use a separate integration branch or worktree if appropriate.

Do not restart the project or replace working infrastructure unnecessarily.

---

# 2. PRESERVE AND INVESTIGATE THE FIRST LIVE QUALIFICATION

Historical session:

`session-4374c2fa7c8f44708fef506893831998`

Runtime root:

`runtime/controlled-live`

Status:

`PAUSED`

Stop reason:

`QUALIFICATION_CHECKPOINT`

Observed results:

- Four settled Meta requests.
- Seven substantive publications.
- Eleven source records.
- Zero hypotheses generated.
- Zero critiques completed.
- Zero provider errors.
- Zero unresolved reservations.
- Locally calculated expenditure: $0.012262.
- 109 verified evidence events.
- Provider-confirmed billing remains pending.

The original qualification packet and evidence ledger must remain unchanged.

**Do not resume or rerun the original session.**

It is an important regression baseline.

## Observed failures

### Failure A — Hypothesis generation is overly restrictive

The system investigated whether aviation incident classification methods could improve manufacturing defect detection.

It retrieved substantive aviation and manufacturing research.

However, the evidence extractor required research demonstrating that this specific cross-domain combination already produced comparative improvements.

No such evidence was found, so no hypothesis was generated.

This is appropriate when evaluating an established performance claim, but potentially incorrect when forming a new scientific hypothesis.

### Failure B — Insufficient cross-domain retrieval

The archival-provenance-to-clinical-triage investigation retrieved forensic DNA chain-of-custody research without adequately establishing the clinical domain.

The ecology-to-demand-forecasting investigation retrieved supply-chain forecasting research without substantive ecological evidence.

The system needs to understand both domains independently before deciding that an original connection cannot be investigated.

### Failure C — Cross-direction summary contamination

The session's `next_research` entry combined an aviation/manufacturing question with a clinical-triage evidence gap.

Investigate the source of this mismatch and repair it.

Verify that research summaries, citations, findings, and next-action recommendations remain associated with the correct investigation.

### Failure D — Research progress measured too heavily by retrieval volume

Seven substantive publications were retrieved, but no hypothesis reached critique.

New publications alone must not be treated as sufficient evidence of useful discovery progress.

Measure actual knowledge gained and research advancement.

---

# 3. MAKE AI-NATIVE OPPORTUNITY DISCOVERY AN EXPLICIT OBJECTIVE

This is a core requirement.

The current project configuration uses a generic research objective focused on overlooked cross-disciplinary opportunities.

Replace or extend that objective with an explicit AI-enabled capability-discovery mission.

The system should search for:

- Important problems existing technology cannot adequately solve.
- Work requiring expensive, rare, or inaccessible human expertise.
- Tasks people avoid because of complexity, uncertainty, or required training.
- Information that exists but cannot currently be combined or interpreted effectively.
- Physical-world activities where useful AI assistance is missing.
- Capabilities that new AI architectures, multimodal models, agents, simulations, or verification methods might enable.
- Problems considered impractical because of cost, time, labor, or technical constraints.
- Contradictions between what is theoretically possible and what existing systems actually deliver.
- Opportunities created by connecting methods from unrelated scientific or technical fields.
- Entirely new user experiences or products made possible by AI.

**The goal is not to find places where AI can simply be added. The goal is to identify what AI could newly make possible.**

## Required discovery process

For each serious candidate, investigate:

### A. Identify the gap

What is currently missing, inefficient, inaccessible, unreliable, or impossible?

What evidence demonstrates that limitation?

Who experiences the problem?

What existing approaches have been attempted?

### B. Explain the underlying constraint

Why hasn't the problem already been solved?

Possible explanations include:

- Technological limitations
- Missing information
- Unaffordable expertise
- High operational costs
- Poor integration between systems
- Lack of real-time interpretation
- Insufficient verification
- Human cognitive limitations
- Inadequate interfaces
- Physical-world constraints
- Unresolved scientific mechanisms

Distinguish an observed constraint from a speculative explanation.

### C. Investigate the AI opportunity

Could AI remove or substantially change the constraint?

Consider different technical approaches, including:

- Reasoning models
- Multimodal understanding
- Agent coordination
- Computer use
- Simulation
- World models
- Reinforcement learning
- Human-AI collaboration
- Automated experimentation
- Knowledge representation
- Retrieval and persistent memory
- Independent verification
- Computer vision
- Speech and interaction
- Robotics and physical-world intelligence

Do not assume an LLM is always the right solution.

Consider combinations of AI and non-AI methods.

### D. Propose something genuinely different

What new capability or mechanism is being proposed?

Why might it work?

What evidence supports the underlying components?

Which parts remain hypothetical?

What would make it meaningfully different from existing products, research, or workflows?

### E. Challenge the AI requirement

Could ordinary software, better process design, human expertise, or an existing product solve the same problem more efficiently?

If AI provides no meaningful advantage, do not classify the idea as a strong AI opportunity.

### F. Evaluate technical feasibility

Identify:

- Required models and tools
- Data requirements
- Model limitations
- Integration requirements
- Safety and reliability concerns
- Verification methods
- Deployment constraints
- Cost considerations
- Experiments needed

### G. Evaluate potential usefulness

Determine:

- Who benefits
- Frequency and severity of the problem
- Potential magnitude of improvement
- Existing alternatives
- Economic buyer, if applicable
- Evidence of actual demand
- Barriers to adoption

Do not invent market demand.

A technically interesting idea is not automatically a business opportunity.

---

# 4. PRESERVE BROAD SCIENTIFIC EXPLORATION

AI-enabled discovery should become an explicit primary track.

However, do not force every scientific hypothesis into an AI product.

Preserve two related research pathways:

**Track A — AI-Native Capability Discovery**

Primary objective: Identify unmet needs and investigate new AI-enabled mechanisms or capabilities.

**Track B — Open Scientific and Technical Exploration**

Investigate promising discoveries across any field, including findings that are not immediately AI-related.

Track B may feed discoveries into Track A when a useful AI application becomes apparent.

Research directions may move between tracks with recorded justification.

Maintain the open-industry mission.

Creative markets, gaming, social platforms, entertainment, consumer technology, education, healthcare, manufacturing, and other sectors remain eligible.

Do not prioritize an industry merely because it is fashionable.

Prefer opportunities with strong evidence, meaningful technical potential, and credible practical usefulness.

Make track selection configurable and record which track produced each candidate.

Do not implement duplicate research engines if the existing Discovery-v2 architecture can support both tracks.

---

# 5. REPAIR THE HYPOTHESIS-FORMATION PROCESS

This is necessary before the next paid qualification.

## Separate four epistemic states

### State 1 — Verified source finding

An empirical statement supported by an exact source passage.

Must pass source ownership, provenance, citation, and substantive-support checks.

### State 2 — Proposed mechanism

A scientifically or technically plausible explanation connecting known findings.

Its assumptions and unsupported elements must be explicit.

### State 3 — Testable hypothesis

A prediction about what could happen if the proposed mechanism is applied.

Must include a metric, comparator, falsifier, and meaningful outcome.

It does not require prior experimental proof of the proposed result.

### State 4 — Validated result

A demonstrated outcome supported by qualifying experiments or external evidence.

Do not promote a hypothesis into this state merely because a model considers it plausible.

## Critical acceptance behavior

The system must be able to say:

"These source-domain findings and target-domain findings are supported. Their combination has not been validated. Here is a plausible mechanism, a predicted result, the assumptions involved, and a controlled experiment that could falsify it."

That should qualify for independent critique when the underlying evidence is sufficient.

It must not be incorrectly rejected solely because no study has already demonstrated the cross-domain improvement.

At the same time, do not weaken:

- Citation validity
- Source ownership
- Empirical claim grounding
- Prior-art screening
- Unsupported-superiority rejection
- Experiment requirements for validated claims
- Commercial evidence requirements

A claim that an AI system already outperforms an established method must require actual supporting evidence.

A proposed experiment to determine whether it could outperform that method does not.

---

# 6. IMPROVE RESEARCH RETRIEVAL AND CROSS-DOMAIN REASONING

For cross-disciplinary hypotheses, use a staged retrieval strategy.

### Stage 1 — Source domain

Investigate the established mechanism and supporting findings in the first field.

### Stage 2 — Target domain

Investigate the actual problem, conditions, and existing solutions in the second field.

### Stage 3 — Mechanistic bridge

Identify:

- Shared variables
- Transferable mechanisms
- Domain differences
- Required assumptions
- Failure modes
- Relevant comparators
- Missing evidence

### Stage 4 — Prior art

Search for equivalent or closely related combinations.

Do not use an empty result set as proof of novelty.

### Stage 5 — Testable proposal

Generate a provisional hypothesis when the evidence supports a defensible experiment.

Missing direct-transfer studies should be treated as an uncertainty, not an automatic rejection.

## Retrieval efficiency

Do not repeatedly submit near-identical searches.

Require meaningful information gain for targeted recovery.

New source IDs alone are not enough.

Prioritize relevance, substantive passages, and domain coverage over raw retrieval counts.

Record search failures and retrieval limitations.

---

# 7. IMPLEMENT STAGE-SPECIFIC META REASONING

The current provider configuration uses minimal reasoning for Spark models and low reasoning for Wonder.

Test a more capable configuration.

### Proposed reasoning allocation

| Stage | Proposed reasoning |
| --- | --- |
| Research planning | Medium |
| Routine retrieval classification | Low |
| Atomic evidence extraction | Low |
| Gap identification | Medium |
| AI opportunity analysis | High |
| Mechanistic bridge analysis | High |
| Hypothesis generation | High |
| Independent adversarial critique | High |
| Recovery routing | Low or medium |
| Final synthesis | Medium or high when justified |

These are hypotheses about configuration quality, not established optimal settings.

Verify supported reasoning levels against the actual Meta API and each configured model.

If multiple stages share one provider route, implement stage-specific overrides instead of changing every request globally.

Preserve distinct model identities where required for independent critique.

## Token and timeout configuration

The current output limit is 2,560 completion tokens.

Higher reasoning may use substantial hidden reasoning tokens and leave insufficient room for structured responses.

Evaluate 4,096 and 8,192 completion-token limits for complex stages, where supported.

Review the existing 25-second provider timeout.

Use a longer timeout only when justified by provider behavior and compatible with the existing branch deadline.

Preserve:

- Bounded execution
- Cancellation
- Durable reservations
- Token accounting
- Ambiguous-dispatch handling
- Structured-output validation
- Exact replay

A timeout must not cause silent duplicate billable requests.

## Evaluate reasoning changes

Compare the existing settings with the proposed stage-specific settings.

Measure:

- Valid hypothesis formation
- Quality of mechanistic reasoning
- Evidence support
- Invalid claims
- Substantive critique coverage
- Output truncation
- Latency
- Reasoning tokens
- Total cost
- Recovery behavior

Use offline fixtures for initial testing.

If live comparisons are necessary, prepare them separately and request authorization.

Do not assume high reasoning is automatically better.

Do not measure success by answer length or number of ideas generated.

---

# 8. ADD AN AI OPPORTUNITY EVALUATION CONTRACT

Each serious AI-native discovery candidate should record:

- Identified unmet need
- Source evidence for the need
- Current workaround
- Existing products and research
- Root constraint
- Proposed AI-enabled capability
- Proposed technical mechanism
- Why AI is appropriate
- Non-AI alternatives
- Evidence supporting component mechanisms
- Unsupported assumptions
- Technical dependencies
- Differentiation from prior art
- Falsifiable prediction
- Evaluation dataset or environment
- Comparator
- Minimum meaningful improvement
- Technical feasibility status
- Scientific novelty status
- Target user
- Economic buyer
- Commercial validation status
- Next cheapest useful experiment

Keep distinct statuses for:

- Unverified idea
- Evidence-grounded hypothesis
- Experimentally supported result
- Independently replicated result
- Commercially validated opportunity

Do not allow model enthusiasm to advance validation status.

Avoid forcing existing historical Discovery-v1 and Discovery-v2 packets into an incompatible new schema.

Use versioned contracts or backward-compatible additions.

---

# 9. IMPROVE LONG-SESSION RESEARCH PRIORITIZATION

The existing four-hour controller is technically implemented.

Improve the selection of research directions without rebuilding the scheduler.

Prioritize based on:

- Importance of the underlying gap
- Strength of evidence that the gap exists
- Degree to which AI could change the constraint
- Distinctiveness of the proposed capability
- Technical plausibility
- Information gain
- Experimental feasibility
- Prior-art uncertainty
- Potential usefulness
- Estimated research cost
- Historical research progress

Separate AI suitability from novelty.

A problem can be important without requiring AI.

An idea can be novel without being useful.

An AI approach can be technically plausible without being commercially viable.

## Long-session stagnation detection

Do not treat unrelated new articles as continuous meaningful progress.

Measure:

- New independently supported findings
- Newly identified limitations
- New mechanistic relationships
- Valid provisional hypotheses
- Independent critique outcomes
- Resolved research uncertainty
- Useful negative results
- Duplicate hypotheses
- Repeated searches
- Actual progress toward experimental validation

When a research direction stops yielding useful information, the controller should change direction or stop.

Prevent circular research loops and repeated paid calls.

Retain an auditable explanation for why each branch continued or stopped.

---

# 10. EXPAND THE OFFLINE BENCHMARKS

Preserve all existing research-quality tests.

Add focused regression cases for the first live qualification.

### Required scenarios

1. Two independently supported domains with no existing cross-domain trial. The system should produce a provisional testable hypothesis if a defensible mechanism exists.
2. A supposed empirical finding supported only by a publication title. Must reject.
3. A proposed AI advantage with no measured comparison. Must remain unverified.
4. A defensible AI-native mechanism with known assumptions. May advance to critique.
5. A problem better solved by ordinary software. Must not be promoted as a strong AI opportunity merely because AI could be used.
6. An AI product idea that already exists. Must record prior art rather than assert novelty.
7. A technically interesting proposal without evidence of a real user problem. Must not be commercially validated.
8. A cross-domain proposal with no plausible transfer mechanism. Must fail or remain inconclusive.
9. New sources that are substantively irrelevant. Must not incorrectly trigger successful recovery.
10. Valid new evidence supporting a narrower revised hypothesis. Must allow justified recovery.
11. Two simultaneous research directions with different evidence gaps. Must never mix their summaries.
12. Multiple branches that retrieve different papers but produce no meaningful research progress. Must eventually stop or change strategy.

Include positive controls.

A system that rejects everything must fail the benchmark.

A system that accepts every speculative AI idea must also fail.

## Comparative evaluation

Compare:

A. Current verified Discovery-v2 behavior.

B. Corrected hypothesis formation and staged retrieval.

C. Corrected research with stage-specific reasoning and AI-native discovery.

Control the offline fixture inputs and model behavior.

Distinguish structural tests from independently reviewed semantic outcomes.

Do not claim that mocked high reasoning demonstrates a real high-reasoning performance gain.

Preserve the previous A/B/C evaluation as historical evidence.

---

# 11. VERIFY THE LONG-SESSION SYSTEM

Run all applicable validations:

- Ruff
- Pyright
- Full pytest suite
- Focused Discovery-v2 tests
- AI opportunity contract tests
- Research-quality regressions
- Session controller tests
- Replay and provenance tests
- Cancellation tests
- Cross-process recovery tests
- Provider accounting tests
- Ambiguous dispatch tests
- Token limit tests
- Structured-output tests
- CLI smoke tests
- Package build

Run an accelerated multi-hour simulation using the updated research objectives.

Verify that it can:

1. Select research gaps autonomously.
2. Investigate both relevant domains.
3. Produce defensible provisional hypotheses.
4. Reject unsupported claims.
5. Critique promising proposals independently.
6. Record technical and commercial uncertainty.
7. Change directions when research stagnates.
8. Recover without repeating settled paid requests.
9. Produce complete evidence-linked reports.
10. Stop reliably when operating limits are reached.

Also confirm that the historical live qualification still replays exactly.

Do not modify its stored data.

---

# 12. PREPARE THE NEXT CONTROLLED META QUALIFICATION

After all offline checks pass, prepare a **new controlled Meta qualification**.

Use a new runtime root.

Do not overwrite `runtime/controlled-live`.

The next qualification should verify:

- Genuine live Meta inference
- Stage-specific reasoning configuration
- Real public-source retrieval
- Evidence-grounded gap detection
- Independent source-domain research
- AI-native opportunity analysis
- Provisional hypothesis generation
- Independent critique
- Prior-art analysis
- Correct uncertainty labeling
- Request accounting
- Source ownership
- Exact replay
- Pause/resume behavior

A qualification may legitimately produce zero hypotheses when no defensible idea exists.

However, it must demonstrate that valid provisional hypotheses are not systematically screened out.

A passing operational qualification should include a substantive critique from the real-provider path.

If the selected research question does not produce one, report the result accurately and determine whether another bounded qualification is justified.

Do not weaken scientific standards to force success.

## Spending policy

Do not make paid requests during this Codex task without explicit authorization.

The user previously removed the historical per-call, per-run, daily, and qualification dollar caps.

Do not silently reintroduce those values.

Preserve request, token, duration, retry, concurrency, and cancellation controls.

The optional aggregate dollar ceiling may remain configurable.

Recalculate the conservative usage estimate based on the actual new reasoning, output-token, and timeout configuration.

The historical $1.45552 estimate is no longer authoritative if the configuration changes.

If the updated qualification exceeds the selected session limits, adjust the profile deliberately and document the new maximum before any live execution.

Keep credential values out of logs, reports, and commits.

---

# 13. CONTEXT PRESERVATION AND DOCUMENTATION

Maintain durable context throughout the task.

At each significant phase boundary, record:

- Current branch and commit
- Completed implementation
- Tests passed
- Tests failed
- Decisions made
- Research findings
- Unresolved defects
- Next implementation action
- Any verification limitations

Update:

- Existing project charter or requirements when needed
- Decision log
- Requirements traceability
- Task ledger
- Research-quality documentation
- Long-session operator runbook
- Phase report
- Notion recovery handoff

Do not create conflicting duplicate status documents.

If Notion is unavailable, retain a complete repository handoff.

Do not repeat already verified work without a technical reason.

If an approach becomes stuck, document the failure, investigate alternatives, and continue other useful work.

External technical documentation and live web research are allowed.

Do not turn implementation into endless background research.

---

# 14. COMMIT AND PUBLISH

Commit verified implementation in logical stages.

Keep unrelated work unchanged.

Do not overwrite historical runtime artifacts.

Do not force-push.

Do not merge PR #2 automatically.

Push the completed integration branch when safe.

Run final tests on the committed state.

Document the exact commit and verification evidence.

---

# 15. FINAL DELIVERABLES

Produce an updated implementation report covering:

### AI-NATIVE DISCOVERY

Is the system now explicitly searching for gaps that AI could fill in genuinely new ways?

Show the actual configuration, prompts, contracts, and execution path.

### HYPOTHESIS GENERATION

Was the overly restrictive evidence requirement repaired?

Can scientifically defensible but unverified connections advance to critique?

### REASONING CONFIGURATION

Which Meta reasoning levels and output limits are configured for each stage?

What was actually tested?

What remains to be verified with real inference?

### RESEARCH RETRIEVAL

Can the system investigate both domains independently and assess mechanistic transfers?

### QUALITY AND SAFETY

Are empirical claims, citations, novelty, and commercial validation still appropriately gated?

### LONG-SESSION READINESS

Did the updated four-hour offline simulation pass?

Do recovery and stagnation handling still work?

### EXPENDITURE

Confirm whether any paid calls occurred.

Provide the recalculated qualification and long-session conservative maximum usage estimates.

### GIT STATUS

Provide branch, commits, test counts, push status, and PR status.

### FINAL READINESS

Explicitly assess:

- Offline implementation: PASS/FAIL
- Full local regression: PASS/FAIL
- Controlled Meta qualification: GO/NO-GO
- Supervised four-hour session: GO/CONDITIONAL GO/NO-GO
- Fully unattended overnight operation: GO/NO-GO

---

# 16. EXACT COMMANDS REQUIRED

At the end, provide the actual commands for:

1. Entering the correct project directory.
2. Setting the existing credentials path without exposing the key.
3. Preflighting the updated qualification.
4. Running a non-billable dry run.
5. Starting a new controlled Meta qualification.
6. Inspecting the qualification checkpoint.
7. Reviewing model usage and generated hypotheses.
8. Resuming the qualification.
9. Generating the final qualification report.
10. Launching the supervised four-hour session after qualification passes.
11. Monitoring, pausing, resuming, and cancelling the long session.

All commands must match the implemented CLI.

Use a new runtime root for the next qualification.

---

## NON-NEGOTIABLE SUCCESS CRITERIA

This task is finished when:

- The AI-native discovery objective is genuinely integrated into execution, not merely added to documentation.
- Gap identification and AI suitability analysis are functional.
- The hypothesis-versus-validation problem has been corrected.
- Both-domain retrieval and prior-art checks work.
- Explicitly provisional inventions can reach independent critique.
- Stage-specific reasoning is implemented and safely configured.
- The previous live failure patterns have regression coverage.
- Research summaries remain associated with the correct directions.
- Full offline tests pass.
- Extended session execution remains reliable.
- Existing historical evidence remains replayable.
- Updated usage estimates are documented.
- The new controlled Meta qualification is ready to run.
- Verified changes are committed and the handoff is current.

### Final instruction

**Do not stop after producing an implementation plan.**

Implement the changes, run the tests, resolve reproducible failures, document the results, and commit verified work.

Do not spend credits, launch a paid qualification, or begin the four-hour session without explicit authorization.

Do not declare success simply because the system generates more hypotheses.

The objective is to build a system that can independently discover real gaps, investigate genuinely new AI-enabled capabilities, challenge its own assumptions, and determine which ideas deserve further technical or commercial validation.

When finished, I should be able to run one short controlled qualification and, if that passes, start a supervised four-hour autonomous discovery session without another major implementation phase.
## Subsequent user steering (2026-11-04)

"Lets do 1.5 hours instead of 4"

The supervised operating target is now 90 minutes (5,400 seconds). Update the current capability profile, accelerated acceptance, usage estimate and operator launch commands accordingly. This changes duration only; paid qualification and live session authorization are still required. Historical four-hour implementation and evidence remain preserved.

## Subsequent user steering — timeout repair and short medium qualification (2026-11-04)

Preserve both live qualifications and all evidence. Never resume the failed planning session `session-4c376b05f4e8440aab2d15c30a603ec8` / `runtime/controlled-capability-wRPtYg`; leave its UNCERTAIN $0.077408 hold untouched. No reported tokens does not establish processing or billing outcome. Document provider-record investigation before any newly authorized paid test; retain unresolved status if unconfirmed.

Create new versioned qualification files with low planning/extraction and medium gap, AI suitability/mechanistic analysis, hypothesis generation and independent critique. Candidate timeouts: 90/45/60/90/90 seconds; align provider transport/stage bounds and branch/session duration. Preserve mission, independent retrieval, provisional hypotheses, provenance, request ledger, ambiguity/retry/cancellation/usage/identity/schema/cache/redaction safeguards and removed dollar caps. Calculate the actual conservative inclusive reasoning/output envelope. Verify HTTP slow/timeout/interruption/structured/uncertain cases, complete offline capability rehearsal, Ruff/Pyright/full/focused pytest/build. Preserve saved-session profiles. Update runbook/handoff/history/traceability/Notion, commit and push verified changes. Do not start paid qualification. Next milestone is a successful controlled live Meta test; 90-minute operation remains deferred. Medium superiority requires actual comparative evidence. DEC-028 and phase_reports/META_MEDIUM_QUALIFICATION_2026-11-04.md record implementation and acceptance.

## Subsequent user steering — evidence-role repair (2026-11-04)

Separate unmet-need evidence from mechanism evidence and measured-improvement evidence. Admit relevant contextual findings into gap analysis without causal/efficacy promotion. Reject placeholder fields (including #TODO), internally inconsistent typed outputs and meaningless units. Require explicit support for observed constraints. Regress against the saved medium qualification without modifying historical evidence. Verify offline both a legitimate provisional hypothesis reaching independent critique and unsupported proposals remaining rejected. DEC-029 and phase_reports/EVIDENCE_ROLES_REPAIR_2026-11-04.md define implementation/acceptance; historical sessions remain preserved, no paid calls or historical resume in this repair.
