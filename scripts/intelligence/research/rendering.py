from __future__ import annotations

import json
from typing import Any


def render_brief_markdown(brief: dict[str, Any], evidence: list[dict[str, Any]]) -> str:
    refs, markers = _evidence_index(evidence)
    lines = [f"# {brief['question']}", "", "## Executive summary", "",
             _with_citations(str(brief.get("executive_summary") or "Evidence collection is ready; no summary was generated."),
                             brief.get("summary_evidence_ids", []), markers),
             "", "## What the sources actually show", ""]
    claims_by_id = {row["claim_id"]: row for row in brief.get("claims", [])}
    findings = [claims_by_id[item] for item in brief.get("key_findings", []) if item in claims_by_id]
    if not findings:
        findings = list(brief.get("claims", []))
    if findings:
        for claim in findings:
            label = str(claim.get("claim_type", "claim")).replace("_", " ").title()
            lines.append(f"- **{label}** — {_with_citations(claim['text'], claim.get('evidence_ids', []), markers)}")
    else:
        lines.append("- No claims were generated.")
    lines.extend(["", "## Key findings", ""])
    lines.extend(f"- {_with_citations(row['text'], row.get('evidence_ids', []), markers)}" for row in findings)
    lines.extend(["", "## Disagreements / uncertainty", ""])
    if brief.get("disagreements"):
        lines.extend(f"- {_with_citations(row['text'], row.get('evidence_ids', []), markers)}"
                     for row in brief["disagreements"])
    else:
        lines.append("No explicit disagreement was identified in this evidence packet.")
    lines.extend(["", "## Implications", "", "**Synthesis / interpretation**"])
    if brief.get("practical_implications"):
        lines.extend(f"- {_with_citations(row['text'], row.get('evidence_ids', []), markers)}"
                     for row in brief["practical_implications"])
    else:
        lines.append("- No practical implication was generated.")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in brief.get("limitations", []))
    if not brief.get("limitations"):
        lines.append("- The brief only reflects the bounded local evidence packet.")
    lines.extend(["", "## Open questions", ""])
    lines.extend(f"- {item}" for item in brief.get("open_questions", []))
    if not brief.get("open_questions"):
        lines.append("- None recorded.")
    lines.extend(["", "## Evidence", ""])
    for index, row in enumerate(refs, 1):
        label = f"E{index}"
        title = str(row.get("title") or row.get("locator", {}).get("value") or row["artifact_id"])
        date = f" ({row['published_at'][:10]})" if row.get("published_at") else ""
        url = f" — [{title}]({row['canonical_url']})" if row.get("canonical_url") else f" — {title}"
        lines.append(f"- **[{label}]**{url}{date} · `{row['artifact_id']}`")
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
        f"  session_id: {json.dumps(session['research_session_id'])}",
        f"  evidence_set_hash: {json.dumps(brief['evidence_set_hash'])}",
        "  ai_assisted: true",
        "---",
        "",
    ]
    lines = [*front, f"# {title}", "", "## Research question", "", session["question"],
             "", "## Executive summary", "",
             _with_citations(brief.get("executive_summary") or "", brief.get("summary_evidence_ids", []), markers),
             "", "## What the sources actually show", ""]
    claims = {row["claim_id"]: row for row in brief.get("claims", [])}
    findings = [claims[key] for key in brief.get("key_findings", []) if key in claims]
    if not findings:
        findings = list(brief.get("claims", []))
    for row in findings:
        kind = str(row.get("claim_type") or "fact").replace("_", " ").title()
        prefix = "**Synthesis / interpretation** — " if kind in {"Inference", "Interpretation"} else ""
        lines.append(f"- {prefix}{_with_citations(row['text'], row.get('evidence_ids', []), markers)}")
    lines.extend(["", "## Disagreements / uncertainty", ""])
    lines.extend(f"- {_with_citations(row['text'], row.get('evidence_ids', []), markers)}"
                 for row in brief.get("disagreements", []))
    if not brief.get("disagreements"):
        lines.append("No explicit disagreement was identified in the collected evidence.")
    lines.extend(["", "## Implications", "", "**Synthesis / interpretation**"])
    lines.extend(f"- {_with_citations(row['text'], row.get('evidence_ids', []), markers)}"
                 for row in brief.get("practical_implications", []))
    if not brief.get("practical_implications"):
        lines.append("- No practical implication was generated.")
    lines.extend(["", "## Open questions", ""])
    lines.extend(f"- {item}" for item in brief.get("open_questions", []))
    if not brief.get("open_questions"):
        lines.append("- None recorded.")
    lines.extend(["", "## References", ""])
    for index, row in enumerate(refs, 1):
        marker = f"e{index}"
        title = str(row.get("title") or row.get("locator", {}).get("value") or row["artifact_id"])
        date_text = f" ({row['published_at'][:10]})" if row.get("published_at") else ""
        canonical = row.get("canonical_url")
        linked_title = f"[{title}]({canonical})" if canonical else title
        lines.append(f"[^{marker}]: {linked_title}{date_text}. Artifact `{row['artifact_id']}`.")
    model = brief.get("model_provenance") or {}
    lines.extend(["", "## AI-assisted provenance", "",
                  f"This note was synthesized with `{model.get('provider') or 'provider not reported'}` / "
                  f"`{model.get('model') or 'model not reported'}` at temperature "
                  f"`{model.get('temperature') if model.get('temperature') is not None else 'not reported'}`. "
                  f"Evidence set `{brief['evidence_set_hash']}`. The synthesis is not itself a source.",
                  ""])
    return "\n".join(lines).rstrip() + "\n"


def _evidence_index(evidence: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    refs = sorted(evidence, key=lambda row: str(row["evidence_id"]))
    markers = {str(row["evidence_id"]): f"e{index}" for index, row in enumerate(refs, 1)}
    return refs, markers


def _with_citations(text: str, ids: list[str], markers: dict[str, str]) -> str:
    suffix = " ".join(f"[^{markers[item]}]" for item in ids if item in markers)
    return f"{text}{(' ' + suffix) if suffix else ''}"
