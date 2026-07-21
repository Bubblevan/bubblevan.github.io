from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
import re


URL_RE = re.compile(r"https?://[^\s<>()\"']+")
EVENT_RE = re.compile(r"(星期|周[一二三四五六日天]|今天|明天|后天|\d{1,2}[点:：]\d{0,2}|日程|抛光|预约|开会|deadline)", re.I)
TASK_RE = re.compile(r"(再一次|研究|排查|记得|待办|todo|TODO|提醒|follow.?up|准备)", re.I)
PROJECT_RE = re.compile(r"(项目日志|project log|项目复盘|stablepay|pkb)", re.I)
XHS_RE = re.compile(r"(小红书|xhslink\.com)", re.I)


@dataclass
class ImportResult:
    output_path: Path
    count: int


def import_wechat_file(
    root: Path,
    file_path: Path,
    adapter: str = "hermes",
    source_channel: str = "wechat",
    topics: list[str] | None = None,
    project_hint: str = "",
    out_path: Path | None = None,
) -> ImportResult:
    root = root.resolve()
    file_path = file_path if file_path.is_absolute() else root / file_path
    text = file_path.read_text(encoding="utf-8-sig")
    records = parse_wechat_text(
        text=text,
        source_agent=adapter,
        source_channel=source_channel,
        topics=topics or [],
        project_hint=project_hint,
    )
    if out_path is None:
        now = datetime.now().astimezone()
        safe_name = f"{now:%Y-%m-%dT%H-%M-%S}-wechat-import.json"
        out_path = root / "inbox" / "drop" / adapter / safe_name
    elif not out_path.is_absolute():
        out_path = root / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ImportResult(output_path=out_path, count=len(records))


def parse_wechat_text(
    text: str,
    source_agent: str,
    source_channel: str,
    topics: list[str],
    project_hint: str,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for index, raw_line in enumerate(split_lines(text), start=1):
        line = raw_line.strip()
        if not line:
            continue
        urls = [clean_url(match) for match in URL_RE.findall(line)]
        without_urls = URL_RE.sub("", line).strip()
        type_hint = classify_line(line, has_url=bool(urls))
        record_project = project_hint
        if type_hint == "project_log" and not record_project:
            record_project = infer_project(line)
        records.append(
            {
                "type_hint": type_hint,
                "text": summarize_line(without_urls or line),
                "urls": urls,
                "topics": infer_topics(line, topics),
                "project_hint": record_project,
                "visibility": "private",
                "source_agent": source_agent,
                "source_platform": "windows",
                "source_channel": source_channel,
                "source_message_id": f"wechat-import-{index:04d}",
                "raw": {"original_text": line},
            }
        )
    return records


def split_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw.strip()
        if line in {"{", "}"}:
            continue
        lines.append(line)
    return lines


def classify_line(line: str, has_url: bool) -> str:
    if PROJECT_RE.search(line) and not has_url:
        return "project_log"
    if EVENT_RE.search(line) and not has_url:
        return "event"
    if TASK_RE.search(line) and not has_url:
        return "task"
    if has_url:
        return "bookmark" if XHS_RE.search(line) else "link"
    return "note"


def infer_topics(line: str, defaults: list[str]) -> list[str]:
    topics = {topic.strip("# ") for topic in defaults if topic.strip("# ")}
    lower = line.lower()
    if "agent" in lower or "llm" in lower:
        topics.add("agent")
    if "icml" in lower or "科研" in line:
        topics.add("research")
    if "简历" in line or "实习" in line:
        topics.add("career")
    if "小红书" in line or "xhslink.com" in lower:
        topics.add("xhs")
    if "zhihu.com" in lower or "知乎" in line:
        topics.add("zhihu")
    return sorted(topics)


def infer_project(line: str) -> str:
    lower = line.lower()
    if "stablepay" in lower:
        return "stablepay"
    if "pkb" in lower:
        return "pkb"
    return ""


def summarize_line(line: str) -> str:
    value = re.sub(r"\s+", " ", line).strip()
    return value[:240]


def clean_url(url: str) -> str:
    return url.rstrip("，。,.、~")

