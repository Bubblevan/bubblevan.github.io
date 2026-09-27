from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from .bridge_capture import ingest_capture
from .bridge_xhs import ingest_xhs
from .store import JsonlStore


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STORE = REPO_ROOT / "data" / "intelligence" / "events"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline Personal Research Intelligence data layer.")
    commands = parser.add_subparsers(dest="command", required=True)

    for name in ("ingest-xhs", "ingest-capture"):
        command = commands.add_parser(name)
        command.add_argument("json_file", type=Path)
        command.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    inspect = commands.add_parser("inspect-artifact")
    inspect.add_argument("artifact_id")
    inspect.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    stats = commands.add_parser("stats")
    stats.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        store = JsonlStore(args.store_dir)
        if args.command in {"ingest-xhs", "ingest-capture"}:
            payload = _read_json_object(args.json_file)
            if args.command == "ingest-xhs":
                source, observation, artifact_ids = ingest_xhs(payload, store)
                _print_json(
                    {
                        "source_id": source["source_id"],
                        "observation_id": observation["observation_id"],
                        "artifact_ids": artifact_ids,
                    }
                )
            else:
                source, observation = ingest_capture(payload, store)
                _print_json(
                    {"source_id": source["source_id"], "observation_id": observation["observation_id"]}
                )
            return 0
        if args.command == "inspect-artifact":
            artifact = store.get_by_id("artifact", args.artifact_id)
            if artifact is None:
                raise ValueError(f"artifact not found: {args.artifact_id}")
            _print_json(artifact)
            return 0
        if args.command == "stats":
            _print_json(store.stats())
            return 0
        raise ValueError(f"unsupported command: {args.command}")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("input JSON must be one object")
    return payload


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
