"""Persist a development boundary; only metadata is accepted, never secret/source bodies."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

from autodiscover.orchestrator.durability import append_event, atomic_json, now

parser = argparse.ArgumentParser()
parser.add_argument("task")
parser.add_argument("--phase", type=int, required=True)
parser.add_argument("--status", required=True)
parser.add_argument("--next", required=True)
parser.add_argument("--evidence", type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]


# Constant allowlisted commands; no shell or user command interpolation.
def git(*arguments: str) -> str:
    executable = shutil.which("git")
    if executable is None:
        raise RuntimeError("git unavailable")
    result = subprocess.run(  # noqa: S603 - executable resolved, constant internal arguments
        [executable, *arguments], cwd=root, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "NO_COMMIT"


record = {
    "timestamp": now(),
    "task_id": args.task,
    "phase": args.phase,
    "status": args.status,
    "evidence": str(args.evidence),
    "next_exact_action": args.next,
    "commit": git("rev-parse", "HEAD"),
    "git_state": git("status", "--short", "--branch"),
    "resource_status": "No billable provider calls authorized or executed",
    "recovery_commands": ["cat AGENTS.md", "uv sync --locked", "uv run pytest -q"],
    "assumptions": ["trusted local workers only", "mock inference by default"],
}
run_id = str(uuid4())
append_event(
    root / "runtime/logs/development.jsonl",
    run_id=run_id,
    task_id=args.task,
    event="checkpoint",
    details=record,
)
atomic_json(root / "runtime/checkpoints/development.json", record)
print(json.dumps({"task_id": args.task, "checkpoint": "runtime/checkpoints/development.json"}))
