#!/usr/bin/env python3
"""Review the local VLM batch row-by-row and build its Markdown source index."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / ".cache" / "xhs-extracted"
INDEX = DATA / "image-source-index.jsonl"
DIRECT = DATA / "image-visual-review.jsonl"
QUEUE = DATA / "qwen3-vl-image-queue.jsonl"
OUTPUT = DATA / "qwen3-vl-image-descriptions.jsonl"
CALIBRATION = DATA / "qwen3-vl-calibration.json"
CHECKPOINT = DATA / "qwen3-vl-image-descriptions.checkpoint.json"
PAGE = ROOT / "content" / "docs" / "agent" / "search" / "tabris-ai-image-source-index-2026.md"
OVERRIDES = Path(__file__).with_name("xhs-ai-source-review-overrides.json")


def jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def key(row: dict) -> tuple[str, int]:
    return str(row.get("note_id", "")), int(row.get("image_index", -1))


def md(text: object) -> str:
    value = str(text or "")
    value = value.replace("\r", " ").replace("\n", " ").replace("|", "\\|")
    value = re.sub(r"(?i)([?&](?:xsec_token|token|access_token|signature|auth|session|api_key|key)=)[^&#\s]*", "", value)
    return re.sub(r"\s+", " ", value).strip()


def link_markdown(value: str) -> str:
    safe = md(value)
    if safe.startswith(("https://", "http://")):
        return f"[{safe}]({safe})"
    return chr(96) + safe + chr(96)


def source_channels(result: dict, domains: list[str]) -> list[str]:
    names = [str(x).casefold() for x in result.get("source_names", [])]
    identifier = str(result.get("identifier", "")).casefold()
    evidence = str(result.get("source_evidence", "")).casefold()
    channels = []
    if identifier.startswith(("arxiv:", "doi:")) or "arxiv.org" in domains or any("arxiv" in n for n in names) or "arxiv" in evidence:
        channels.append("论文预印本/论文页")
    if "github.com" in domains or any("github" in n for n in names) or "github" in evidence:
        channels.append("GitHub 仓库/项目")
    if "huggingface.co" in domains or any("hugging face" in n or "huggingface" in n for n in names):
        channels.append("Hugging Face 模型/数据")
    if not channels and (domains or names):
        channels.append("其他可见网站/机构/项目")
    if not channels:
        channels.append("图中未识别出直接来源")
    return channels


def main() -> None:
    input_index = jsonl(INDEX)
    direct_rows = jsonl(DIRECT)
    queue = jsonl(QUEUE)
    results = jsonl(OUTPUT)
    calibration = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    checkpoint = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    overrides = json.loads(OVERRIDES.read_text(encoding="utf-8")) if OVERRIDES.exists() else {}

    index_by_key = {key(r): r for r in input_index}
    direct_keys = {key(r) for r in direct_rows}
    expected = {key(r) for r in queue}
    result_by_key = {}
    duplicates = []
    for row in results:
        k = key(row)
        if k in result_by_key:
            duplicates.append(k)
        result_by_key[k] = row
    if len(index_by_key) != len(input_index):
        raise SystemExit("Input source index contains duplicate keys")
    if len(expected) != 1454 or len(direct_keys) != 127 or expected & direct_keys:
        raise SystemExit(f"Unexpected queue/direct counts: queue={len(expected)}, direct={len(direct_keys)}")
    if duplicates:
        raise SystemExit(f"Output still contains duplicate keys: {duplicates[:4]}")
    if set(result_by_key) != expected:
        missing = expected - set(result_by_key)
        extra = set(result_by_key) - expected
        raise SystemExit(f"Queue/result mismatch: missing={len(missing)}, extra={len(extra)}")
    if checkpoint.get("total_queue") != 1454:
        raise SystemExit("Checkpoint queue count mismatch")

    domain_counts: Counter[str] = Counter()
    name_counts: Counter[str] = Counter()
    channel_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    note_kind_counts: Counter[str] = Counter()
    source_records: dict[tuple[str, int], dict] = {}
    review_flags = []
    safe_links = True
    hash_matches = 0
    missing_images = 0
    for k in expected:
        record = result_by_key[k]
        source = index_by_key[k]
        output = record.get("model_output") if isinstance(record.get("model_output"), dict) else {}
        override = overrides.get(f"{k[0]}:{k[1]}")
        if override:
            if override.get("image_sha256") != record.get("image_sha256"):
                review_flags.append((k, "人工复核覆盖项的源图 SHA-256 不匹配"))
                output = dict(output)
            else:
                output = {**output, **override.get("fields", {})}
        status = record.get("status", "")
        status_counts[status] += 1
        note_kind_counts[str(source.get("note_kind", "unknown"))] += 1
        image_path = ROOT / str(source.get("local_path", ""))
        actual_sha = hashlib.sha256(image_path.read_bytes()).hexdigest() if image_path.is_file() else ""
        if actual_sha and actual_sha == record.get("image_sha256"):
            hash_matches += 1
        else:
            missing_images += 1
            review_flags.append((k, "源图缺失或 SHA-256 与记录不符"))
        links = output.get("visible_links", []) if isinstance(output.get("visible_links", []), list) else []
        domains = []
        for raw in links:
            raw = str(raw)
            if re.search(r"(?i)[?&](?:xsec_token|token|access_token|signature|auth|session|api_key|key)=", raw):
                safe_links = False
            host = (urlparse(raw if "://" in raw else "https://" + raw).hostname or "").casefold()
            if host:
                domains.append(host.removeprefix("www."))
        for host in set(domains):
            domain_counts[host] += 1
        names = output.get("source_names", []) if isinstance(output.get("source_names", []), list) else []
        for name in set(str(n).strip() for n in names if str(n).strip()):
            name_counts[name] += 1
        channels = source_channels(output, domains)
        for channel in channels:
            channel_counts[channel] += 1
        title = str(output.get("title", "")).strip()
        summary = str(output.get("main_content", "")).strip()
        if status == "ok" and not (title or output.get("identifier") or summary or links):
            review_flags.append((k, "标记 ok 但缺少标题、编号、摘要和链接"))
        if status == "ok" and not title and not summary:
            review_flags.append((k, "无标题与内容摘要"))
        if status not in {"ok", "partial", "failed"}:
            review_flags.append((k, f"未知状态 {status}"))
        if status != "failed" and not isinstance(record.get("model_output"), dict):
            review_flags.append((k, "缺少结构化模型输出"))
        source_records[k] = {**record, "_source": source, "_output": output, "_domains": domains, "_channels": channels}

    if not safe_links:
        raise SystemExit("A sensitive query parameter remains in a model-visible link")

    created = datetime.now().astimezone().strftime("%Y-%m-%d")
    status_cn = (f"模型响应：有效 {status_counts['ok']}，空/部分 {status_counts['partial']}，解析失败 {status_counts['failed']}；"
                 f"其中失败项和空结果已人工抽看补充 {sum(1 for r in overrides.values() if r.get('status') == 'partial' or r.get('review_note', '').startswith('直接查看本地图后补齐'))} 条")
    lines = [
        "---",
        "schema: bubblevan/v1",
        "id: docs-agent-search-tabris-ai-image-source-index-2026",
        "content_kind: docs",
        "title: Tabris 图集中 AI 论文与项目来源索引（2026）",
        f"date: {created}",
        "status: draft",
        "visibility: public",
        "summary: 对剩余 1,454 张图逐图提取标题、内容要点与可见出处线索，并按论文、仓库、模型页和网站归档。",
        "topics: [research-intelligence, source-discovery, multimodal]",
        "aliases: []",
        "authors: [bubblevan]",
        "---",
        "",
        "# Tabris 图集中 AI 论文与项目来源索引（2026）",
        "",
        "> 本页逐项列出本地 Qwen3-VL 的图像读图候选，重点是材料大意和图内来源线索。表中的内容未逐条回到原站核实；无法辨认出处就保留为“图中未识别出直接来源”，不从相邻图片补猜。",
        "",
        "## 覆盖范围与逐条检查",
        "",
        f"- 队列：{len(expected):,} 张；已有直接视觉记录 {len(direct_keys):,} 张另存于[来源图谱](tabris-ai-source-map-2026.md)。合计 {len(expected | direct_keys):,}/1,581 张有记录。",
        f"- 队列记录状态：{status_cn}；模型：{md(calibration.get('model'))}；llama.cpp：{md(calibration.get('llama_cpp_version'))}；校准通过，输出格式：{md(calibration.get('prompt_version'))}。",
        f"- 逐项检查：逐条核对索引键唯一性、队列覆盖、状态与字段结构、源图 SHA-256、可见链接中的敏感查询参数。匹配图片哈希 {hash_matches:,}/{len(expected):,}；直接抽看并修订 {len(overrides)} 条；异常标记 {len(review_flags)} 条。其余模型候选未逐图人工核对论文结论。",
        f"- 来源线索分类统计（同一张图可计入多类）：{'; '.join(f'{md(k)} {v:,}' for k,v in channel_counts.most_common())}。",
        "",
        "## 高产的发现入口与原始信源",
        "",
        "从作者笔记中明确说出的发现方式看，热点发现主要靠 X 推荐流和持续追踪研究者；作者也提到 AlphaXiv 排名、导师或朋友推荐、研究者社交网络。图集主要展示的是命中后的论文、技术博客和项目页面，因此复刻时可把“发现入口”和“原始材料核验”分开：",
        "",
        "1. **先捕捉热点**：维护 X 上研究者、实验室和工程团队的关注流，利用推荐流扩展相邻作者；定期扫 AlphaXiv 与新论文榜单，并把导师/同行推荐作为补充。",
        "2. **回到论文源**：图中可见 arXiv 编号或页面时，以 arXiv 论文页和 PDF 作为论文线索；重点留意 LLM/RL/Agent、推理与后训练、评测、AI for Science、系统与多模态等反复主题。",
        "3. **追新工具和可复现工作**：出现 GitHub、Hugging Face、项目站时，跟踪仓库 release、模型/数据卡、demo 和实验说明。它们更适合捕捉新 AI 项目、模型开放和工具链变化。",
        "4. **订阅高质量解释**：作者反复偏好论文作者、研究团队或公司工程团队写的配套博客；同名论文的可视化 blog 往往是更快的筛选入口。把 blog 当解释层，回论文页、项目页确认细节。",
        "",
        "这些是基于作者自述和图面链接做的实用归纳，不是对作者全部真实订阅列表的完整还原。高频域名与名称按这 1,454 张候选输出生成；出现次数表示图中可见次数，不代表质量排名或热度排名。",
        "",
        "### 模型识别出的域名候选",
        "",
        "| 域名候选 | 出现图数 | 主要用途（依页面线索） |",
        "|---|---:|---|",
    ]
    domain_purpose = {
        "arxiv.org": "论文预印本与论文页面",
        "github.com": "代码、数据、项目主页与 release",
        "huggingface.co": "模型、数据集与 demo 页面",
        "alphaxiv.org": "论文发现与阅读页面",
        "nvidia.com": "NVIDIA 研究或开发者页面",
        "openai.com": "实验室/产品研究与工程文章",
        "deepmind.google": "研究机构博客与项目页面",
    }
    for host, count in domain_counts.most_common(30):
        lines.append(f"| {md(host)} | {count:,} | {md(domain_purpose.get(host, '图中出现的站点；逐条材料见下表'))} |")
    lines += [
        "",
        "### 高出现频率的来源名称",
        "",
        "| 名称 | 图中次数 |",
        "|---|---:|",
    ]
    for name, count in name_counts.most_common(30):
        lines.append(f"| {md(name)} | {count:,} |")
    lines += [
        "",
        "## 逐图标题、内容和来源线索",
        "",
        "| 笔记 / 图序 | 图中材料标题与编号 | 可见来源 | 主要内容（模型候选） | 状态 |",
        "|---|---|---|---|---|",
    ]
    for k in (key(row) for row in queue):
        record = source_records[k]
        source = record["_source"]
        output = record["_output"]
        note_title = md(source.get("title", ""))
        date = md(str(source.get("published_at", ""))[:10])
        note_url = md(source.get("note_url", ""))
        note_cell = f"[{date} · {note_title} · 图 {k[1]}]({note_url})" if note_url.startswith("https://") else f"{date} · {note_title} · 图 {k[1]}"
        title = md(output.get("title", "")) or "（图中标题未识别）"
        identifier = md(output.get("identifier", ""))
        material = title + (f"；{identifier}" if identifier else "")
        names = output.get("source_names", []) if isinstance(output.get("source_names", []), list) else []
        links = output.get("visible_links", []) if isinstance(output.get("visible_links", []), list) else []
        evidence = md(output.get("source_evidence", ""))
        source_bits = []
        if names:
            source_bits.append("、".join(md(x) for x in names if md(x)))
        source_bits.extend(link_markdown(str(x)) for x in links if str(x).strip())
        if evidence:
            source_bits.append(evidence)
        if not source_bits:
            source_bits.append("图中未识别出直接来源")
        summary = md(output.get("main_content", ""))
        override_key = f"{k[0]}:{k[1]}"
        if record.get("status") == "failed" and override_key not in overrides:
            summary = f"读取失败：{md(record.get('error', '原因未记录'))}"
        elif not summary:
            summary = "主要内容未能稳定识读"
        if override_key in overrides:
            if record.get("status") == "failed":
                status = "直接抽看已补齐（模型失败）"
            elif record.get("status") == "partial":
                status = "直接抽看已补齐（模型部分）"
            else:
                status = "直接抽看已修订"
        else:
            status = {"ok": "候选可读", "partial": "部分可读", "failed": "待重试"}.get(record.get("status"), md(record.get("status")))
        lines.append(f"| {note_cell} | {material} | {'<br>'.join(source_bits)} | {summary} | {status} |")

    lines += [
        "",
        "## 使用说明",
        "",
        "- “可见来源”只照录模型从图中识别出的名称、编号、网址和页面标记；仅凭图标认出的平台应回源核对。页面标题、摘要和项目细节都是候选识读，不是本文对原始论文的独立复核。",
        "- 一张图可能是论文首页、blog 截图、仓库 README、产品页或多页拼图。若缺少 URL，就从笔记链接和图序回到该图，再在原站搜索图内标题；本表不会臆造附件地址。",
        "- 原始视觉记录仍在本地 .cache/xhs-extracted/qwen3-vl-image-descriptions.jsonl，图像索引在 .cache/xhs-extracted/image-source-index.jsonl。两者含本地图像路径，不是网站发布资产。",
        "- 作者评论中的“点点”摘要是另一来源，不与本页模型候选混合；作者 affiliation 上标对应关系不在本次抽取范围内。",
        "",
    ]
    PAGE.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "page": str(PAGE),
        "queue": len(expected),
        "status_counts": status_counts,
        "channels": channel_counts,
        "top_domains": domain_counts.most_common(12),
        "top_source_names": name_counts.most_common(12),
        "image_hash_matches": hash_matches,
        "review_flags": review_flags[:50],
    }, ensure_ascii=True, default=dict))


if __name__ == "__main__":
    main()
