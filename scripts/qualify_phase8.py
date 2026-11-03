"""Reproducible, offline Phase 8 acceptance; refuses to overwrite earlier evidence.

Run with --root runtime/phase8-final and --output docs/phase_reports/phase-8-acceptance.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from autodiscover.config import Limits
from autodiscover.evidence.artifacts import Artifacts
from autodiscover.evidence.chain import export_snapshot, verify_chain, verify_events
from autodiscover.experiments.contracts import Plan
from autodiscover.experiments.evaluator import evaluate
from autodiscover.orchestrator.durability import atomic_json, canonical, now
from autodiscover.orchestrator.lab import Lab
from autodiscover.orchestrator.scheduler import Scheduler

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def revision() -> dict[str, Any]:
    """Bind acceptance to source, tests, dependency lock, configuration and qualification script."""
    paths = [
        p
        for folder in ("src", "tests", "config", "scripts")
        for p in (ROOT / folder).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    ]
    paths += [ROOT / name for name in ("pyproject.toml", "uv.lock", ".python-version")]
    manifest = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(paths)
        if p.exists()
    }
    git = shutil.which("git")
    require(git is not None, "git required")
    base = subprocess.run(  # noqa: S603 - resolved executable and fixed Git arguments
        [str(git), "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()  # noqa: S603 - fixed Git command
    return {
        "base_commit": base,
        "files": manifest,
        "sha256": hashlib.sha256(canonical(manifest).encode()).hexdigest(),
        "scope": "Source/tests/config/scripts/dependencies; docs recorded by milestone commit",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    runtime, output = args.root.resolve(), args.output.resolve()
    require(
        not runtime.exists() and not output.exists(), "Use new runtime and evidence directories"
    )
    output.mkdir(parents=True)
    runtime.mkdir(parents=True)
    uv = shutil.which("uv")
    require(uv is not None, "uv required")
    started_at, started = now(), time.monotonic()
    source = revision()
    validations = []
    targeted_xml = output / "targeted-tests.xml"
    commands = [
        ["run", "ruff", "check", "."],
        ["run", "pyright"],
        ["run", "pytest", "-q"],
        ["build"],
        [
            "run",
            "pytest",
            "-q",
            "tests/integration/test_durable_jobs.py",
            "tests/end_to_end/test_scheduled_operation.py",
            "tests/integration/test_providers.py",
            "tests/integration/test_experiment_runner.py",
            "tests/integration/test_recovery.py",
            "tests/unit/test_state.py",
            "tests/unit/test_budget.py",
            "tests/adversarial/test_evaluation_manipulation.py",
            f"--junitxml={targeted_xml}",
        ],
    ]
    for command in commands:
        check_started_at, check_started = now(), time.monotonic()
        result = subprocess.run(  # noqa: S603 - resolved executable and allowlisted checks
            [str(uv), *command], cwd=ROOT, text=True, capture_output=True, check=False
        )  # noqa: S603 - allowlisted local checks
        record = {
            "command": ["uv", *command],
            "started_at": check_started_at,
            "ended_at": now(),
            "elapsed_seconds": time.monotonic() - check_started,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        validations.append(record)
        atomic_json(output / "validation.json", validations)
        require(result.returncode == 0, f"Acceptance check failed: {command}")
        print(json.dumps({"check": command[:3], "exit_code": result.returncode}), flush=True)
    cases = [
        {
            "name": case.attrib["name"],
            "class": case.attrib.get("classname"),
            "outcome": "passed" if not list(case) else "inspect",
        }
        for case in ET.parse(targeted_xml).getroot().iter("testcase")  # noqa: S314 - generated local pytest output
    ]
    require(all(case["outcome"] == "passed" for case in cases), "Targeted case did not pass")
    run_started_at, run_started = now(), time.monotonic()
    lab = Lab(runtime)
    queue = Scheduler(lab.store)
    policy = Limits()
    require(
        not policy.allow_live_inference and not policy.allow_retrieval, "Offline policy required"
    )
    runs = [
        lab.store.create_run(
            f"Phase 8 offline acceptance cycle {index}", policy.model_dump(mode="json")
        )
        for index in range(1, 9)
    ]
    for run in runs:
        queue.enqueue(run)
    first = queue.run(max_steps=16, max_seconds=60, concurrency=2)
    before_restart = {run: lab.store.get_run(run)["version"] for run in runs}
    require(all(version > 0 for version in before_restart.values()), "Queue starvation observed")
    recovered = Lab(runtime)
    second = Scheduler(recovered.store).run(max_steps=300, max_seconds=60, concurrency=2)
    reports = [recovered.report(run) for run in runs]
    jobs = recovered.jobs.status()
    require(
        all(r["status"] == "COMPLETED" and r["completed_steps"] == 12 for r in reports),
        "Not all workflows completed",
    )
    require(
        len(jobs) == 24 and all(j["status"] == "COMPLETED" and j["attempts"] == 1 for j in jobs),
        "Unexpected duplicate or incomplete computation",
    )
    require(
        all(r["usage"]["charged_usd"] == "0" for r in reports), "Unexpected provider accounting"
    )
    require(
        all(
            r["assessment"]["technical_success"]
            and r["assessment"]["novelty"] == "unknown"
            and r["commercial"]["level"] == 0
            and not r["commercial"]["validated"]
            for r in reports
        ),
        "Unsupported classification",
    )
    for job in jobs:
        plan = Plan.model_validate(recovered.artifacts.get_json(job["plan_digest"]))
        raw = recovered.artifacts.get_json(job["artifact_digest"])
        require(
            evaluate(plan, raw, replication=job["replication"])["passed"],
            "Independent re-evaluation failed",
        )
    active: set[str] = set()
    peak = 0
    with recovered.store.connection() as db:
        events = [dict(r) for r in db.execute("SELECT * FROM events ORDER BY seq")]
    for event in events:
        data = json.loads(event["payload_json"])
        if event["kind"] == "job_claimed":
            active.add(data["job_id"])
            peak = max(peak, len(active))
            require(len(active) <= data["concurrency_ceiling"], "Admission limit violated")
        elif event["kind"] in ("job_completed", "job_failed", "job_interrupted", "job_reconciled"):
            active.discard(data["job_id"])
    require(not active and peak == 1, "Default experiment concurrency violated")
    snapshot = output / "evidence-snapshot.json"
    anchor = export_snapshot(recovered.store, snapshot)
    integrity = verify_chain(recovered.store, anchor)
    retained = json.loads(snapshot.read_text())
    verify_events(retained["events"], anchor)
    archive = Artifacts(output / "artifacts")
    artifacts = []
    for path in sorted((runtime / "artifacts").glob("*/*")):
        require(
            archive.put(recovered.artifacts.get(path.name)) == path.name, "Archive hash mismatch"
        )
        artifacts.append(path.name)
    operation = {
        "qualification": (
            "Short bounded local mock-provider run; "
            "not a long-duration soak or live-provider qualification"
        ),
        "started_at": run_started_at,
        "ended_at": now(),
        "elapsed_seconds": time.monotonic() - run_started,
        "provider_mode": "deterministic mock; retrieval disabled; no credentials read",
        "runs": 8,
        "completed_stages": sum(r["completed_steps"] for r in reports),
        "completed_jobs": len(jobs),
        "peak_recorded_concurrent_experiments": peak,
        "stage_worker_concurrency": 2,
        "provider_spend_usd": "0",
        "versions_before_coordinator_restart": before_restart,
        "stage_attempts": [first["stage_attempts"], second["stage_attempts"]],
        "run_ids": runs,
        "queue": second["queue"],
        "jobs": jobs,
        "peak_rss_bytes": max(
            recovered.artifacts.get_json(j["artifact_digest"])["peak_rss_bytes"] for j in jobs
        ),
        "independently_recomputed_job_results": len(jobs),
        "evidence": integrity,
        "accepted_classification": {
            "technical_success": True,
            "novelty": "unknown",
            "market_level": 0,
        },
    }
    require(revision() == source, "Source changed during qualification; rerun on stable final code")
    atomic_json(output / "source-manifest.json", source)
    atomic_json(output / "bounded-operation.json", operation)
    atomic_json(
        output / "acceptance.json",
        {
            "schema_version": 1,
            "status": "LOCALLY_VERIFIED",
            "started_at": started_at,
            "ended_at": now(),
            "elapsed_seconds": time.monotonic() - started,
            "command": [
                "uv",
                "run",
                "python",
                "scripts/qualify_phase8.py",
                "--root",
                str(runtime),
                "--output",
                str(output),
            ],
            "source_revision_sha256": source["sha256"],
            "base_commit": source["base_commit"],
            "validations": "validation.json",
            "operation": "bounded-operation.json",
            "targeted_cases": cases,
            "snapshot_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            "artifact_sha256s": artifacts,
            "limitations": [
                "macOS trusted encoding workers only; deprecated/private Seatbelt",
                "RSS polling may overshoot; forced RSS test uses a simulated observation",
                (
                    "Unknown remote outcome retains reservation; "
                    "caller cancellation is not provider cancellation"
                ),
                "Transport threads bounded to eight per process; late responses discarded",
                "Local coordinator identity; legacy/remote owners require lease expiry",
                "SQLite/anchors are tamper evident relative to retained copy, not immutable",
                "No distributed/production/live-inference/novelty/commercial qualification",
            ],
        },
    )
    print(
        json.dumps(
            {
                "status": "LOCALLY_VERIFIED",
                "source_sha256": source["sha256"],
                "workflows": 8,
                "stages": 96,
                "jobs": 24,
                "peak_experiments": peak,
                "artifacts": len(artifacts),
                "evidence": str(output),
            }
        )
    )


if __name__ == "__main__":
    main()
