"""CLI for bounded research runs, recovery, reports, controls and integrity inspection."""

import argparse
import json
from pathlib import Path

from autodiscover import __version__
from autodiscover.config import Limits
from autodiscover.evidence.chain import export_snapshot, verify_chain
from autodiscover.hypotheses.engine import Hypothesis, demo_proposal
from autodiscover.hypotheses.proposals import ResearchProposal
from autodiscover.orchestrator.lab import Lab


def main() -> None:
    parser = argparse.ArgumentParser(prog="autodiscover")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--root", type=Path, default=Path("runtime"))
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="Validate local policy; no provider calls")
    check.add_argument("--config", type=Path, default=Path("config/default.json"))
    demo = sub.add_parser("demo", help="Execute complete offline trusted encoding research cycle")
    demo.add_argument("--topic", default="consumer, gaming and telemetry data")
    demo.add_argument("--config", type=Path, default=Path("config/default.json"))
    demo.add_argument("--stop-after", type=int)
    demo.add_argument("--algorithm", choices=["rle", "identity"], default="rle")
    explore = sub.add_parser(
        "explore", help="Bounded offline exploration of multiple reviewed candidate directions"
    )
    explore.add_argument(
        "--topic", default="lossless storage across repeated and alternating datasets"
    )
    research = sub.add_parser(
        "research", help="Retrieve public prior-art metadata, then stop for inspection"
    )
    research.add_argument("query")
    research.add_argument("--allow-network", action="store_true")
    resume = sub.add_parser("resume", help="Continue an active run from committed state")
    resume.add_argument("run_id")
    resume.add_argument("--stop-after", type=int)
    tree = sub.add_parser(
        "tree", help="Inspect durable hypotheses, lineage, allocations and stopping"
    )
    tree.add_argument("run_id")
    add = sub.add_parser(
        "candidate-add", help="Import a typed candidate; unsupported families remain theoretical"
    )
    add.add_argument("run_id")
    add.add_argument("candidate", type=Path)
    status = sub.add_parser("status", help="Inspect persisted state and verified reports")
    status.add_argument("run_id", nargs="?")
    for command in ("pause", "unpause", "cancel"):
        sub.add_parser(command).add_argument("run_id")
    integrity = sub.add_parser("integrity", help="Verify chain against optional retained anchor")
    integrity.add_argument("--anchor", type=Path)
    snapshot = sub.add_parser(
        "snapshot", help="Export no-overwrite evidence snapshot for separate retention"
    )
    snapshot.add_argument("destination", type=Path)
    args = parser.parse_args()
    if args.command == "check":
        result = {"valid": True, "limits": Limits.load(args.config).model_dump(mode="json")}
    else:
        lab = Lab(args.root)
        if args.command == "demo":
            run = lab.demo(
                args.topic,
                limits=Limits.load(args.config),
                stop_after=args.stop_after,
                algorithm=args.algorithm,
            )
            result = lab.report(run)
        elif args.command == "explore":
            candidates = [
                Hypothesis.model_validate(
                    {**demo_proposal("consumer telemetry"), "algorithm": "identity"}
                ),
                Hypothesis.model_validate(
                    {**demo_proposal("gaming event streams"), "data_profile": "alternating"}
                ),
            ]
            run = lab.explore(args.topic, candidates)
            result = lab.report(run)
        elif args.command == "research":
            if not args.allow_network:
                parser.error("research requires --allow-network")
            run = lab.demo(args.query, limits=Limits(allow_retrieval=True), stop_after=2)
            result = lab.report(run)
        elif args.command == "resume":
            lab.resume(args.run_id, stop_after=args.stop_after)
            result = lab.report(args.run_id)
        elif args.command in ("pause", "unpause", "cancel"):
            lab.store.control(args.run_id, "resume" if args.command == "unpause" else args.command)
            result = lab.report(args.run_id)
        elif args.command == "tree":
            result = lab.director.tree(args.run_id)
        elif args.command == "candidate-add":
            if args.candidate.stat().st_size > 65536:
                parser.error("Candidate JSON exceeds 64 KiB")
            data = json.loads(args.candidate.read_text())
            schema = (
                ResearchProposal if data.get("experiment_family") == "theoretical" else Hypothesis
            )
            identifier = lab.director.register(args.run_id, schema.model_validate(data))
            result = {"hypothesis_id": identifier, "search": lab.director.tree(args.run_id)}
        elif args.command == "status":
            result = (
                lab.report(args.run_id)
                if args.run_id
                else [
                    {
                        "run_id": r["id"],
                        "topic": r["topic"],
                        "stage": r["stage"],
                        "status": r["status"],
                        "version": r["version"],
                    }
                    for r in lab.store.list_runs()
                ]
            )
        elif args.command == "integrity":
            anchor = json.loads(args.anchor.read_text()) if args.anchor else None
            result = verify_chain(lab.store, anchor.get("anchor", anchor) if anchor else None)
        else:
            result = export_snapshot(lab.store, args.destination)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
