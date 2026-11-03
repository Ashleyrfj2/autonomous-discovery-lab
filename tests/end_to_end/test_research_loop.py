import json
import subprocess
import sys

from autodiscover.evidence.chain import verify_chain
from autodiscover.orchestrator.contracts import Stage
from autodiscover.orchestrator.lab import Lab


def test_complete_offline_loop_with_replicated_evidence(tmp_path):
    lab = Lab(tmp_path)
    run = lab.demo()
    report = lab.report(run)
    assert report["status"] == "COMPLETED"
    assert report["completed_steps"] == 12
    assert report["assessment"]["technical_success"] is True
    assert report["assessment"]["novelty"] == "unknown"
    assert report["commercial"]["level"] == 0
    assert report["commercial"]["validated"] is False
    assert report["usage"]["charged_usd"] == "0"
    plan = lab.plan(run)
    result = lab.artifacts.get_json(lab.latest(run, Stage.VERIFY)["report_digest"])
    assert result["heldout_cases"] == 48
    assert result["heldout_min_savings"] >= plan.minimum_savings
    replications = lab.latest(run, Stage.REPLICATE)["report_digests"]
    assert len(replications) == 2
    for index, digest in enumerate(replications, start=1):
        replication = lab.artifacts.get_json(digest)
        raw = lab.artifacts.get_json(replication["raw_artifact_digest"])
        assert replication["passed"] is True
        assert raw["replication"] == index
    assert verify_chain(lab.store)["verified_events"] >= 12


def test_resume_partial_loop_does_not_duplicate_completed_stages(tmp_path):
    first = Lab(tmp_path)
    run = first.demo(stop_after=7)
    original_steps = first.store.outputs(run)
    original_execution = first.latest(run, Stage.EXECUTE)
    assert first.store.get_run(run)["stage"] == Stage.VERIFY
    recovered = Lab(tmp_path)
    recovered.resume(run)
    assert recovered.store.outputs(run)[:7] == original_steps
    assert recovered.latest(run, Stage.EXECUTE) == original_execution
    assert recovered.report(run)["completed_steps"] == 12
    recovered.resume(run)
    assert recovered.report(run)["completed_steps"] == 12


def test_cli_one_command_outputs_report_and_inspection(tmp_path):
    result = subprocess.run(  # noqa: S603 - fixed trusted test commands, no shell
        [sys.executable, "-m", "autodiscover.cli", "--root", str(tmp_path), "demo"],
        capture_output=True,
        text=True,
        check=True,
    )  # noqa: S603
    report = json.loads(result.stdout)
    assert report["status"] == "COMPLETED"
    status = subprocess.run(  # noqa: S603 - fixed trusted test commands, no shell
        [
            sys.executable,
            "-m",
            "autodiscover.cli",
            "--root",
            str(tmp_path),
            "status",
            report["run_id"],
        ],
        capture_output=True,
        text=True,
        check=True,
    )  # noqa: S603
    assert json.loads(status.stdout)["assessment"] == report["assessment"]
