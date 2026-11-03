import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from pydantic import ValidationError

from autodiscover.config import Limits
from autodiscover.orchestrator.durability import append_event, atomic_json
from autodiscover.security.redaction import sanitize


def test_defaults_and_invalid_limits():
    limits = Limits()
    assert str(limits.max_cost_per_run_usd) == "2"
    assert limits.max_concurrent_experiments == 1
    assert not limits.allow_live_inference
    for invalid in (
        {"max_experiment_seconds": 0},
        {"max_cost_per_run_usd": "NaN"},
        {"max_concurrent_experiments": -1},
        {"unknown": 1},
    ):
        with pytest.raises(ValidationError):
            Limits.model_validate(invalid)


def test_atomic_checkpoint(tmp_path):
    path = tmp_path / "state.json"
    atomic_json(path, {"phase": 0, "password": "never-persist"})
    atomic_json(path, {"phase": 1})
    assert json.loads(path.read_text()) == {"phase": 1}
    assert list(tmp_path.iterdir()) == [path]


def test_locked_events_and_redaction(tmp_path):
    path = tmp_path / "events.jsonl"
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(
            pool.map(
                lambda i: append_event(
                    path,
                    run_id="run",
                    task_id=str(i),
                    event="test",
                    details={"api_key": "secret-value", "error": "Bearer dont-save-me"},
                ),
                range(40),
            )
        )
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows) == len({r["event_id"] for r in rows}) == 40
    assert "dont-save-me" not in path.read_text()
    assert "secret-value" not in path.read_text()
    assert sanitize({"contact": "person@example.com"}) == {"contact": "[REDACTED]"}


def test_permanent_context_exists():
    root = Path(__file__).resolve().parents[2]
    required = [
        "PROJECT_CHARTER",
        "ARCHITECTURE",
        "IMPLEMENTATION_PLAN",
        "REQUIREMENTS_TRACEABILITY",
        "TASK_LEDGER",
        "DECISION_LOG",
        "HANDOFF",
        "SECURITY_MODEL",
        "EVALUATION_PROTOCOL",
        "RESEARCH_PROTOCOL",
        "OPERATIONS",
        "KNOWN_ISSUES",
        "DEVELOPMENT_HISTORY",
        "RELEASE_READINESS",
        "MASTER_REQUIREMENTS",
    ]
    assert (root / "AGENTS.md").is_file()
    for name in required:
        assert (root / "docs" / f"{name}.md").stat().st_size > 100
    trace = (root / "docs/REQUIREMENTS_TRACEABILITY.md").read_text()
    for index in range(1, 43):
        assert f"REQ-{index:03}" in trace
    assert Limits.load(root / "config/default.json") == Limits()
