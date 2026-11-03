# Operations

Run from the nested `autonomous-discovery-lab` repository. Install Python 3.12 and `uv sync --locked`. Development defaults to mocked inference, no secrets required. Local checks: `uv run ruff check .`, `uv run pyright`, `uv run pytest -q`, `uv build`. CLI and runtime operations will be documented as implemented. Do not assume commands from the plan already exist.

Default limits: per run USD 2; daily USD 10; experiment 120 seconds; retries 2; hypotheses 5; concurrency 1. These are software limits, not provider hard caps. Raising authority or spending requires explicit configuration and user authorization. Avoid provider calls during infrastructure tests.

Recovery: read AGENTS and its ordered documents, inspect Git, examine checkpoints/logs/artifacts, run relevant checks, reconcile discrepancies, resume the exact next task from HANDOFF. Checkpoint before refactors/session ends and after tasks/failures/decisions. Export anchors independently for stronger tamper detection. Logs and runtime databases are ignored by Git. Preserve selected sanitized test evidence under docs/phase_reports.
