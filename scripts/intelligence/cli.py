from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

from .bridge_capture import ingest_capture
from .bridge_xhs import ingest_xhs
from .store import JsonlStore
from .aliases import ArtifactAliases
from .connectors.base import ConnectorContext
from .connectors.registry import connector_registry
from .connectors.state import ConnectorStateStore
from .ids import artifact_id
from .resolver import SemanticScholarResolver, materialize_semantic_scholar_result
from .runner import load_source_catalog, run_source


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STORE = REPO_ROOT / "data" / "intelligence" / "events"
DEFAULT_RUNTIME = REPO_ROOT / "data" / "intelligence" / "runtime"


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

    commands.add_parser("connectors", help="list available connector ids and capabilities")
    commands.add_parser("sources", help="list source ids from the seed catalog")
    run = commands.add_parser("run-source", help="run one configured source once")
    run.add_argument("source_id")
    run.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    run.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)

    run_all = commands.add_parser("run-all", help="run each active source once")
    run_all.add_argument("--once", action="store_true", required=True)
    run_all.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    run_all.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)

    state = commands.add_parser("connector-state", help="show one local connector checkpoint")
    state.add_argument("source_id")
    state.add_argument("--runtime-dir", type=Path, default=DEFAULT_RUNTIME)

    smoke = commands.add_parser("smoke", help="explicitly run an optional live resolver smoke check")
    smoke.add_argument("provider", choices=["semantic-scholar"])
    smoke.add_argument("--arxiv", required=True)
    smoke.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)

    resolve = commands.add_parser("resolve-artifact", help="optionally reconcile an artifact with Semantic Scholar")
    resolve.add_argument("artifact_id")
    resolve.add_argument("--store-dir", type=Path, default=DEFAULT_STORE)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        store = JsonlStore(getattr(args, "store_dir", DEFAULT_STORE))
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
        if args.command == "connectors":
            _print_json([
                {
                    "connector_id": spec.connector_id,
                    "version": spec.version,
                    "modes": list(spec.modes),
                    "capabilities": sorted(spec.capabilities),
                    "requires_auth": spec.requires_auth,
                    "supports_incremental": spec.supports_incremental,
                }
                for spec in connector_registry().list()
            ])
            return 0
        if args.command == "sources":
            _print_json([
                {"source_id": source["source_id"], "name": source["name"],
                 "connector": source["acquisition"]["connector"], "status": source["status"]}
                for source in load_source_catalog()
            ])
            return 0
        if args.command in {"run-source", "run-all"}:
            sources = load_source_catalog()
            if args.command == "run-source":
                source = next((item for item in sources if item["source_id"] == args.source_id), None)
                if source is None:
                    raise ValueError(f"source not found in catalog: {args.source_id}")
                selected = [source]
            else:
                selected = [item for item in sources if item["status"] == "active"]
            states = ConnectorStateStore(args.runtime_dir)
            registry = connector_registry()
            results = [run_source(item, registry, states, store, ConnectorContext(store=store)) for item in selected]
            _print_json(results[0] if args.command == "run-source" else results)
            return 0
        if args.command == "connector-state":
            state = ConnectorStateStore(args.runtime_dir).load(args.source_id)
            if state is None:
                raise ValueError(f"connector state not found: {args.source_id}")
            from dataclasses import asdict
            _print_json(asdict(state))
            return 0
        if args.command == "smoke":
            from .canonicalize import extract_arxiv_id
            arxiv = extract_arxiv_id(args.arxiv)
            if not arxiv:
                raise ValueError("smoke requires a valid arXiv identifier")
            with tempfile.TemporaryDirectory(prefix="ri-s2-smoke-") as temp:
                result = SemanticScholarResolver().resolve(
                    {"identifiers": {"arxiv": arxiv}, "title": ""},
                    artifact_id(f"arxiv:{arxiv}"), ArtifactAliases(temp), ConnectorContext(store=store),
                )
            _print_json(result)
            return 0
        if args.command == "resolve-artifact":
            aliases = ArtifactAliases(args.store_dir)
            canonical_id = aliases.resolve_artifact_id(args.artifact_id)
            artifact = store.get_by_id("artifact", canonical_id) or store.get_by_id("artifact", args.artifact_id)
            if artifact is None:
                raise ValueError(f"artifact not found: {args.artifact_id}")
            result = SemanticScholarResolver().resolve(
                artifact, str(artifact["artifact_id"]), aliases, ConnectorContext(store=store),
            )
            resolved_artifact = materialize_semantic_scholar_result(result, artifact, store)
            if resolved_artifact:
                result["materialized_artifact"] = resolved_artifact
            _print_json(result)
            return 0
        raise ValueError(f"unsupported command: {args.command}")
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError, RuntimeError) as exc:
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
