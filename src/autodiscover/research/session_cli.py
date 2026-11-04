"""Session preflight, opt-in launch, read-only status and durable controls."""

import argparse
import hashlib
import json
import os
import signal
import sys
import threading
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

from pydantic import ValidationError

from autodiscover.evidence.artifacts import IntegrityError
from autodiscover.models.contracts import Provider, ProviderConfig, ProviderError
from autodiscover.models.providers import MetaProvider
from autodiscover.models.router import Router
from autodiscover.orchestrator.durability import canonical
from autodiscover.orchestrator.store import SnapshotStore, StateError, Store
from autodiscover.research.discovery import Discovery
from autodiscover.research.discovery_cli import preflight
from autodiscover.research.retrieval import Fetcher
from autodiscover.research.session import Session, create_session, registration, request_pause
from autodiscover.research.session import session_report as report
from autodiscover.research.session_contracts import SessionProfile
from autodiscover.research.session_rehearsal import rehearsal

DEFAULT_PROVIDERS = Path("config/discovery-meta.json")


def add_parser(sub: argparse._SubParsersAction) -> argparse.ArgumentParser:
    parser = sub.add_parser("session", help="Control a durable, foreground discovery session")
    commands = parser.add_subparsers(dest="session_command", required=True)
    for name in ("preflight", "dry-run", "start"):
        command = commands.add_parser(name)
        command.add_argument("--profile", type=Path, required=True)
        command.add_argument("--providers", type=Path, default=DEFAULT_PROVIDERS)
        if name == "preflight":
            command.add_argument("--check-model-access", action="store_true")
            command.add_argument("--allow-network", action="store_true")
        if name == "start":
            command.add_argument("--authorize-live", action="store_true")
            command.add_argument("--allow-network", action="store_true")
    for name in ("status", "pause", "resume", "cancel", "report"):
        command = commands.add_parser(name)
        command.add_argument("session_id")
        if name == "resume":
            command.add_argument("--providers", type=Path, default=DEFAULT_PROVIDERS)
            command.add_argument("--authorize-live", action="store_true")
            command.add_argument("--allow-network", action="store_true")
        if name == "cancel":
            command.add_argument("--confirm", action="store_true")
    return parser


def _load(path: Path) -> dict:
    if path.stat().st_size > 65536:
        raise ValueError("Configuration exceeds 64 KiB")
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError("Configuration must be an object")
    return result


def _configs(path: Path) -> dict[str, ProviderConfig]:
    configs = {role: ProviderConfig.model_validate(data) for role, data in _load(path).items()}
    if any(config.kind != "meta" for config in configs.values()):
        raise ValueError("Session live profiles use the qualified Meta route")
    return configs


def _clients(configs: dict[str, ProviderConfig]) -> dict[str, MetaProvider]:
    if any(not os.environ.get(config.api_key_env, "").strip() for config in configs.values()):
        raise ValueError("Required provider credential environment variable is missing")
    return {
        role: MetaProvider(config.model_copy(update={"live_authorized": True}))
        for role, config in configs.items()
    }


def session_preflight(profile: SessionProfile, configs: dict[str, ProviderConfig]) -> dict:
    single = preflight(profile.discovery, configs)
    attempts = single["maximum_attempts"]
    tokens = (
        single["input_tokens_estimated_upper_bound"]
        + single["output_tokens_including_reasoning_max"]
    )
    digest = hashlib.sha256(
        canonical(
            {
                role: config.model_dump(mode="json", exclude={"api_key_env", "live_authorized"})
                for role, config in configs.items()
            }
        ).encode()
    ).hexdigest()
    branch = {
        "attempts": attempts,
        "tokens": tokens,
        "providers_digest": digest,
        "gross_usd": single["conservative_gross_usd_estimate"],
    }
    count = 0
    while not Session._admission_stop(profile, branch, count):
        count += 1
    if not count:
        raise ValueError("Selected profile cannot admit one branch at its configured upper bound")
    return {
        "profile": profile.model_dump(mode="json"),
        "branch": branch,
        "roles": single["roles"],
        "public_hosts": single["public_hosts"],
        "max_admitted_branches": count,
        "max_attempts": count * attempts,
        "max_estimated_tokens_including_reasoning": count * tokens,
        "max_calculated_gross_usd": str(Decimal(branch["gross_usd"]) * count),
        "max_parallel_requests": min(profile.concurrency, count),
        "max_bibliographic_fetches": count * single["bibliographic_fetches_max"],
        "model_access": "not checked",
        "credential_environment": sorted({c.api_key_env for c in configs.values()}),
        "stop_conditions": [
            "Session duration, call/token/branch limit, or optional aggregate cost ceiling",
            "Consecutive provider failures or research stagnation",
            "Pause, cancellation, signal, or ambiguous reservation requiring reconciliation",
        ],
        "recovery_command": "autodiscover --root ROOT session resume SESSION_ID",
        "cancel_command": "autodiscover --root ROOT session cancel SESSION_ID --confirm",
        "live_resume_flags": "--providers MANIFEST --authorize-live --allow-network",
    }


def _factory(
    store: Store,
    configs: dict[str, ProviderConfig],
    estimate: dict,
    *,
    live: bool,
) -> Callable[[int], Discovery]:
    if not live:
        if estimate["profile"]["discovery"].get("capability"):
            from autodiscover.research.capability_rehearsal import rehearsal as capability_rehearsal

            return lambda branch: capability_rehearsal(store, branch)
        return lambda branch: rehearsal(store, branch)
    clients = _clients(configs)

    def build(_branch: int) -> Discovery:
        routes: dict[str, list[Provider]] = {role: [client] for role, client in clients.items()}
        return Discovery(
            Router(store, routes),
            Fetcher(authorized=True, allowed_hosts=tuple(estimate["public_hosts"]), timeout=8),
            allow_retrieval=True,
        )

    return build


def _write(value: object) -> None:
    print(json.dumps(value, indent=2))


def run(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    action = args.session_command
    try:
        if action in {"status", "report"}:
            with SnapshotStore(args.root) as store:
                _write(report(store, args.session_id, dossiers=action == "report"))
            return
        if action in {"pause", "cancel"}:
            store = Store(args.root)
            if not store.is_session(args.session_id):
                raise StateError("Unknown session")
            if action == "pause":
                request_pause(store, args.session_id)
            else:
                if not args.confirm:
                    parser.error("Cancel requires --confirm")
                from autodiscover.evidence.chain import verify_chain

                verify_chain(store)
                store.control(args.session_id, "cancel")
            _write(report(store, args.session_id, dossiers=False))
            return

        configs = _configs(args.providers)
        saved = None
        if action == "resume":
            with SnapshotStore(args.root) as view:
                saved = registration(view, args.session_id)
            profile = SessionProfile.model_validate(saved["profile"])
            live = saved["live"]
        else:
            profile = SessionProfile.model_validate(_load(args.profile))
            live = action == "start"
        estimate = session_preflight(profile, configs)
        if action == "preflight":
            if args.check_model_access:
                if not args.allow_network:
                    parser.error("Model catalog access requires --allow-network")
                estimate["model_access"] = {
                    role: provider.health_check() for role, provider in _clients(configs).items()
                }
            _write(estimate)
            return
        if live and not (args.authorize_live and args.allow_network):
            parser.error("Live execution requires --authorize-live and --allow-network")
        if saved is not None and estimate["branch"] != saved["admission"]:
            raise StateError("Provider manifest differs from the session registration")
        if action == "dry-run":
            # Rehearse using the same state machine with a short, no-network profile.
            profile = SessionProfile.model_validate(
                {
                    **profile.model_dump(mode="json"),
                    "duration_seconds": min(profile.duration_seconds, 90),
                    "max_branches": min(profile.max_branches, 4),
                    "concurrency": min(profile.concurrency, 2),
                }
            )
            estimate = session_preflight(profile, configs)
        store = Store(args.root)
        factory = _factory(store, configs, estimate, live=live)
        session_id = (
            args.session_id
            if action == "resume"
            else create_session(
                store,
                profile,
                estimate["branch"],
                live=live,
            )
        )
        print(f"Session {session_id}", file=sys.stderr, flush=True)
        stopped = threading.Event()
        handlers = {
            sig: signal.signal(sig, lambda _signum, _frame: stopped.set())
            for sig in (signal.SIGTERM, signal.SIGINT)
        }
        try:
            Session(store, factory).execute(session_id, stop=stopped, resume=action == "resume")
        finally:
            for sig, handler in handlers.items():
                signal.signal(sig, handler)
        outcome = report(store, session_id, dossiers=False)
        _write(outcome)
        if outcome["unresolved_reservations"]:
            parser.exit(1, "Session requires provider reconciliation. Inspect its saved status.\n")
    except ProviderError:
        parser.exit(1, "Provider catalog or execution check failed. Inspect saved status.\n")
    except (StateError, IntegrityError):
        parser.exit(
            1, "Session state, integrity or reconciliation blocked execution. Use status.\n"
        )
    except (OSError, ValueError, ValidationError, KeyError, TypeError):
        parser.exit(
            2, "Invalid or inaccessible session profile, provider manifest or credentials.\n"
        )
