from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Callable

from ..cli import DEFAULT_PRIVATE_ROOT, DEFAULT_RUNTIME, DEFAULT_STORE
from .daily import run_daily_pipeline


def build_daily_summary(result: dict[str, Any]) -> str:
    run = result.get("run") if isinstance(result.get("run"), dict) else {}
    run_date = str(run.get("run_date") or date.today().isoformat())
    if len(run_date) != 10 or run_date[4:5] != "-" or run_date[7:8] != "-":
        run_date = "未知日期"

    labels = {
        "completed": "完成",
        "partial": "部分完成",
        "failed": "失败",
        "running": "未完成",
    }
    status = str(run.get("status") or result.get("status") or "unknown")
    status_label = labels.get(status, "未知")
    source = run.get("source_summary") if isinstance(run.get("source_summary"), dict) else {}
    health = run.get("source_health") if isinstance(run.get("source_health"), dict) else {}
    feed = run.get("feed_metrics") if isinstance(run.get("feed_metrics"), dict) else {}
    stages = run.get("stages") if isinstance(run.get("stages"), list) else []

    def count(row: dict[str, Any], key: str) -> int:
        try:
            return max(0, int(row.get(key) or 0))
        except (TypeError, ValueError):
            return 0

    total = count(source, "sources_total")
    succeeded = count(source, "sources_succeeded")
    failed = count(source, "sources_failed")
    deferred = count(source, "sources_deferred")
    fetched = count(source, "fetched")
    new_observations = count(source, "new_observations")
    new_artifacts = count(source, "new_artifacts")
    feed_selected = count(feed, "selected_count")
    feed_revision = count(feed, "revision")

    corpus_hash = run.get("corpus_hash_after")
    short_hash = str(corpus_hash)[:12] if isinstance(corpus_hash, str) and corpus_hash else "未生成"
    source_stats_available = "sources_total" in source
    acquisition_failure = next((stage for stage in reversed(stages)
                                if isinstance(stage, dict) and stage.get("stage") == "acquisition"
                                and stage.get("status") == "failed"), None)
    if source_stats_available:
        source_line = f"来源：{succeeded}/{total} 成功，{failed} 失败，{deferred} 延后"
        acquisition_line = (
            f"采集：抓取 {fetched} 条，新 Observation {new_observations} 条，新 Artifact {new_artifacts} 个"
        )
    elif acquisition_failure:
        failure_class = str(acquisition_failure.get("error_class") or "未知错误")[:80]
        source_line = f"来源：未生成统计（采集阶段中断，{failure_class}）"
        acquisition_line = "采集：未生成统计"
    else:
        source_line = "来源：未生成统计"
        acquisition_line = "采集：未生成统计"
    feed_line = (
        f"Feed：{feed_selected} 条，revision {feed_revision}；刷新待处理：{'是' if run.get('feed_refresh_pending') else '否'}"
        if run.get("feed_run_id") else "Feed：未生成"
    )
    health_line = (
        "来源健康："
        f"{count(health, 'healthy')} healthy，{count(health, 'deferred')} deferred，"
        f"{count(health, 'stale')} stale，{count(health, 'failing')} failing，"
        f"{count(health, 'never_run')} never-run"
        if health else "来源健康：未生成"
    )
    lines = [
        f"研究情报每日任务｜{run_date}",
        f"状态：{status_label}",
        source_line,
        acquisition_line,
        feed_line,
        f"语料：{short_hash}",
        health_line,
    ]
    if result.get("reused") is True:
        lines.append("本次复用了当天已完成的运行结果。")
    return "\n".join(lines)


def resolve_hermes_path(value: str | None) -> Path:
    candidate = value or shutil.which("hermes.exe") or shutil.which("hermes")
    if not candidate:
        raise FileNotFoundError("Hermes CLI path is required for scheduled summary delivery")
    path = Path(candidate).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError("Hermes CLI executable was not found")
    return path


def send_summary(message: str, *, hermes_path: Path, target: str) -> None:
    result = subprocess.run(
        [str(hermes_path), "send", "--to", target, "--quiet"],
        input=message,
        text=True,
        encoding="utf-8",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=60,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Hermes summary delivery failed")


def run_scheduled_pipeline(*, hermes_path: Path, target: str = "weixin",
                           pipeline: Callable[..., dict[str, Any]] = run_daily_pipeline,
                           sender: Callable[..., None] = send_summary,
                           store_dir: Path = DEFAULT_STORE,
                           runtime_dir: Path = DEFAULT_RUNTIME,
                           private_root: Path = DEFAULT_PRIVATE_ROOT,
                           mode: str = "production") -> int:
    try:
        result = pipeline(
            store_dir=store_dir,
            runtime_dir=runtime_dir,
            private_root=private_root,
            mode=mode,
            scheduled=True,
        )
        message = build_daily_summary(result)
        pipeline_exit = int(result.get("exit_code", 1))
    except Exception:
        message = (
            f"研究情报每日任务｜{date.today().isoformat()}\n"
            "状态：失败\n"
            "运行入口未能生成可用日报；请检查本机任务历史。"
        )
        pipeline_exit = 1

    try:
        sender(message, hermes_path=hermes_path, target=target)
    except Exception:
        print("Hermes summary delivery failed; check Hermes and its messaging connection.", file=sys.stderr)
        return 1

    if pipeline_exit == 2:
        return 0  # Partial but usable runs remain successful Task Scheduler runs.
    return 0 if pipeline_exit == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the daily Research Intelligence pipeline and send its aggregate completion summary via Hermes."
    )
    parser.add_argument("--hermes-path", default=None)
    parser.add_argument("--target", default="weixin", choices=("weixin",))
    parser.add_argument("--mode", default="production", choices=("production", "smoke"))
    args = parser.parse_args(argv)
    try:
        hermes_path = resolve_hermes_path(args.hermes_path)
    except OSError:
        print("Hermes CLI is unavailable; scheduled summary delivery is not configured.", file=sys.stderr)
        return 1
    return run_scheduled_pipeline(hermes_path=hermes_path, target=args.target, mode=args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
