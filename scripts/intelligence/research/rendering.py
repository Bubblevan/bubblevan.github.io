from __future__ import annotations

import json
import re
from typing import Any

from .quality import curator_attribution, safe_public_url


def render_brief_markdown(brief: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    refs, markers = _evidence_index(evidence)
    lines = [f"# {brief['question']}", "", "## Executive summary", "",
             _with_citations(str(brief.get("executive_summary") or "Evidence collection is ready; no summary was generated."),
                             brief.get("summary_evidence_ids", []), markers),
             "", "## What the sources actually show", ""]
    claims = list(brief.get("claims", []))
    facts = [row for row in claims if row.get("claim_type") == "fact"]
    lines.extend(_claim_review_lines(facts, markers, evidence))
    if not facts:
        lines.append("- No factual claims were generated.")
    interpretations = [row for row in claims if row.get("claim_type") in {"inference", "interpretation"}]
    if interpretations or brief.get("practical_implications"):
        lines.extend(["", "## Working interpretation", ""])
        lines.extend(_claim_review_lines(interpretations, markers, evidence))
        lines.extend(f"- {_with_citations(row['text'], row.get('evidence_ids', []), markers)}"
                     for row in brief.get("practical_implications", []))
    if brief.get("disagreements") or brief.get("limitations"):
        lines.extend(["", "## Disagreements and limitations", ""])
        lines.extend(f"- {_with_citations(row['text'], row.get('evidence_ids', []), markers)}"
                     for row in brief.get("disagreements", []))
        lines.extend(f"- {item}" for item in brief.get("limitations", []))
    if brief.get("open_questions") or any(row.get("claim_type") == "open_question" for row in claims):
        lines.extend(["", "## Open questions", ""])
        lines.extend(f"- {item}" for item in brief.get("open_questions", []))
        lines.extend(f"- {_with_citations(row['text'], row.get('evidence_ids', []), markers)}"
                     for row in claims if row.get("claim_type") == "open_question")
    lines.append("## Evidence and claim links")
    for index, row in enumerate(refs, 1):
        label = f"E{index}"
        title = str(row.get("title") or row.get("locator", {}).get("value") or row["artifact_id"])
        date = f" ({row['published_at'][:10]})" if row.get("published_at") else ""
        url = safe_public_url(row.get("canonical_url"))
        linked = f"[{title}]({url})" if url else title
        detail = f" · {row.get('source_name') or 'source not named'} · {row.get('evidence_kind') or 'metadata'}"
        lines.append(f"- **[{label}]** — {linked}{date}{detail} · Evidence `{row['evidence_id']}`")
    lines.extend(["", f"Evidence set: `{brief['evidence_set_hash']}`",
                  f"Quality: {brief['metrics']['supported_fact_count']}/{brief['metrics']['fact_claim_count']} supported facts; "
                  f"{brief['metrics']['unsupported_fact_count']} unsupported facts; "
                  f"{brief['metrics']['broken_citation_count']} broken citations."])
    return "\n".join(lines).rstrip() + "\n"


def render_promotion_markdown(session: dict[str, Any], brief: dict[str, Any], evidence: list[dict[str, Any]],
                              *, target: str, title: str | None, topics: list[str]) -> str:
    refs, markers = _evidence_index(evidence)
    title = str(title or session["question"]).strip().replace("\n", " ")
    date = str(session["created_at"])[:10]
    content_kind = "papers" if target.startswith("content/papers/") else "blog" if target.startswith("content/blog/") else "docs"
    front = [
        "---",
        "schema: bubblevan/v1",
        f"content_kind: {content_kind}",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f"date: {date}",
        "topics: " + json.dumps(list(dict.fromkeys(topics)), ensure_ascii=False),
        "research_intelligence:",
        f"  evidence_set_hash: {json.dumps(brief['evidence_set_hash'])}",
        "  ai_assisted: true",
        "---",
        "",
    ]
    lines = [*front, f"# {title}", "", "## 我在回答什么问题", "", session["question"],
             "", "## 一句话结论", "",
             _with_citations(brief.get("executive_summary") or "", brief.get("summary_evidence_ids", []), markers)]
    claims = list(brief.get("claims", []))
    facts = [row for row in claims if row.get("claim_type") == "fact"]
    attributed_curator = [row for row in facts if curator_attribution(str(row.get("text") or ""))]
    source_facts = [row for row in facts if row not in attributed_curator]
    if source_facts:
        lines.extend(["", "## 原始论文真正报告了什么", ""])
        lines.extend(f"- {_with_citations(row['text'], row.get('evidence_ids', []), markers)}" for row in source_facts)
    if attributed_curator:
        lines.extend(["", "## 社区 / curator 如何解释这些工作", ""])
        lines.extend(f"- {_with_citations(row['text'], row.get('evidence_ids', []), markers)}" for row in attributed_curator)
    comparison_claims = [row for row in facts
                         if re.search(r"\b(?:differ|versus|compared?)\b|区别|差异",
                                      str(row.get("text") or ""), re.IGNORECASE)]
    if comparison_claims:
        lines.extend(["", "## 方法之间的差异", ""])
        lines.extend(f"- {_with_citations(row['text'], row.get('evidence_ids', []), markers)}"
                     for row in comparison_claims)
    if brief.get("disagreements"):
        lines.extend(["", "## Disagreements", ""])
        lines.extend(f"- {_with_citations(row['text'], row.get('evidence_ids', []), markers)}"
                     for row in brief["disagreements"])
    uncertainty = [row for row in claims if row.get("claim_type") == "fact"
                   and (row.get("confidence") != "supported" or not row.get("evidence_ids"))]
    if uncertainty or brief.get("limitations"):
        lines.extend(["", "## 哪些判断目前证据不足", ""])
        lines.extend(f"- {row['text']}" for row in uncertainty)
        lines.extend(f"- {item}" for item in brief.get("limitations", []))
    interpretations = [row for row in claims if row.get("claim_type") in {"inference", "interpretation"}]
    if interpretations or brief.get("practical_implications"):
        lines.extend(["", "## 我的 working interpretation", ""])
        lines.extend(f"- {_with_citations(row['text'], row.get('evidence_ids', []), markers)}" for row in interpretations)
        lines.extend(f"- {_with_citations(row['text'], row.get('evidence_ids', []), markers)}"
                     for row in brief.get("practical_implications", []))
    if brief.get("open_questions"):
        lines.extend(["", "## 接下来值得验证什么", ""])
        lines.extend(f"- {item}" for item in brief["open_questions"])
    lines.extend(["", "## Sources", ""])
    for index, row in enumerate(refs, 1):
        marker = f"e{index}"
        title = str(row.get("title") or row.get("locator", {}).get("value") or row["artifact_id"])
        date_text = f" ({row['published_at'][:10]})" if row.get("published_at") else ""
        canonical = safe_public_url(row.get("canonical_url"))
        linked_title = f"[{title}]({canonical})" if canonical else title
        lines.append(f"[^{marker}]: {linked_title}{date_text}.")
    model = brief.get("model_provenance") or {}
    lines.extend(["", "## AI-assisted provenance", "",
                  f"This note was synthesized with `{model.get('provider') or 'provider not reported'}` / "
                  f"`{model.get('model') or 'model not reported'}` at temperature "
                  f"`{model.get('temperature') if model.get('temperature') is not None else 'not reported'}`. "
                  f"Evidence set `{brief['evidence_set_hash']}`. The synthesis is not itself a source.",
                  ""])
    return "\n".join(lines).rstrip() + "\n"


def _claim_review_lines(claims: list[dict[str, Any]], markers: dict[str, str],
                        evidence: list[dict[str, Any]]) -> list[str]:
    evidence_by_id = {str(row["evidence_id"]): row for row in evidence}
    lines = []
    for row in claims:
        kind = str(row.get("claim_type", "claim")).replace("_", " ").title()
        lines.append(f"- **{kind}** — {_with_citations(row['text'], row.get('evidence_ids', []), markers)}")
        for evidence_id in row.get("evidence_ids", []):
            ref = evidence_by_id.get(str(evidence_id))
            if not ref:
                continue
            lines.append(f"  - `{evidence_id}` — {ref.get('title') or 'Untitled'} · "
                         f"{ref.get('source_name') or 'source not named'} · {ref.get('evidence_kind') or 'metadata'}")
    return lines


def _evidence_index(evidence: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    refs = sorted(evidence, key=lambda row: str(row["evidence_id"]))
    markers = {str(row["evidence_id"]): f"e{index}" for index, row in enumerate(refs, 1)}
    return refs, markers


def _with_citations(text: str, ids: list[str], markers: dict[str, str]) -> str:
    suffix = " ".join(f"[^{markers[item]}]" for item in ids if item in markers)
    return f"{text}{(' ' + suffix) if suffix else ''}"
