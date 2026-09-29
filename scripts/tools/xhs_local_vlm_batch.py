#!/usr/bin/env python3
"""Sequential, resumable local Qwen3-VL pass over the unreviewed XHS images."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import signal
import sys
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / ".cache" / "xhs-extracted"
INDEX = DATA / "image-source-index.jsonl"
DIRECT = DATA / "image-visual-review.jsonl"
CALIBRATION = DATA / "qwen3-vl-calibration.json"
OUT = DATA / "qwen3-vl-image-descriptions.jsonl"
CHECKPOINT = DATA / "qwen3-vl-image-descriptions.checkpoint.json"
QUEUE = DATA / "qwen3-vl-image-queue.jsonl"
API = "http://127.0.0.1:18987/v1/chat/completions"
MODEL = "Qwen3-VL-8B-Instruct-GGUF Q4_K_M"
GPU_LAYERS = 12
RESTART_EVERY = 5
PID_FILE = DATA / "llama-server.pid"
SERVER_EXE = ROOT / ".cache" / "xhs-extracted" / "llama-cpp-b11207" / "llama-server.exe"
MODEL_FILE = ROOT / ".cache" / "xhs-extracted" / "models" / "Qwen3VL-8B-Instruct-Q4_K_M.gguf"
MM_PROJ_FILE = ROOT / ".cache" / "xhs-extracted" / "models" / "mmproj-Qwen3VL-8B-Instruct-Q8_0.gguf"

PROMPT_VERSION = "xhs-image-v2-content-source"
PROMPT = """只根据图中可见内容识读，不查外部资料、不猜来源、不输出思维过程。只返回一个简体中文 JSON 对象，不要 markdown：
{"title":"可见标题","identifier":"可见论文编号","visible_links":["清楚可见的网址，去掉查询参数"],"source_names":["图中清楚可见的平台、出版物或项目"],"source_evidence":"图上来源标记；没有写未见","main_content":"最多两句，概括主要内容","uncertainties":[]}。
看不清的字段留空并说明；不补全截断文字，不分析作者机构，不把推测写成事实。"""

SENSITIVE_QUERY = re.compile(
    r"(?i)(?:[?&](?:xsec_token|token|access_token|refresh_token|signature|sign|auth|authorization|cookie|session|secret|api_key|key)=)[^&#\s]*"
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
                if not isinstance(row, dict):
                    raise RuntimeError(f"Expected JSON object at {path}:{line_no}")
                rows.append(row)
    return rows


def key_of(row: dict[str, Any]) -> tuple[str, int]:
    return str(row.get("note_id", "")), int(row.get("image_index", -1))


def dump_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def save_checkpoint(done: dict[tuple[str, int], dict[str, Any]], last_key: tuple[str, int] | None) -> None:
    counts = {status: sum(1 for row in done.values() if row.get("status") == status)
              for status in ("ok", "partial", "failed")}
    body = {
        "schema_version": 1,
        "updated_at": now(),
        "model": MODEL,
        "runtime": {"llama_cpp_version": "0.5.0-dev (build 11207, commit 7ac59a6e3)",
                    "context": 4096, "gpu_layers": GPU_LAYERS, "parallel": 1,
                    "image_min_tokens": 512, "host": "127.0.0.1", "port": 18987},
        "prompt_version": PROMPT_VERSION,
        "total_queue": 1454,
        "record_counts": counts,
        "last_completed_key": {"note_id": last_key[0], "image_index": last_key[1]} if last_key else None,
    }
    tmp = CHECKPOINT.with_suffix(CHECKPOINT.suffix + ".tmp")
    tmp.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, CHECKPOINT)


def clean_links(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    links = []
    for item in value:
        if not isinstance(item, str):
            continue
        item = SENSITIVE_QUERY.sub("", item.strip())
        # The corpus intentionally stores canonical, query-free links.
        item = re.sub(r"([?&])[^\s]*$", "", item).rstrip("?&")
        if item and item not in links:
            links.append(item)
    return links


def clean_result(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("No JSON object in model response")
    obj = json.loads(text[start:end + 1])
    if not isinstance(obj, dict):
        raise ValueError("Model response is not a JSON object")
    def string(name: str) -> str:
        value = obj.get(name, "")
        return SENSITIVE_QUERY.sub("", value.strip()) if isinstance(value, str) else ""
    def strings(name: str) -> list[str]:
        value = obj.get(name, [])
        if not isinstance(value, list):
            return []
        return [SENSITIVE_QUERY.sub("", x.strip()) for x in value if isinstance(x, str) and x.strip()]
    return {
        "title": string("title"),
        "identifier": string("identifier"),
        "visible_links": clean_links(obj.get("visible_links", [])),
        "source_names": strings("source_names"),
        "source_evidence": string("source_evidence"),
        "main_content": string("main_content"),
        "uncertainties": strings("uncertainties"),
    }


def image_request(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    image_data = "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")
    body = {
        "model": "Qwen3-VL-8B-Instruct-GGUF",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": image_data}},
        ]}],
        "temperature": 0.1,
        "max_tokens": 512,
    }
    req = urllib.request.Request(API, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=600) as response:
        raw_response = response.read()
    response_obj = json.loads(raw_response)
    text = response_obj["choices"][0]["message"]["content"]
    return {"result": clean_result(text), "usage": response_obj.get("usage", {}),
            "response_id": response_obj.get("id"), "prompt_tokens": response_obj.get("usage", {}).get("prompt_tokens"),
            "completion_tokens": response_obj.get("usage", {}).get("completion_tokens")}


def restart_server() -> None:
    """Recycle llama-server between small batches to release accumulated CUDA allocations."""
    if PID_FILE.exists():
        try:
            os.kill(int(PID_FILE.read_text(encoding="ascii").strip()), signal.SIGTERM)
        except (ValueError, OSError, ProcessLookupError):
            pass
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            urllib.request.urlopen("http://127.0.0.1:18987/health", timeout=1).close()
            time.sleep(0.5)
        except (urllib.error.URLError, TimeoutError, OSError):
            break
    log = (DATA / "llama-server-managed.log").open("ab")
    proc = subprocess.Popen(
        [str(SERVER_EXE), "--model", str(MODEL_FILE), "--mmproj", str(MM_PROJ_FILE),
         "--ctx-size", "4096", "--gpu-layers", str(GPU_LAYERS), "--parallel", "1",
         "--threads", "8", "--image-min-tokens", "512", "--host", "127.0.0.1", "--port", "18987"],
        cwd=str(SERVER_EXE.parent), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    log.close()
    PID_FILE.write_text(str(proc.pid), encoding="ascii")
    deadline = time.time() + 90
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"llama-server exited while restarting, code={proc.returncode}")
        try:
            with urllib.request.urlopen("http://127.0.0.1:18987/health", timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(1)
    raise TimeoutError("llama-server health check timed out after restart")


def stop_server() -> None:
    if PID_FILE.exists():
        try:
            os.kill(int(PID_FILE.read_text(encoding="ascii").strip()), signal.SIGTERM)
        except (ValueError, OSError, ProcessLookupError):
            pass
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            urllib.request.urlopen("http://127.0.0.1:18987/health", timeout=1).close()
            time.sleep(0.5)
        except (urllib.error.URLError, TimeoutError, OSError):
            break
    PID_FILE.unlink(missing_ok=True)


def enrich_social_note_images(note: dict[str, Any]) -> list[dict[str, Any]]:
    """Opt-in bounded reuse of the existing local VLM pipeline for one XHS note."""
    note_id = str(note.get("note_id") or "")
    if not note_id:
        return []
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    if calibration.get("passed") is not True:
        raise RuntimeError("Calibration did not pass; refusing image enrichment")
    indexed = [row for row in read_jsonl(INDEX) if key_of(row)[0] == note_id][:20]
    if not indexed:
        return []
    existing: dict[tuple[str, int], dict[str, Any]] = {}
    for row in read_jsonl(OUT):
        if row.get("status") in {"ok", "partial"}:
            existing[key_of(row)] = row
    new_rows = [row for row in indexed if key_of(row) not in existing]
    started_server = False
    candidates: list[dict[str, Any]] = []
    if new_rows:
        try:
            with urllib.request.urlopen("http://127.0.0.1:18987/health", timeout=3) as response:
                if response.status != 200:
                    raise RuntimeError("local VLM health check failed")
        except (urllib.error.URLError, TimeoutError, OSError):
            restart_server()
            started_server = True
    try:
        for source in new_rows:
            image_path = ROOT / Path(str(source.get("local_path") or ""))
            if not image_path.is_file():
                continue
            payload = image_request(image_path)
            result = payload["result"]
            record = {
                "note_id": note_id, "image_index": int(source["image_index"]),
                "note_url": "", "image_id": str(source.get("image_id") or ""),
                "image_path": str(source.get("local_path") or ""),
                "image_sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                "model": MODEL, "prompt_version": PROMPT_VERSION,
                "review_status": "model_generated_unverified", "status": "ok" if any(
                    result.get(key) for key in ("title", "identifier", "main_content", "visible_links")
                ) else "partial", "model_output": result,
                "usage": payload.get("usage", {}), "processed_at": now(),
            }
            with OUT.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            existing[key_of(record)] = record
        from scripts.intelligence.canonicalize import extract_artifact_candidates
        for row in indexed:
            model_output = existing.get(key_of(row), {}).get("model_output")
            if not isinstance(model_output, dict):
                continue
            text = "\n".join(str(model_output.get(key) or "") for key in ("title", "identifier", "main_content"))
            links = model_output.get("visible_links") if isinstance(model_output.get("visible_links"), list) else []
            for candidate in extract_artifact_candidates(text, [str(link) for link in links]):
                candidate["mention"] = {"evidence_level": "image_extract", "origin": "image",
                                        "confidence": 0.35, "role": "referenced"}
                candidates.append(candidate)
        unique = {json.dumps(row, sort_keys=True, ensure_ascii=False): row for row in candidates}
        return [unique[key] for key in sorted(unique)]
    finally:
        if started_server:
            stop_server()


def main() -> int:
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    if calibration.get("passed") is not True:
        raise RuntimeError("Calibration did not pass; refusing to start batch")
    try:
        with urllib.request.urlopen("http://127.0.0.1:18987/health", timeout=10) as response:
            if response.status != 200:
                raise RuntimeError("Local llama-server health check failed")
    except urllib.error.URLError:
        restart_server()

    source_rows = read_jsonl(INDEX)
    direct_keys = {key_of(row) for row in read_jsonl(DIRECT)}
    by_key: dict[tuple[str, int], dict[str, Any]] = {}
    for row in source_rows:
        k = key_of(row)
        if k in by_key:
            raise RuntimeError(f"Duplicate source-index key: {k}")
        by_key[k] = row
    queue_rows = [row for k, row in by_key.items() if k not in direct_keys]
    queue_rows.sort(key=lambda r: (str(r["note_id"]), int(r["image_index"])))
    if len(by_key) != 1581 or len(direct_keys) != 127 or len(queue_rows) != 1454:
        raise RuntimeError(f"Unexpected queue counts: index={len(by_key)}, direct={len(direct_keys)}, pending={len(queue_rows)}")
    dump_jsonl_atomic(QUEUE, queue_rows)

    existing = read_jsonl(OUT)
    done: dict[tuple[str, int], dict[str, Any]] = {}
    for row in existing:
        k = key_of(row)
        if k not in by_key:
            raise RuntimeError(f"Output key is outside the source index: {k}")
        done[k] = row
    # Compact a previous interrupted append pass and discard duplicate events by keeping the latest row.
    dump_jsonl_atomic(OUT, list(done.values()))

    todo = [row for row in queue_rows if done.get(key_of(row), {}).get("status") not in ("ok", "partial")]
    total = len(queue_rows)
    print(f"queue={total} direct_excluded={len(direct_keys)} already_complete={total-len(todo)} remaining={len(todo)}", flush=True)
    for ordinal, source in enumerate(todo, 1):
        key = key_of(source)
        rel_path = str(source["local_path"])
        img = ROOT / Path(rel_path)
        record: dict[str, Any] = {
            "note_id": key[0], "image_index": key[1], "note_url": source.get("note_url", ""),
            "image_id": source.get("image_id", ""), "image_path": rel_path,
            "image_sha256": hashlib.sha256(img.read_bytes()).hexdigest() if img.is_file() else "",
            "image_width": source.get("width"), "image_height": source.get("height"),
            "model": MODEL, "model_repo": "Qwen/Qwen3-VL-8B-Instruct-GGUF",
            "llama_cpp_version": calibration.get("llama_cpp_version"),
            "runtime": calibration.get("runtime"), "prompt_version": PROMPT_VERSION,
            "review_status": "model_generated_unverified", "source_index_status": source.get("visual_review_status"),
            "processed_at": now(),
        }
        failure = ""
        result: dict[str, Any] | None = None
        for attempt in range(1, 4):
            try:
                if not img.is_file():
                    raise FileNotFoundError(rel_path)
                payload = image_request(img)
                result = payload["result"]
                record["usage"] = payload["usage"]
                record["model_response_id"] = payload["response_id"]
                record["model_output"] = result
                failure = ""
                break
            except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                failure = f"{type(exc).__name__}: {str(exc)[:350]}"
                if isinstance(exc, urllib.error.HTTPError) and exc.code >= 500:
                    try:
                        restart_server()
                    except Exception as restart_exc:
                        failure += f"; restart failed: {type(restart_exc).__name__}: {str(restart_exc)[:150]}"
                time.sleep(min(2 * attempt, 6))
        if failure:
            record.update({"status": "failed", "error": failure, "attempts": 3})
        else:
            has_material = bool(result and (result["title"] or result["identifier"] or result["main_content"] or result["visible_links"]))
            record["status"] = "ok" if has_material else "partial"
        # Append after each image so interruption loses at most an in-flight request.
        with OUT.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            f.flush()
            os.fsync(f.fileno())
        done[key] = record
        save_checkpoint(done, key)
        # ASCII-safe progress for Windows consoles with legacy encodings.
        print(json.dumps({"position": ordinal, "total_remaining_at_start": len(todo),
                          "absolute_done": total - sum(1 for r in queue_rows if key_of(r) not in done),
                          "key": {"note_id": key[0], "image_index": key[1]},
                          "status": record["status"], "title": result["title"][:100] if result else "",
                          "failure": failure[:180]}, ensure_ascii=True), flush=True)
        if ordinal % RESTART_EVERY == 0 and ordinal < len(todo):
            restart_server()
    # Deduplicate retry history and leave one final materialized row per key.
    dump_jsonl_atomic(OUT, list(done.values()))
    save_checkpoint(done, key_of(todo[-1]) if todo else None)
    print("BATCH_COMPLETE " + json.dumps({"records": len(done), "ok": sum(r.get("status") == "ok" for r in done.values()),
                                         "partial": sum(r.get("status") == "partial" for r in done.values()),
                                         "failed": sum(r.get("status") == "failed" for r in done.values())}), flush=True)
    stop_server()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FATAL {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise
