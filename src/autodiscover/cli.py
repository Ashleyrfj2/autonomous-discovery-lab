"""CLI for bounded research runs, recovery, reports, controls and integrity inspection."""

import argparse
import json
import signal
import sys
import threading
from pathlib import Path
from urllib.parse import urlsplit

from autodiscover import __version__
from autodiscover.commercial.contracts import HumanReview, MarketEvidence, Opportunity
from autodiscover.commercial.service import Market
from autodiscover.config import Limits
from autodiscover.evidence.chain import export_snapshot, verify_chain
from autodiscover.hypotheses.allocation import AllocationHypothesis, allocation_demo_proposal
from autodiscover.hypotheses.engine import Hypothesis, demo_proposal
from autodiscover.hypotheses.proposals import ResearchProposal
from autodiscover.orchestrator.lab import Lab
from autodiscover.orchestrator.scheduler import Scheduler
from autodiscover.research.retrieval import Fetcher
from autodiscover.security.redaction import sanitize


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
    allocation_demo = sub.add_parser(
        "allocation-demo", help="Run a reviewed resource-allocation family end to end"
    )
    allocation_demo.add_argument("--topic", default="resource scheduling")
    allocation_demo.add_argument("--algorithm", choices=["dynamic", "greedy"], default="dynamic")
    allocation_demo.add_argument("--config", type=Path, default=Path("config/default.json"))
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
    market_profile = sub.add_parser(
        "market-opportunity", help="Import user/buyer/problem/competition hypotheses"
    )
    market_profile.add_argument("run_id")
    market_profile.add_argument("document", type=Path)
    market_document = sub.add_parser(
        "market-document", help="Import an operator-supplied UTF-8 evidence document"
    )
    market_document.add_argument("run_id")
    market_document.add_argument("document", type=Path)
    market_document.add_argument("--title", required=True)
    market_source = sub.add_parser(
        "market-source", help="Collect an explicitly authorized public HTTPS source"
    )
    market_source.add_argument("run_id")
    market_source.add_argument("url")
    market_source.add_argument("--title", required=True)
    market_source.add_argument("--allow-network", action="store_true")
    market_evidence = sub.add_parser(
        "market-evidence", help="Import source-bound market evidence for review"
    )
    market_evidence.add_argument("opportunity_id")
    market_evidence.add_argument("document", type=Path)
    market_review = sub.add_parser(
        "market-review", help="Interactive human attestation; never automatic model approval"
    )
    market_review.add_argument("evidence_id")
    market_review.add_argument("document", type=Path)
    market_show = sub.add_parser("market-show", help="Recompute current commercial evidence level")
    market_show.add_argument("opportunity_id")
    portfolio = sub.add_parser(
        "portfolio-plan", help="Read-only cost-aware planning; does not authorize experiments"
    )
    portfolio.add_argument("document", type=Path)
    status = sub.add_parser("status", help="Inspect persisted state and verified reports")
    status.add_argument("run_id", nargs="?")
    for command in ("pause", "unpause", "cancel"):
        sub.add_parser(command).add_argument("run_id")
    enqueue = sub.add_parser("enqueue", help="Persist an active run or a new bounded research task")
    enqueue.add_argument("run_id", nargs="?")
    enqueue.add_argument("--topic")
    enqueue.add_argument("--config", type=Path, default=Path("config/default.json"))
    workers = sub.add_parser(
        "workers", help="Run bounded foreground workers; no background service"
    )
    workers.add_argument("--max-steps", type=int, default=100)
    workers.add_argument("--max-seconds", type=float, default=60)
    workers.add_argument("--concurrency", type=int, default=1)
    sub.add_parser("queue", help="Inspect persisted scheduling state")
    jobs = sub.add_parser("jobs", help="Inspect trusted-worker resources/results/recovery state")
    jobs.add_argument("run_id", nargs="?")
    integrity = sub.add_parser("integrity", help="Verify chain against optional retained anchor")
    integrity.add_argument("--anchor", type=Path)
    snapshot = sub.add_parser(
        "snapshot", help="Export no-overwrite evidence snapshot for separate retention"
    )
    snapshot.add_argument("destination", type=Path)
    serve = sub.add_parser(
        "serve", help="Foreground loopback operator read API; no background service"
    )
    serve.add_argument("--port", type=int, default=8765)
    discover = sub.add_parser("discover", help="Run a bounded, checkpointed research experiment")
    discover.add_argument("--spec", type=Path)
    discover.add_argument("--providers", type=Path)
    discover.add_argument("--run-id")
    discovery_mode = discover.add_mutually_exclusive_group()
    discovery_mode.add_argument("--preflight", action="store_true")
    discovery_mode.add_argument("--cache-only", action="store_true")
    discover.add_argument("--allow-live", action="store_true")
    discover.add_argument("--allow-network", action="store_true")
    commercial = sub.add_parser(
        "discovery-commercial", help="Record independent commercial evidence for a candidate"
    )
    commercial.add_argument("run_id")
    commercial.add_argument("direction", type=int)
    commercial.add_argument("observations", type=Path)
    from autodiscover.research.session_cli import add_parser as add_session_parser
    from autodiscover.research.session_cli import run as run_session

    session = add_session_parser(sub)
    args = parser.parse_args()
    if args.command == "session":
        run_session(args, session)
        return
    if args.command == "discovery-commercial":
        from autodiscover.research.discovery_cli import commercial_review

        commercial_review(args, commercial)
        return
    if args.command == "discover":
        from autodiscover.research.discovery_cli import run

        run(args, discover)
        return
    if args.command == "serve":
        import getpass

        import uvicorn
        from pydantic import SecretStr

        from autodiscover.reporting.web import create_app

        if not sys.stdin.isatty():
            parser.error("Operator startup requires an interactive terminal")
        password = SecretStr(getpass.getpass("Temporary operator passphrase (12–200 characters): "))
        app = create_app(args.root, password, port=args.port)
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=args.port,
            proxy_headers=False,
            access_log=False,
            log_level="warning",
        )
        return
    if args.command == "portfolio-plan":
        from autodiscover.hypotheses.portfolio import PortfolioRequest, rank_portfolio

        if args.document.stat().st_size > 65536:
            parser.error("Planning request exceeds 64 KiB")
        request = PortfolioRequest.model_validate_json(args.document.read_text(encoding="utf-8"))
        print(json.dumps(sanitize(rank_portfolio(request)), indent=2))
        return
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
        elif args.command == "allocation-demo":
            hypothesis = allocation_demo_proposal(args.topic)
            hypothesis = hypothesis.model_copy(update={"algorithm": args.algorithm})
            run = lab.explore(
                args.topic,
                [hypothesis],
                limits=Limits.load(args.config),
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
            family = data.get("experiment_family", "encoding-v1")
            schema = {
                "encoding-v1": Hypothesis,
                "allocation-v1": AllocationHypothesis,
                "theoretical": ResearchProposal,
            }.get(family)
            if schema is None:
                parser.error("Unknown or unreviewed experiment family")
            identifier = lab.director.register(args.run_id, schema.model_validate(data))
            result = {"hypothesis_id": identifier, "search": lab.director.tree(args.run_id)}
        elif args.command.startswith("market-"):
            market = Market(lab.store)
            if args.command == "market-show":
                verify_chain(lab.store)
                result = market.assess(args.opportunity_id)
            elif args.command == "market-source":
                host = urlsplit(args.url).hostname
                if not args.allow_network or not host:
                    parser.error("market-source requires an explicit HTTPS URL and --allow-network")
                result = {
                    "source_id": market.collect_source(
                        args.run_id,
                        args.url,
                        title=args.title,
                        fetcher=Fetcher(authorized=True, allowed_hosts=(host,)),
                    )
                }
            elif args.command == "market-document":
                result = {
                    "source_id": market.add_document(args.run_id, args.document, title=args.title)
                }
            else:
                if args.document.stat().st_size > 65536:
                    parser.error("Market JSON exceeds 64 KiB")
                data = args.document.read_text()
                if args.command == "market-opportunity":
                    result = {
                        "opportunity_id": market.save(
                            args.run_id, Opportunity.model_validate_json(data)
                        )
                    }
                elif args.command == "market-evidence":
                    result = {
                        "evidence_id": market.add_evidence(
                            args.opportunity_id, MarketEvidence.model_validate_json(data)
                        )
                    }
                else:
                    if not sys.stdin.isatty():
                        parser.error("Commercial review requires an interactive human terminal")
                    review = HumanReview.model_validate_json(data)
                    _opportunity_id, evidence = market.evidence(args.evidence_id)
                    print(json.dumps(sanitize(evidence.model_dump(mode="json")), indent=2))
                    phrase = (
                        "APPROVE EXTERNAL EVIDENCE"
                        if review.accepted
                        else "REJECT EXTERNAL EVIDENCE"
                    )
                    if input(f"Review the original source, then type {phrase}: ") != phrase:
                        parser.error("Human review was not confirmed")
                    result = {
                        "review_id": market.review(args.evidence_id, review, actor_kind="human")
                    }
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
        elif args.command == "enqueue":
            if args.run_id and args.topic:
                parser.error("Use an existing run ID or a new --topic")
            run_id = args.run_id or lab.store.create_run(
                args.topic or "cross-domain research task",
                Limits.load(args.config).model_dump(mode="json"),
            )
            scheduler = Scheduler(lab.store)
            scheduler.enqueue(run_id)
            result = {"run_id": run_id, "queue": scheduler.status()}
        elif args.command == "workers":
            stop = threading.Event()

            def shutdown(_signal, _frame):
                stop.set()

            previous = {
                sig: signal.signal(sig, shutdown) for sig in (signal.SIGINT, signal.SIGTERM)
            }
            try:
                result = Scheduler(lab.store).run(
                    max_steps=args.max_steps,
                    max_seconds=args.max_seconds,
                    concurrency=args.concurrency,
                    stop=stop,
                )
            finally:
                for sig, handler in previous.items():
                    signal.signal(sig, handler)
        elif args.command == "queue":
            verify_chain(lab.store)
            result = Scheduler(lab.store).status()
        elif args.command == "jobs":
            verify_chain(lab.store)
            result = lab.jobs.status(args.run_id)
        elif args.command == "integrity":
            anchor = json.loads(args.anchor.read_text()) if args.anchor else None
            result = verify_chain(lab.store, anchor.get("anchor", anchor) if anchor else None)
        else:
            result = export_snapshot(lab.store, args.destination)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
