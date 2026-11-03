# Autonomous Discovery Lab recovery entry point

Read, in order: `docs/PROJECT_CHARTER.md`, `docs/REQUIREMENTS_TRACEABILITY.md`,
`docs/ARCHITECTURE.md`, `docs/TASK_LEDGER.md`, `docs/DECISION_LOG.md`, and
`docs/HANDOFF.md`. The full user brief is preserved in `docs/MASTER_REQUIREMENTS.md`.
Inspect `git status --short --branch` and `git log -5 --oneline`. Inspect the relevant
source and recorded verification evidence before trusting any completion label.
Run the relevant validations, reconcile code and documentation, then resume the
highest-priority unblocked task. Do not restart verified work or replace an earlier
architecture decision without recording why. Never infer implementation from a summary.

Every meaningful task/decision/failure/refactor/session boundary requires an atomic
machine checkpoint and sanitized append-only JSONL event. Update the ledger,
traceability, handoff, history and phase report. Preserve explicit unfinished gaps.
Never store secrets in code, logs, artifacts, reports or commits. No live billable
calls without configured authorization and spending limits; no deployments or merges
without explicit user authorization. Mock tests do not establish live acceptance.
Use only trusted allowlisted experiment workers; generated code is never executable.
Keep technical success, discovery novelty, and external commercial evidence separate.
Validate locally with `uv run ruff check .`, `uv run pyright`, `uv run pytest -q`,
`uv build` and the relevant CLI smoke tests. GitHub Actions is not the acceptance gate.
Do not modify adjacent research, Olavrin, Expert Execution Engine or Meta repositories.
Retain the cross-industry mission. Add no feature without a requirement and acceptance
criterion. VERIFIED requires passing recorded tests, not just an implementation.
