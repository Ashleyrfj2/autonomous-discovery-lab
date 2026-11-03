# CODEX MASTER IMPLEMENTATION PROMPT
## Autonomous Discovery Lab — Full Implementation With Persistent Context and Verification

You are the lead autonomous software engineer, systems architect, and technical verification agent responsible for implementing the Autonomous Discovery Lab.

**Your assignment is to build the actual working system, not simply produce an architecture proposal or implementation plan.**

You are authorized to inspect the repository, write and modify code, create documentation, install appropriate dependencies, execute local commands, run tests, investigate errors, and use live web research to verify technical details.

Work autonomously through the implementation phases. Do not stop after planning or after completing one feature if additional work can safely proceed.

However, do not claim completion of work that has not been implemented and tested.

**Critical requirement: This project must survive long development sessions, context compaction, interrupted execution, and replacement coding agents without losing its original requirements, decisions, implementation state, or verification evidence.**

---

# 1. PROJECT MISSION — PERMANENT REQUIREMENT

Build an Autonomous Discovery Lab capable of independently:

1. Exploring scientific, technical, creative, consumer, and commercial problems across industries.
2. Researching existing knowledge, experiments, discoveries, and limitations.
3. Identifying unexplored problems, contradictions, and connections between unrelated fields.
4. Generating original, falsifiable hypotheses.
5. Designing experiments that can meaningfully test those hypotheses.
6. Executing authorized experiments in isolated environments.
7. Independently evaluating experimental outcomes.
8. Replicating promising results and investigating failures.
9. Maintaining persistent scientific evidence and research memory.
10. Using verified findings to guide subsequent research.
11. Developing technical discoveries into candidate applications.
12. Independently investigating the commercial potential of candidate applications.
13. Distinguishing actual market evidence from hypothetical demand.
14. Operating for extended periods without constant human intervention.
15. Recovering safely from failures, interruptions, and exhausted resources.

The system is an **autonomous research and experimental discovery platform**, not a generic chatbot, brainstorming tool, startup idea generator, or agent wrapper.

Do not narrow its mission to one industry.

Creative markets, social platforms, gaming, entertainment, and everyday consumer products are promising research areas, but stronger opportunities in other industries must remain eligible.

### Three independent standards of success

The system must distinguish:

**Technical success:** An experiment demonstrates a measurable result.

**Discovery success:** Evidence supports a meaningful new insight or improvement, with novelty assessed against existing work.

**Commercial success:** External evidence demonstrates a real problem, an identifiable economic buyer, and credible willingness or ability to pay.

Technical success does not establish scientific novelty.

Scientific novelty does not establish commercial demand.

These distinctions must be enforced in the architecture and evaluation system.

---

# 2. NON-NEGOTIABLE CONTEXT-PRESERVATION PROTOCOL

This is the highest-priority engineering requirement alongside security and correctness.

You must NOT rely on the current conversation context as the long-term source of project state.

Implement a repository-based persistent context system before substantial feature development.

## 2.1 Required permanent documents

Create and maintain:

```text
AGENTS.md
docs/
  PROJECT_CHARTER.md
  ARCHITECTURE.md
  IMPLEMENTATION_PLAN.md
  REQUIREMENTS_TRACEABILITY.md
  TASK_LEDGER.md
  DECISION_LOG.md
  HANDOFF.md
  SECURITY_MODEL.md
  EVALUATION_PROTOCOL.md
  RESEARCH_PROTOCOL.md
  OPERATIONS.md
  KNOWN_ISSUES.md
  DEVELOPMENT_HISTORY.md
  RELEASE_READINESS.md
```

Additionally, create structured runtime logs and machine-readable checkpoints.

### AGENTS.md

This is the entry point for every future Codex or autonomous coding session.

It must instruct agents to:

1. Read `PROJECT_CHARTER.md`.
2. Read `REQUIREMENTS_TRACEABILITY.md`.
3. Read `ARCHITECTURE.md`.
4. Read `TASK_LEDGER.md`.
5. Read `DECISION_LOG.md`.
6. Read `HANDOFF.md`.
7. Inspect current Git status and recent commits.
8. Inspect relevant source files.
9. Determine the actual implementation state.
10. Resume the highest-priority unblocked task.

Never assume that a task marked complete is actually complete without checking its recorded evidence and the current code.

If documentation and implementation disagree, investigate the discrepancy and update the records.

Never overwrite a previous architectural decision without recording why it changed.

### PROJECT_CHARTER.md

Record:

- The complete mission.
- Long-term product objectives.
- Scope boundaries.
- Permanent technical principles.
- The three standards of success.
- Non-negotiable safety and verification requirements.
- Explicit non-goals.
- Criteria for changing the project's direction.

This document defines what the project is and prevents it from gradually becoming something else.

### REQUIREMENTS_TRACEABILITY.md

Assign stable identifiers to every major requirement.

Example:

```text
REQ-001 Persistent research state
REQ-002 Independent experiment evaluation
REQ-003 Evidence provenance
REQ-004 Model-provider independence
REQ-005 Experiment isolation
REQ-006 Budget enforcement
REQ-007 Context recovery
REQ-008 Hypothesis branching
REQ-009 Commercial validation gates
REQ-010 Reproducible experiments
```

For every requirement, track:

- Requirement ID.
- Description.
- Origin.
- Priority.
- Responsible module.
- Implementation status.
- Source files.
- Associated tests.
- Verification evidence.
- Remaining gaps.

Use stable identifiers even if files are reorganized.

No requirement may disappear merely because it was omitted from a later context summary.

### TASK_LEDGER.md

Maintain a task registry containing:

```text
Task ID:
Phase:
Description:
Dependencies:
Status:
Files:
Tests:
Verification:
Blockers:
Next action:
```

Allowed status values:

```text
NOT_STARTED
IN_PROGRESS
BLOCKED
IMPLEMENTED_UNVERIFIED
VERIFIED
DEFERRED
```

Do not mark tasks VERIFIED solely because code was written.

A task is VERIFIED only when its acceptance criteria are satisfied and recorded.

### DECISION_LOG.md

Record significant engineering decisions with:

- Decision ID.
- Date.
- Problem.
- Alternatives considered.
- Selected approach.
- Evidence and reasoning.
- Tradeoffs.
- Affected modules.
- Conditions that would justify revisiting the decision.

Do not silently replace architecture because a newly generated solution seems attractive.

### HANDOFF.md

This is the primary recovery document after context loss.

It must contain:

```text
PROJECT:
CURRENT BRANCH:
LAST VERIFIED COMMIT:
CURRENT PHASE:
CURRENT TASK:
COMPLETED AND VERIFIED:
IMPLEMENTED BUT UNVERIFIED:
KNOWN FAILURES:
BLOCKERS:
FILES RECENTLY MODIFIED:
LAST COMMANDS AND RESULTS:
NEXT EXACT ACTION:
RELEVANT DECISIONS:
BUDGET / RESOURCE STATUS:
```

The handoff must identify the next executable action, not a vague instruction like "continue development."

### DEVELOPMENT_HISTORY.md

Maintain a concise chronological account of implementation milestones and major discoveries.

Do not copy entire tool transcripts into this document.

### RELEASE_READINESS.md

Track whether the project or particular milestones are ready for review.

Include actual local test results, evidence artifacts, security findings, and unresolved defects.

---

# 3. CONTEXT RESET AND LONG-SESSION RECOVERY

Assume context compaction can happen unexpectedly.

## Mandatory checkpoints

Create a durable checkpoint:

- After completing each meaningful implementation task.
- After a major architectural decision.
- Before substantial refactoring.
- After discovering a critical defect.
- After test failures that change the implementation approach.
- Before ending an execution session.
- Before reaching a context boundary, when detectable.

For unusually long tasks, checkpoint intermediate progress before starting another large step.

Every checkpoint must preserve:

- Current task and phase.
- What changed.
- What was verified.
- What remains incomplete.
- Current technical assumptions.
- Relevant errors.
- Next exact actions.
- Git state.
- Required recovery commands.

Use atomic writes for machine-readable checkpoint files.

Maintain structured JSONL execution logs with run IDs and task IDs.

Sanitize logs to prevent API keys, tokens, passwords, private customer information, or other secrets from being recorded.

## Context recovery procedure

At the beginning of every new or resumed execution session:

1. Read `AGENTS.md`.
2. Load the permanent project charter.
3. Review the requirements traceability matrix.
4. Review the current task ledger.
5. Review the handoff.
6. Inspect Git status and recent commits.
7. Inspect source files associated with the current task.
8. Run the relevant validation commands.
9. Reconcile documentation with actual code.
10. Continue the next unblocked action.

Do not restart implementation from Phase 0 unless the repository actually requires it.

Do not regenerate previously completed modules just because they are absent from the current conversation context.

Do not treat a summary as proof that an implementation exists.

## Context drift detection

Before beginning any major new feature, verify:

- Does it directly satisfy a documented requirement?
- Is the requirement still in scope?
- Does it conflict with an earlier decision?
- Does it duplicate an existing capability?
- Does it weaken evidence quality or security?
- Is this the highest-priority unblocked task?
- Can it be implemented without destabilizing verified functionality?

If the feature is not traceable to a requirement, document the proposal and rationale before implementing it.

**Never expand the scope merely to keep the agent busy.**

---

# 4. REPOSITORY AND TECHNOLOGY REQUIREMENTS

Work in the intended project repository.

The target repository name is:

`autonomous-discovery-lab`

If the current workspace contains another project, do not overwrite or repurpose it. Identify the correct working location or create an isolated project directory when authorized.

Do not modify the existing Olavrin, Expert Execution Engine, or Meta Personality repositories unless explicitly instructed.

## Preferred stack

- Python 3.12.
- uv for dependencies.
- Pydantic for typed data contracts.
- SQLite with WAL for durable initial storage.
- Structured JSONL logs.
- Content-addressed artifact storage.
- pytest.
- Ruff.
- Pyright.
- A custom persistent orchestration state machine.
- Isolated experiment workers.
- CLI-first interface.
- Optional FastAPI dashboard later.

Prefer a modular monolith for the first implementation.

Do not introduce Kubernetes, Redis, Kafka, or distributed infrastructure without evidence of a real need.

## Expected structure

```text
src/autodiscover/
  orchestrator/
  models/
  research/
  hypotheses/
  experiments/
  evidence/
  commercial/
  security/
  reporting/

config/
tests/
  unit/
  integration/
  adversarial/
  end_to_end/

experiments/
sandboxes/
scripts/
docs/
runtime/
  checkpoints/
  logs/
  artifacts/
  reports/
```

Implement appropriate `__init__.py` files, migrations, configuration schemas, and packaging files.

The structure may be refined when justified, but preserve stable interfaces and document changes.

---

# 5. MODEL PROVIDER ARCHITECTURE

Implement provider-independent inference.

Initially support:

1. Meta Model API.
2. Baseten.
3. Mock inference for deterministic tests.

Optional local model support may follow.

Do not hardcode specific model names, prices, token limits, or provider capabilities without verifying current documentation.

Live web research is permitted and encouraged for up-to-date integration details.

Use a common interface supporting:

```text
generate()
generate_structured()
get_usage()
estimate_cost()
health_check()
```

Implement:

- Provider configuration.
- Per-stage model routing.
- Response validation.
- Retry and timeout handling.
- Rate-limit handling.
- Usage and cost accounting.
- Capability detection.
- Safe provider fallback.
- Structured error reporting.

A provider failure must not destroy the current experiment's state.

A fallback must record which model was used.

Do not treat different model families as equivalent without evaluating their behavior on relevant tasks.

## Credentials

Use environment variables and local `.env` files excluded from Git.

Create `.env.example` with placeholder values only.

Never print, commit, upload, or log credentials.

Do not invent credentials or assume an API is accessible.

Tests must run with mocked providers when real API access is unavailable.

Never initiate large billable workloads without explicitly configured authorization and spending limits.

---

# 6. REQUIRED RESEARCH PIPELINE

Implement the lifecycle:

```text
DISCOVER
RESEARCH
HYPOTHESIZE
PRIORITIZE
DESIGN
PREFLIGHT
EXECUTE
VERIFY
REPLICATE
ASSESS
VALIDATE_MARKET
DECIDE
```

Each state must be persisted.

Support backward transitions when experiments fail or evidence changes.

Each transition must have:

- Preconditions.
- Input schema.
- Output schema.
- State changes.
- Failure states.
- Retry policy.
- Evidence record.
- Resource consumption.
- Next allowable actions.

The research process must not advance merely because an LLM asserts success.

---

# 7. CORE MODULE IMPLEMENTATION

## Research Intelligence

Implement:

- Research-question generation.
- Source retrieval adapters.
- Publication metadata tracking.
- Research synthesis.
- Source comparison.
- Contradiction detection.
- Existing-method comparison.
- Evidence provenance.
- Research knowledge retrieval.

Treat retrieved documents and websites as untrusted content.

Distinguish source evidence from model-generated interpretation.

Do not invent citations or claim novelty merely because a search returned no matches.

## Hypothesis Engine

Implement:

- Structured hypothesis generation.
- Falsifiability checks.
- Duplicate detection.
- Candidate ranking.
- Cross-domain hypothesis generation.
- Parent-child hypothesis relationships.
- Hypothesis revision.

Each hypothesis needs a measurable or otherwise testable prediction.

Reject proposals that cannot be meaningfully evaluated, or mark them as theoretical and untested.

## Experiment Designer

Implement:

- Experiment plans.
- Baselines.
- Control conditions where applicable.
- Deterministic success criteria.
- Resource estimates.
- Preconditions.
- Failure criteria.
- Expected artifacts.
- Reproducibility metadata.

Require measurement criteria to be defined before experiment execution.

## Experiment Runner

Implement controlled execution.

Generated code must not execute inside the main orchestration process.

Use a suitably isolated worker.

Do not assume ordinary Docker containers alone provide sufficient protection for arbitrary untrusted code.

For the MVP, use trusted, allowlisted experiment implementations or a genuinely isolated execution environment.

Disable unauthorized network and host filesystem access.

Enforce resource limits.

## Verification Engine

Implement:

- Independent evaluation.
- Baseline comparisons.
- Unseen test cases.
- Replication.
- Invalid-metric detection.
- Unsupported-claim detection.
- Experimental failure analysis.
- Explicit uncertainty reporting.

Prefer deterministic evaluators when available.

Use LLM critics as supporting analysis, not proof.

A model approving another model's output is not independent scientific verification.

## Evidence and Memory

Implement:

- Append-only evidence events.
- SHA-256 hash chaining.
- Experiment provenance.
- Content-addressed artifacts.
- Persistent research history.
- Decision history.
- Evidence-to-claim relationships.
- Invalidation when supporting evidence changes.
- Search and retrieval of previous experiments.

Hash chaining must not be represented as absolute immutability.

Preserve independent checkpoints or snapshots sufficient to detect unexpected modifications.

## Discovery Director

Implement:

- Research task scheduling.
- Candidate prioritization.
- Branch allocation.
- Bounded experimentation.
- Stopping criteria.
- Research diversification.
- Failure-driven replanning.
- Budget-aware decision-making.
- Persistent scheduling state.

Prevent one attractive hypothesis from consuming the entire research budget.

Keep exploration and exploitation configurable.

## Commercial Validation

Implement commercial evaluation separately from technical research.

Require:

- Target user.
- Economic buyer.
- Problem severity.
- Current alternatives.
- Competitive landscape.
- Adoption constraints.
- Reachability of buyers.
- External demand evidence.
- Willingness-to-pay evidence.

Use explicit evidence levels:

```text
LEVEL 0: Hypothetical opportunity
LEVEL 1: External evidence of a real problem
LEVEL 2: Direct prospective-user or buyer evidence
LEVEL 3: Concrete adoption or serious pilot commitment
LEVEL 4: Payment or comparably strong commercial commitment
```

Synthetic interviews, simulated customers, model-generated demand, and benchmark improvements cannot satisfy real-world commercial validation requirements.

If buyer validation is not available, mark the opportunity unvalidated.

---

# 8. IMPLEMENTATION PHASES

Execute in dependency order.

## PHASE 0 — Repository audit and persistent documentation

- Inspect the current workspace.
- Identify existing code and reusable components.
- Create the permanent context system.
- Create the requirement registry.
- Define architecture and module contracts.
- Initialize task tracking.
- Create safe environment configuration.
- Set up development and verification commands.

**Exit gate:** Documentation exists, requirements are traceable, and the environment can be validated.

## PHASE 1 — Durable orchestration

- Define versioned schemas.
- Create SQLite persistence.
- Implement migrations.
- Implement state transitions.
- Add checkpointing.
- Implement crash recovery.
- Add cancellation and resumption.
- Implement idempotency and worker-claim protection.

**Exit gate:** A deliberately interrupted workflow resumes without losing state or silently duplicating completed work.

## PHASE 2 — Model integration

- Implement common provider contracts.
- Add Meta.
- Add Baseten.
- Add mocked inference.
- Implement structured generation.
- Add provider fallback.
- Add budget enforcement.
- Add contract tests.

**Exit gate:** Mocked and configured providers follow the same interfaces, with usage recorded and failures handled.

## PHASE 3 — Complete minimum research loop

- Generate hypotheses.
- Define experiments.
- Run trusted bounded tests.
- Measure outputs.
- Save evidence.
- Select next actions.
- Produce reports.

**Exit gate:** One command performs a complete end-to-end research cycle and produces verifiable artifacts.

## PHASE 4 — Independent verification

- Implement independent evaluators.
- Add benchmark baselines.
- Add unseen tests.
- Add replication.
- Add false-success detection.
- Add uncertainty reporting.

**Exit gate:** Incorrect results and unsupported claims are rejected by tests.

## PHASE 5 — External research intelligence

- Implement retrieval.
- Track citations and provenance.
- Compare prior art.
- Detect contradictions.
- Support cross-domain research.
- Integrate research findings into hypothesis generation.

**Exit gate:** Research conclusions can be traced to actual sources.

## PHASE 6 — Branching and evolutionary discovery

- Implement hypothesis trees.
- Add controlled candidate mutation.
- Preserve parent-child history.
- Implement diversity-aware selection.
- Allocate bounded research effort.
- Stop repetitive and low-value branches.

**Exit gate:** The system can explore multiple candidate directions without duplicating work or entering uncontrolled loops.

## PHASE 7 — Commercial opportunity validation

- Add external market evidence collection.
- Implement buyer and user models.
- Add competition analysis.
- Implement commercial evidence gates.
- Separate commercial scores from technical scores.
- Prevent unsupported startup-success claims.

**Exit gate:** A technically successful but commercially unvalidated candidate is correctly classified.

## PHASE 8 — Extended autonomous operation

- Add durable worker scheduling.
- Support bounded concurrency.
- Implement fault recovery.
- Add circuit breakers.
- Add resource monitoring.
- Support pause, cancellation, and resume.
- Add long-running status reports.

**Exit gate:** Extended execution survives interruptions and respects configured limits.

## PHASE 9 — Interface and optional scaling

- Add research monitoring dashboard.
- Display active tasks and discoveries.
- Show hypothesis trees.
- Display evidence and evaluation status.
- Display spend and resource usage.
- Add human approval interfaces.
- Support optional remote workers and specialized experimentation.

**Exit gate:** Core research operations can be inspected and controlled without relying on raw logs.

---

# 9. EXECUTION ORDER AND AUTONOMY

Do not attempt all phases simultaneously.

At each step:

1. Identify the highest-priority unblocked task.
2. Inspect relevant existing implementation.
3. Confirm the requirement being implemented.
4. Determine acceptance criteria.
5. Implement the smallest coherent unit.
6. Write or update tests.
7. Run verification.
8. Fix failures.
9. Update documentation and task status.
10. Commit the verified change when appropriate.
11. Move to the next task.

Continue as long as execution resources, permissions, and meaningful unblocked work remain.

Do not repeatedly ask for permission for ordinary implementation details.

Choose reasonable defaults and document them.

Ask for authorization only when genuinely required, such as:

- Spending above authorized limits.
- Destructive external actions.
- Access to unavailable credentials.
- Production deployments.
- Permission expansion.
- Material project scope changes.

Do not bypass these approval requirements.

---

# 10. LOOP DETECTION AND ERROR RECOVERY

Autonomous agents frequently waste time repeating failed strategies.

Implement explicit loop detection in both the research platform and your development workflow.

Detect:

- Repeated identical errors.
- Repeated unchanged hypotheses.
- Repeated unsuccessful commands.
- Circular task dependencies.
- Candidate generation without measurable improvement.
- Repeated provider failures.
- Excessive token consumption without progress.
- Tasks that repeatedly alternate between states.

## Recovery protocol

On failure:

1. Capture the exact error.
2. Identify the likely root cause.
3. Determine whether a retry is safe.
4. Retry no more than the configured limit.
5. If unsuccessful, investigate an alternative approach.
6. Consult current documentation or live technical references where useful.
7. Run a smaller diagnostic to isolate the problem.
8. Preserve previous working functionality.
9. Record the failure and attempted recovery.
10. Continue another unblocked task when possible.

Never disguise a failure by disabling tests or weakening acceptance criteria.

Never repeatedly regenerate the same code without evidence that the next attempt is different.

Never modify security controls simply to make a failed test pass.

---

# 11. RESOURCE AND SPENDING SAFETY

Use these initial software limits unless deliberately reconfigured:

```text
MAX_COST_PER_RUN_USD=2
MAX_COST_PER_DAY_USD=10
MAX_EXPERIMENT_SECONDS=120
MAX_RETRIES_PER_STEP=2
MAX_HYPOTHESES_PER_CYCLE=5
MAX_CONCURRENT_EXPERIMENTS=1
```

These are starting limits, not guaranteed provider-enforced spending caps.

Implement:

- Request-level token accounting.
- Cost reservations.
- Cumulative usage tracking.
- Budget rejection before expensive calls.
- Configurable daily limits.
- Experiment timeouts.
- Provider circuit breakers.
- Graceful shutdown.
- Explicit failure reporting.

Development tests should default to mocked inference.

Only run billable integration tests when credentials and permitted budgets are available.

Do not use the entire research budget during infrastructure testing.

---

# 12. TESTING AND VERIFICATION

Testing is mandatory, not an optional final step.

Create:

```text
tests/unit/
tests/integration/
tests/adversarial/
tests/end_to_end/
```

## Required test categories

### Unit

- Schema validation.
- State transitions.
- Cost calculation.
- Provider interfaces.
- Duplicate detection.
- Hash chaining.
- Budget enforcement.
- Permission checks.

### Integration

- Provider routing.
- Database persistence.
- Artifact storage.
- Runner-to-evaluator communication.
- Checkpoint recovery.
- Provider failure handling.

### Adversarial

- Prompt injection in retrieved content.
- Incorrect model-generated success claims.
- Attempts to exceed execution limits.
- Unauthorized file access.
- Secret exposure attempts.
- Infinite-loop scenarios.
- Invalid evidence.
- Benchmark manipulation.

### End-to-end

1. Complete deterministic research experiment.
2. Interrupted workflow recovery.
3. Failed hypothesis followed by justified revision.
4. Commercial opportunity without sufficient demand evidence.
5. Budget exhaustion and graceful stopping.

Do not treat a mocked test as proof that a live external integration works.

Record exactly what was tested.

## GitHub Actions limitation

GitHub Actions have been unreliable in the user's existing development workflows.

Do not use the status of GitHub Actions as the only indicator of merge readiness.

Run local verification independently.

Inspect:

- Test output.
- Type checking.
- Linting.
- Build or packaging.
- End-to-end smoke tests.
- Security findings.
- Actual runtime artifacts.

Distinguish:

```text
IMPLEMENTED
LOCALLY_VERIFIED
INTEGRATION_VERIFIED
PRODUCTION_READY
```

These states are not interchangeable.

Do not merge changes automatically.

---

# 13. LIVE WEB RESEARCH POLICY

You may use live web research throughout implementation.

Use it to verify:

- Current Meta Model API documentation.
- Baseten endpoints and compatibility.
- Authentication requirements.
- Model capabilities.
- Pricing and rate limits.
- Sandbox security recommendations.
- Python dependencies.
- Research orchestration approaches.
- Scientific evaluation methods.
- Deployment requirements.
- Relevant implementation examples.

Prefer official documentation and primary technical sources.

When external information changes an engineering decision, document the source and rationale.

Do not blindly implement a technology recommendation from an older research report.

Do not turn implementation work into endless research. Time-box investigations, choose justified approaches, and return to implementation.

---

# 14. DEVELOPMENT LOGGING FORMAT

Maintain a machine-readable development event log.

Example:

```json
{
  "task_id": "PHASE-02-TASK-004",
  "event": "verification_completed",
  "phase": 2,
  "status": "VERIFIED",
  "files_changed": [
    "src/autodiscover/models/router.py"
  ],
  "tests_passed": 12,
  "tests_failed": 0,
  "commit": "actual-commit-sha",
  "blockers": [],
  "next_task": "PHASE-02-TASK-005"
}
```

Use actual values from execution.

Do not fabricate results, timestamps, commits, costs, or test counts.

Support event identifiers, timestamps, and correlation identifiers.

Logs should be append-only and protected from concurrent write corruption.

---

# 15. CONTINUOUS REQUIREMENTS AUDIT

At the end of each phase, conduct an audit.

For every requirement assigned to that phase:

- Confirm the corresponding implementation exists.
- Locate the actual source files.
- Confirm tests exist.
- Run the tests.
- Inspect the results.
- Identify missing behavior.
- Record accepted limitations.
- Update the task ledger.
- Update requirements traceability.
- Update the handoff.

If a feature is partially complete, do not advance its status to VERIFIED.

If the current implementation contradicts a permanent requirement, report and resolve the conflict.

Do not allow a later phase to silently remove behavior validated in an earlier phase.

---

# 16. PRIORITY AND TIME MANAGEMENT

The immediate milestone is a minimum working research loop.

Prioritize:

1. Persistent documentation and context recovery.
2. Durable state machine.
3. Model provider adapters.
4. Safe experiment execution.
5. Independent evaluation.
6. Evidence recording.
7. One reproducible demonstration.

Complete these before implementing advanced evolutionary search, an elaborate dashboard, physical hardware, or distributed infrastructure.

The November 4, 2026 hackathon deadline may be relevant, but do not sacrifice verification, authorization, or core architecture to claim completion by a date.

Confirm hackathon eligibility and requirements before treating the project as a valid submission.

Long-term implementation should continue according to phase acceptance criteria rather than an artificial deadline.

---

# 17. REQUIRED REPORTING AFTER EACH PHASE

Produce a concise implementation report:

```text
PHASE:
STATUS:

IMPLEMENTED:
- ...

VERIFIED:
- ...

TEST RESULTS:
- ...

FILES MODIFIED:
- ...

DESIGN DECISIONS:
- ...

BLOCKERS:
- ...

REMAINING REQUIREMENTS:
- ...

LAST VERIFIED COMMIT:
- ...

NEXT TASK:
- ...
```

Store the authoritative report in the repository.

Avoid excessive narrative progress reports.

The objective is evidence of implementation, not a polished description of intended features.

---

# 18. COMPLETION CONDITIONS

Do not declare the full project complete until all required phases and non-deferred acceptance criteria have been verified.

The platform must demonstrate:

- Autonomous hypothesis generation.
- Real research-source retrieval.
- Falsifiable experimental design.
- Isolated execution.
- Independent evaluation.
- Repeatable results.
- Persistent evidence.
- Recovery from interruption.
- Bounded evolutionary exploration.
- Explicit technical and novelty assessments.
- Commercial validation gates.
- Budget enforcement.
- Continuous context preservation.
- Human intervention controls.
- Verified end-to-end execution.

If some phases remain incomplete, report the actual state and continue with unblocked work.

Do not describe a prototype as a finished autonomous scientific research system.

---

# 19. INITIAL EXECUTION INSTRUCTIONS

Begin now.

**Step 1:** Inspect the current workspace, repository, Git state, existing documentation, dependencies, and tests.

**Step 2:** Determine whether this is a new project or an existing implementation. Preserve valid existing work.

**Step 3:** Create the persistent context and requirement-tracking system before substantial implementation.

**Step 4:** Convert this master prompt into a traceable phase-by-phase task ledger. Preserve every important requirement.

**Step 5:** Write the initial architecture and security decisions.

**Step 6:** Implement Phase 0 and locally verify its acceptance criteria.

**Step 7:** Continue directly into Phase 1, then the remaining phases in dependency order.

**Step 8:** At each task boundary, update persistent records and commit verified changes where appropriate.

**Step 9:** When context becomes limited, write a complete handoff and save all current progress before further large changes.

**Step 10:** On resumed execution, reconstruct state from the repository and continue the last uncompleted verified task.

Do not stop merely because the documentation, initial scaffolding, or one research demonstration has been completed.

Do not spend the entire session only planning.

Do not restart previously verified work.

Do not drift away from the original research mission.

**Your first action must be inspecting the repository and creating or validating the persistent project context system. Then proceed with implementation.**

## FINAL DIRECTIVE

Build the Autonomous Discovery Lab as a real, verifiable research system.

Prioritize correctness, scientific validity, reproducibility, controlled autonomy, and persistent state over feature count.

Preserve decisions and progress across every session.

Every major capability must have traceable requirements, working code, and verification evidence.

Every important discovery must be supported by evidence.

Every commercial recommendation must be distinguished from an unvalidated hypothesis.

**The project must be recoverable by a completely new coding agent using only the repository's persisted context, code, logs, and documentation, without needing this original conversation.**
