"""CLI entry point. Commands are added only with verified implementations."""

import argparse
import json
from pathlib import Path

from autodiscover import __version__
from autodiscover.config import Limits


def main() -> None:
    parser = argparse.ArgumentParser(prog="autodiscover")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="Validate a local policy file; no provider calls")
    check.add_argument("--config", type=Path, default=Path("config/default.json"))
    args = parser.parse_args()
    if args.command == "check":
        config = Limits.load(args.config)
        print(json.dumps({"valid": True, "limits": config.model_dump(mode="json")}, indent=2))


if __name__ == "__main__":
    main()
