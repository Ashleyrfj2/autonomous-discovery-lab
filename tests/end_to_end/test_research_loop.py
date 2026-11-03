import json
import subprocess
import sys

from autodiscover.evidence.chain import verify_chain
from autodiscover.experiments.contracts import Plan
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
    assert isinstance(plan, Plan)
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


def test_failed_hypothesis_then_justified_revision_completes(tmp_path):
    lab = Lab(tmp_path)
    run = lab.demo(algorithm="identity")
    report = lab.report(run)
    assert report["status"] == "COMPLETED"
    assert report["assessment"]["technical_success"] is True
    nodes = report["search"]["nodes"]
    assert len(nodes) == 2
    assert nodes[0]["status"] == "FAILED"
    assert nodes[1]["status"] == "PROMISING"
    assert nodes[1]["parent_id"] == nodes[0]["id"]
    parent_report = lab.artifacts.get_json(nodes[1]["revision_evidence"])
    assert parent_report["passed"] is False
    assert len(report["search"]["allocations"]) == 2
    assert report["commercial"]["validated"] is False


def test_repeated_demo_topics_are_scoped_to_their_own_runs(tmp_path):
    lab = Lab(tmp_path)
    first = lab.demo()
    second = lab.demo()
    assert first != second
    assert len(lab.report(first)["search"]["nodes"]) == 1
    assert len(lab.report(second)["search"]["nodes"]) == 1


def test_bounded_exploration_runs_multiple_directions_and_preserves_negative_results(tmp_path):
    from autodiscover.hypotheses.engine import Hypothesis, demo_proposal

    lab = Lab(tmp_path)
    candidates = [
        Hypothesis.model_validate({**demo_proposal("consumer"), "algorithm": "identity"}),
        Hypothesis.model_validate({**demo_proposal("gaming"), "data_profile": "alternating"}),
    ]
    run = lab.explore("multiple experiment directions", candidates)
    report = lab.report(run)
    assert report["status"] == "COMPLETED"
    assert len(report["search"]["nodes"]) == 3
    assert sorted(n["status"] for n in report["search"]["nodes"]) == [
        "FAILED",
        "FAILED",
        "PROMISING",
    ]
    assert len(report["search"]["allocations"]) == 3
    assert not lab.director.has_work(run)
    assert report["assessment"]["hypothesis_id"] in {n["id"] for n in report["search"]["nodes"]}
    assert report["assessment"]["technical_success"] is True
    assert report["assessment"]["novelty"] == "unknown"


def test_negative_last_branch_concludes_search_without_claiming_it_succeeded(tmp_path):
    from autodiscover.config import Limits
    from autodiscover.hypotheses.engine import Hypothesis, demo_proposal

    lab = Lab(tmp_path)
    run = lab.store.create_run(
        "negative branch last", Limits(explore_existing_candidates=True).model_dump(mode="json")
    )
    lab.director.register(
        run, Hypothesis.model_validate({**demo_proposal("consumer"), "algorithm": "identity"})
    )
    lab.resume(run, stop_after=17)
    assert lab.store.get_run(run)["stage"] == "DECIDE"
    lab.director.register(
        run, Hypothesis.model_validate({**demo_proposal("gaming"), "data_profile": "alternating"})
    )
    lab.resume(run)
    report = lab.report(run)
    assert report["status"] == "COMPLETED"
    verifications = [
        json.loads(s["output_json"]) for s in lab.store.outputs(run) if s["stage"] == "VERIFY"
    ]
    assert verifications[-1]["passed"] is False
    assert lab.plan(run).data_profile == "alternating"
    failed = next(
        n for n in report["search"]["nodes"] if n["identity"] == lab.plan(run).hypothesis_id
    )
    assert failed["status"] == "FAILED"
    assert report["assessment"]["hypothesis_id"] != failed["id"]
    assert len([n for n in report["search"]["nodes"] if n["status"] == "FAILED"]) == 2
    assert not lab.director.has_work(run)
    assert len(report["search"]["allocations"]) == 3
