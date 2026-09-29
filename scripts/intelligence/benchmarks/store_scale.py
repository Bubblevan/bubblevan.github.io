from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any

from ..connectors.base import ConnectorCheckpoint, ConnectorContext, ConnectorSpec, FetchResult
from ..connectors.registry import ConnectorRegistry
from ..connectors.state import ConnectorStateStore
from ..graph.backfill import graph_backfill
from ..ids import source_id
from ..models import new_observation, new_source
from ..retrieval.corpus import build_snapshot
from ..runner import run_source
from ..store import JsonlStore


class _SyntheticConnector:
    spec = ConnectorSpec("scale-benchmark", "1", ("api",), frozenset({"pull"}))

    def __init__(self, observations: list[dict[str, Any]]):
        self.observations = observations

    def fetch(self, _source, _checkpoint, context):
        return FetchResult(self.observations, ConnectorCheckpoint(last_success_at=context.now()), True,
                           {"entries_fetched": len(self.observations), "pages": 1})


def benchmark_size(count: int, *, now: str = "2026-09-29T00:00:00Z") -> dict[str, Any]:
    if count < 1:
        raise ValueError("benchmark size must be positive")
    with tempfile.TemporaryDirectory(prefix="ri-store-scale-") as temp:
        root = Path(temp)
        store = JsonlStore(root / "events")
        source = new_source(identity=f"benchmark|scale|{count}", source_type="publication",
                            platform="synthetic", name="Synthetic scale benchmark",
                            canonical_url="https://example.org/research", connector="scale-benchmark",
                            mode="api", created_at=now)
        observations = [_observation(source["source_id"], index, now) for index in range(count)]
        connector = _SyntheticConnector(observations)
        registry = ConnectorRegistry([connector])
        states = ConnectorStateStore(root / "runtime")
        context = ConnectorContext(store=store, now=lambda: now)

        started = time.perf_counter()
        ingest = run_source(source, registry, states, store, context)
        ingest_seconds = time.perf_counter() - started

        started = time.perf_counter()
        graph = graph_backfill(store, root / "runtime", now=now)
        graph_seconds = time.perf_counter() - started

        started = time.perf_counter()
        corpus = build_snapshot(store)
        corpus_seconds = time.perf_counter() - started

        return {
            "observations": count,
            "artifacts": ingest["artifacts_touched"],
            "ingest_replay": {"seconds": round(ingest_seconds, 3),
                              "records_per_second": round(count / max(ingest_seconds, 1e-9), 2),
                              "new_observations": ingest["new_observations"]},
            "graph_backfill": {"seconds": round(graph_seconds, 3),
                               "edges": graph["edges_total"],
                               "edges_per_second": round(graph["edges_total"] / max(graph_seconds, 1e-9), 2)},
            "corpus_snapshot": {"seconds": round(corpus_seconds, 3),
                                "documents": len(corpus.documents),
                                "corpus_hash": corpus.corpus_hash},
            "peak_rss_mb": _peak_rss_mb(),
        }


def run_benchmarks(sizes: list[int] | None = None) -> dict[str, Any]:
    selected = sizes or [3000, 10000, 30000]
    if selected != sorted(set(selected)) or any(value < 1 for value in selected):
        raise ValueError("sizes must be increasing unique positive integers")
    # Isolate sizes so Windows PeakWorkingSetSize is a true per-size high-water
    # mark instead of retaining the previous size's process peak.
    module = f"{__package__}.store_scale"
    rows = []
    for size in selected:
        completed = subprocess.run(
            [sys.executable, "-m", module, "--single-size", str(size)],
            check=False, capture_output=True, text=True,
        )
        if completed.returncode:
            raise RuntimeError(f"isolated benchmark failed for size {size}")
        rows.append(json.loads(completed.stdout))
    baseline = rows[0]
    for row in rows:
        row["slowdown_vs_first_size"] = {
            key: round(float(row[key]["seconds"]) / max(float(baseline[key]["seconds"]), 1e-9), 3)
            for key in ("ingest_replay", "graph_backfill", "corpus_snapshot")
        }
    return {"benchmark": "ri-jsonl-store-scale-v1", "created_at": datetime.now(timezone.utc).isoformat(),
            "sizes": rows, "notes": [
                "Timings are local diagnostics, not fixed machine pass/fail thresholds.",
                "10x growth ratios are shown relative to the first requested size.",
                "The benchmark uses synthetic public-like records and temporary storage.",
            ]}


def _observation(source_id_value: str, index: int, now: str) -> dict[str, Any]:
    suffix = f"{index + 1:05d}"
    doi = f"10.5555/ri-scale.{suffix}"
    candidate = {
        "artifact_type": "paper", "title": f"Synthetic retrieval systems paper {suffix}",
        "canonical_url": f"https://doi.org/{doi}", "identifiers": {"doi": doi},
        "authors": ["Synthetic Author"], "organizations": [], "summary": "Synthetic benchmark abstract.",
        "published_at": now, "topics": ["topic-search-agent"],
        "mention": {"role": "primary", "evidence_level": "api_metadata", "origin": "scale_benchmark",
                    "confidence": 1.0},
    }
    return new_observation(
        identity=f"benchmark|observation|{index + 1}", source_id=source_id_value,
        platform="synthetic", platform_object_id=f"paper-{index + 1}", kind="indexed_work",
        title=candidate["title"], text=candidate["summary"], urls=[candidate["canonical_url"]],
        media=[], published_at=now, observed_at=now, topics=["topic-search-agent"],
        authors=["Synthetic Author"], provenance={"retrieval_mode": "synthetic",
        "evidence_level": "api_metadata", "source_url": "https://example.org/research",
        "collector": "scale-benchmark"}, artifact_candidates=[candidate],
    )


def _peak_rss_mb() -> float | None:
    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            class _MemoryCounters(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
                    ("PrivateUsage", ctypes.c_size_t),
                ]

            counters = _MemoryCounters()
            counters.cb = ctypes.sizeof(counters)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            psapi = ctypes.WinDLL("psapi", use_last_error=True)
            get_current_process = kernel32.GetCurrentProcess
            get_current_process.restype = wintypes.HANDLE
            get_process_memory_info = psapi.GetProcessMemoryInfo
            get_process_memory_info.argtypes = (wintypes.HANDLE, ctypes.POINTER(_MemoryCounters), wintypes.DWORD)
            get_process_memory_info.restype = wintypes.BOOL
            if not get_process_memory_info(get_current_process(), ctypes.byref(counters), counters.cb):
                return None
            return round(float(counters.PeakWorkingSetSize) / (1024 * 1024), 2)
        except (AttributeError, OSError, ValueError):
            return None
    try:
        import psutil
        info = psutil.Process().memory_info()
        peak = getattr(info, "peak_wset", None) or getattr(info, "rss", None)
        return round(float(peak) / (1024 * 1024), 2) if peak else None
    except (ImportError, OSError, AttributeError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark 3k/10k/30k JSONL ingestion, graph and snapshot paths.")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--sizes", nargs="+", type=int, default=None)
    selection.add_argument("--single-size", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    result = (benchmark_size(args.single_size) if args.single_size is not None
              else run_benchmarks(args.sizes or [3000, 10000, 30000]))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
