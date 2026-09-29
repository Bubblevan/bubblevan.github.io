from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from .canonicalize import canonicalize_url, extract_artifact_candidates, merge_candidates
from .models import new_observation, new_source
from .social.zhihu import canonical_zhihu_url
from .connectors.privacy import redact_private_text


_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)
_ANSWER_RE = re.compile(r"/question/(\d+)/answer/(\d+)/?$")
_MEMBER_RE = re.compile(r"/people/([^/]+)/?$")


def bridge_zhihu(answer: Mapping[str, Any], *, observed_at: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    canonical = canonical_zhihu_url(str(answer.get("canonical_url") or answer.get("url") or ""))
    match = _ANSWER_RE.search(canonical)
    question_id = str(answer.get("question_id") or (match.group(1) if match else ""))
    answer_id = str(answer.get("answer_id") or (match.group(2) if match else ""))
    title = _safe_text(answer.get("question_title"))
    body = _safe_text(answer.get("body"))
    if not question_id or not answer_id or not canonical or not title or not body:
        raise ValueError("Zhihu answer is missing required public fields")
    author_url = str(answer.get("author_url") or "")
    member = _MEMBER_RE.search(author_url)
    member_id = str(answer.get("author_id") or (member.group(1) if member else ""))
    author_name = _safe_text(answer.get("author_name"))
    source_identity = f"zhihu|member|{member_id.casefold()}" if member_id else f"zhihu|answer|{answer_id}"
    profile_url = f"https://www.zhihu.com/people/{member_id}" if member_id else ""
    source = new_source(
        identity=source_identity, source_type="author" if member_id else "curator",
        platform="zhihu", name=author_name or "Zhihu public author",
        canonical_url=profile_url, external_ids={"zhihu_member_id": member_id} if member_id else {},
        topics=[], connector="browser-assisted", mode="browser",
        operations={"acquisition_mode": "interactive"}, status="active",
    )
    explicit_urls = set()
    for raw in _URL_RE.findall(body):
        safe = canonicalize_url(raw.rstrip(".,;:!?)]}"))
        if safe and safe != canonical:
            explicit_urls.add(safe)
    for raw in answer.get("links", []) if isinstance(answer.get("links"), list) else []:
        safe = canonicalize_url(str(raw))
        if safe and safe != canonical:
            explicit_urls.add(safe)
    candidates = merge_candidates([
        *extract_artifact_candidates(body, exclude_urls=[canonical]),
        *extract_artifact_candidates("", sorted(explicit_urls), exclude_urls=[canonical]),
    ])
    candidates.append({
        "artifact_type": "discussion", "title": title, "canonical_url": canonical,
        "identifiers": {"zhihu_question_id": question_id, "zhihu_answer_id": answer_id},
        "authors": [author_name] if author_name else [], "organizations": [],
        "summary": body[:4000], "topics": [],
        "published_at": _safe_text(answer.get("created_at")) or None,
        "mention": {"evidence_level": "source_text", "origin": "social_object",
                    "confidence": 1.0, "role": "primary"},
    })
    source_url = canonical
    observation = new_observation(
        identity=f"zhihu|answer|{answer_id}", source_id=source["source_id"], platform="zhihu",
        platform_object_id=answer_id, kind="discussion", title=title,
        text=body, urls=sorted({canonical, *explicit_urls}), media=[],
        published_at=_safe_text(answer.get("created_at")) or None,
        observed_at=observed_at, topics=[], native_tags=[], authors=[author_name] if author_name else [],
        metadata={"question_id": question_id, "author_public_id": member_id,
                  "created_at": _safe_text(answer.get("created_at")),
                  "updated_at": _safe_text(answer.get("updated_at"))},
        provenance={"retrieval_mode": "browser_assisted", "evidence_level": "rendered_page",
                    "source_url": source_url, "collector": "chrome-use"},
        artifact_candidates=candidates,
    )
    return source, observation


def _safe_text(value: object) -> str:
    text = redact_private_text(str(value or "")).strip()
    text = _URL_RE.sub(lambda match: canonicalize_url(match.group(0).rstrip(".,;:!?)]}")), text)
    return text
