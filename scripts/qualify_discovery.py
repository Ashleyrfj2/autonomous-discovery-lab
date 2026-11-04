"""Export the reproducible offline discovery qualification and a one-model control."""

import argparse
import json
import runpy
from pathlib import Path

from autodiscover.evidence.chain import export_snapshot, verify_chain
from autodiscover.orchestrator.store import SnapshotStore
from autodiscover.research.discovery import replay

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    args.destination.mkdir(parents=True)
    controls = runpy.run_path(str(ROOT / "tests/integration/test_discovery.py"))
    summary = {"mode": "offline_scripted_control", "studies": {}}
    reviewed_content = None
    studies = (
        ("reviewed", "reviewed", True),
        ("single_model", "single_model", True),
        ("two_candidates", "reviewed", False),
    )
    for label, mode, flawed in studies:
        root = args.destination / label
        discovery, spec, calls, archive = controls["setup"](
            root,
            mode=mode,
            flawed_candidate=flawed,
        )
        run_id = discovery.register(spec)
        digest, report = discovery.execute(run_id)
        before = len(calls), len(archive.calls)
        with SnapshotStore(root) as store:
            if replay(store, run_id) != (digest, report):
                raise RuntimeError("Offline replay diverged from committed report")
            anchor = verify_chain(store)
            export_snapshot(store, args.destination / f"{label}-evidence.json")
        if before != (len(calls), len(archive.calls)):
            raise RuntimeError("Offline replay initiated external work")
        content = report.model_dump(include={"plan", "searches", "candidates", "decisions"})
        if label == "reviewed":
            reviewed_content = content
        elif label == "single_model":
            if reviewed_content != content:
                raise RuntimeError("Scripted baseline used different research content")
            summary["matched_control_content"] = True
        result = controls["evaluate_control"](report)
        if not flawed:
            result.pop("flawed_candidate_rejected")
            result.pop("invalid_quotes_advanced")
        result["candidates_reviewed"] = sum(
            c.original_review is not None for c in report.candidates
        )
        result.update(
            run_id=run_id,
            report_digest=digest,
            event_anchor=anchor,
            cache_replay_dispatches=0,
            cache_replay_fetches=0,
            fixture_fetches=before[1],
        )
        summary["studies"][label] = result
        (args.destination / f"{label}-report.json").write_text(report.model_dump_json(indent=2))
    (args.destination / "metrics.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
