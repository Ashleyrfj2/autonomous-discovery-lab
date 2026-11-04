"""Foreground discovery command, preflight and read-only packet replay."""

import argparse
import json
import os
import signal
import sys
import threading
from decimal import Decimal
from typing import Any

from pydantic import ValidationError

from autodiscover.evidence.artifacts import Artifacts, IntegrityError
from autodiscover.models.contracts import Provider, ProviderConfig, ProviderError
from autodiscover.models.providers import BASE_URLS, BasetenProvider, MetaProvider
from autodiscover.models.router import Router
from autodiscover.orchestrator.store import SnapshotStore, StateError, Store
from autodiscover.research.discovery import ROLES, Discovery, _journal, replay
from autodiscover.research.discovery_contracts import DiscoverySpec
from autodiscover.research.discovery_sources import EUROPE_PMC_HOST, seed_host
from autodiscover.research.retrieval import Fetcher
from autodiscover.security.budget import BudgetError
from autodiscover.security.redaction import contains_credential


def preflight(spec: DiscoverySpec, configurations: dict[str, ProviderConfig]) -> dict[str, Any]:
    if set(configurations) != set(ROLES):
        raise ValueError("Provider manifest must define exactly the three research roles")
    identities = {(config.kind, config.model) for config in configurations.values()}
    if len(identities) != (3 if spec.mode == "reviewed" else 1):
        raise ValueError("Provider identities do not match the study mode")
    if contains_credential(spec.objective):
        raise ValueError("Objective contains recognizable credentials")
    hosts = {"api.crossref.org", EUROPE_PMC_HOST, *(seed_host(seed) for seed in spec.sources)}
    calls: dict[str, int] = dict(zip(ROLES, (1, 3, 3), strict=True))
    total_input = total_output = 0
    total_cost = Decimal(0)
    roles = {}
    for role, config in configurations.items():
        if not config.structured_output or spec.max_output_tokens > config.output_limit:
            raise ValueError(
                "Discovery requires native schema support and a compatible output limit"
            )
        attempts = calls[role] * (1 + spec.retry_limit)
        inputs = config.context_window * attempts
        outputs = spec.max_output_tokens * attempts
        cost = (
            inputs * config.input_usd_per_million + outputs * config.output_usd_per_million
        ) / Decimal(1_000_000)
        total_input += inputs
        total_output += outputs
        total_cost += cost
        roles[role] = {
            "endpoint": BASE_URLS[config.kind] + "/chat/completions",
            "model": config.model,
            "reasoning_effort": config.reasoning_effort,
            "timeout_seconds": config.timeout_seconds,
            "maximum_logical_calls": calls[role],
            "maximum_attempts": attempts,
            "input_tokens_estimated_upper_bound": inputs,
            "output_tokens_including_reasoning_max": outputs,
            "gross_usd_estimate": str(cost),
            "pricing_source": config.pricing_source,
        }
    return {
        "protocol": spec.protocol,
        "mode": spec.mode,
        "objective": spec.objective,
        "roles": roles,
        "maximum_attempts": sum(calls.values()) * (1 + spec.retry_limit),
        "input_tokens_estimated_upper_bound": total_input,
        "output_tokens_including_reasoning_max": total_output,
        "conservative_gross_usd_estimate": str(total_cost),
        "wall_seconds_per_invocation": spec.seconds,
        "retry_limit_per_logical_call": spec.retry_limit,
        "searches_max": 4,
        "bibliographic_fetches_max": 8,
        "registered_document_fetches_max": len(spec.sources),
        "public_hosts": sorted(hosts),
        "stop_conditions": [
            "Wall deadline, cancellation, or lease loss",
            "Invalid, incomplete, or ambiguous provider outcome",
            "At most two candidates and one targeted search and revision",
            "No revision without distinct new evidence",
        ],
        "notes": "Estimate uses local context bound, full output including reasoning, all retries "
        "and uncached standard rates. No credit discount or dollar admission limit. "
        "Live execution sends public excerpts and requires explicit approval.",
    }


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    try:
        if args.cache_only:
            if (
                not args.run_id
                or args.spec
                or args.providers
                or args.allow_live
                or args.allow_network
            ):
                parser.error("--cache-only requires only --run-id")
            with SnapshotStore(args.root) as store:
                digest, report = replay(store, args.run_id)
        else:
            if not args.providers or bool(args.spec) == bool(args.run_id):
                parser.error("Provide --providers and exactly one of --spec or --run-id")
            if args.spec:
                spec = DiscoverySpec.model_validate_json(args.spec.read_text())
            else:
                with SnapshotStore(args.root) as store:
                    journal, _ = _journal(store, args.run_id)
                    artifacts = Artifacts(store.root / "artifacts", read_only=True)
                    spec = DiscoverySpec.model_validate(
                        artifacts.get_json(journal["registered"])["specification"]
                    )
            configurations = {
                role: ProviderConfig.model_validate(config)
                for role, config in json.loads(args.providers.read_text()).items()
            }
            estimate = preflight(spec, configurations)
            if args.preflight:
                if args.allow_live or args.allow_network:
                    parser.error("--preflight accepts no external access flags")
                print(json.dumps(estimate, indent=2))
                return
            if not (args.allow_live and args.allow_network):
                parser.error("Live discovery requires both --allow-live and --allow-network")
            missing = sorted(
                {
                    config.api_key_env
                    for config in configurations.values()
                    if not os.environ.get(config.api_key_env, "").strip()
                }
            )
            if missing:
                parser.error(
                    f"Missing provider credentials: {', '.join(missing)}. "
                    "Export them or use uv run --env-file with your ignored local env file."
                )
            store = Store(args.root)
            routes: dict[str, list[Provider]] = {}
            for role, config in configurations.items():
                authorized = config.model_copy(update={"live_authorized": True})
                adapter = MetaProvider if config.kind == "meta" else BasetenProvider
                routes[role] = [adapter(authorized)]
            discovery = Discovery(
                Router(store, routes),
                Fetcher(authorized=True, allowed_hosts=tuple(estimate["public_hosts"]), timeout=8),
                allow_retrieval=True,
            )
            run_id = args.run_id or discovery.register(spec, stable=True)
            print(f"Discovery run {run_id}", file=sys.stderr, flush=True)
            interrupted = threading.Event()

            def stop(_signum, _frame):
                interrupted.set()

            handlers = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
            try:
                digest, report = discovery.execute(run_id, stop_requested=interrupted.is_set)
            finally:
                for sig, handler in handlers.items():
                    signal.signal(sig, handler)
        print(json.dumps({"artifact_digest": digest, **report.model_dump(mode="json")}, indent=2))
    except (BudgetError, IntegrityError, ProviderError, StateError) as error:
        parser.exit(1, f"Discovery stopped ({type(error).__name__}). See the run ledger.\n")
    except (ValidationError, OSError, TypeError, ValueError, AttributeError):
        parser.exit(2, "Invalid discovery configuration or inaccessible local files.\n")


def commercial_review(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    from autodiscover.research.discovery_validation import (
        CommercialReview,
        record_commercial_review,
    )

    if not sys.stdin.isatty():
        parser.error(
            "Commercial review requires an independent operator at an interactive terminal"
        )
    try:
        review = CommercialReview.model_validate_json(args.observations.read_text())
        phrase = f"ATTEST {args.run_id} {args.direction}"
        if input(f"Review original source documents and type {phrase}: ") != phrase:
            parser.error("Commercial review was not attested")
        result = record_commercial_review(
            Store(args.root),
            args.run_id,
            args.direction,
            review,
            operator_attested=True,
        )
        print(json.dumps(result, indent=2))
    except (OSError, StateError, ValueError, EOFError):
        parser.exit(2, "Commercial evidence could not be verified or recorded.\n")
