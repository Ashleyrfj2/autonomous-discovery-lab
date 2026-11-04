"""Read-only quality preflight for operator-supplied discovery findings and evidence.

Usage: python -m autodiscover.research.quality_cli INPUT.json
The tool does not alter run ledgers, fetch sources or call inference providers.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from autodiscover.research.discovery_contracts import Evidence
from autodiscover.research.quality import AtomicFinding, MechanismBridge, screen_evidence

MAX_FILE_BYTES = 256_000


def evaluate_file(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("Missing or oversized quality input")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("findings"), list):
        raise ValueError("Quality input must include a findings list")
    if not isinstance(payload.get("evidence"), list):
        raise ValueError("Quality input must include an evidence list")
    if len(payload["findings"]) > 24 or len(payload["evidence"]) > 24:
        raise ValueError("Quality input exceeds the bounded fixture limit")
    findings = [AtomicFinding.model_validate(row) for row in payload["findings"]]
    evidence = [Evidence.model_validate(row) for row in payload["evidence"]]
    bridge = (
        MechanismBridge.model_validate(payload["bridge"])
        if payload.get("bridge") is not None
        else None
    )
    return screen_evidence(findings, evidence, bridge).model_dump(mode="json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline research-quality screening")
    parser.add_argument(
        "input", type=Path, help="JSON containing findings, evidence, and optional bridge"
    )
    args = parser.parse_args(argv)
    try:
        result = evaluate_file(args.input)
    except (OSError, ValueError, TypeError, ValidationError, json.JSONDecodeError):
        parser.exit(2, "Invalid quality input; see the schema and local fixture documentation.\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "eligible_for_critique" else 1


if __name__ == "__main__":
    raise SystemExit(main())
