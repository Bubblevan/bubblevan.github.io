from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any

from .artifacts import materialize_artifact_candidates
from .canonicalize import canonicalize_url, extract_artifact_candidates, merge_candidates
from .models import new_observation, new_source


_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(xsec_token|cookie|authorization|session(?:_token)?|access_token|refresh_token|token)\s*[:=]\s*[^,\s;&]+"
)


def bridge_xhs(note: Mapping[str, Any], *, observed_at: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Convert an existing sanitized XHS reader result; never acquires pages."""
    if note.get("ok") is False:
        raise ValueError("cannot ingest an unsuccessful XHS reader result")
    note_id = str(note.get("note_id") or "").strip()
    note_url = _first_url(note.get("canonical_url"), note.get("url"), note.get("final_url"))
    if not note_id:
        note_id = _extract_note_id(note_url)
    if not note_id and not note_url:
        raise ValueError("XHS input requires note_id or a canonical note URL")

    author = note.get("author") if isinstance(note.get("author"), Mapping) else {}
    name = _safe_text(author.get("nickname")) or _safe_text(note.get("author_name")) or "tabris"
    author_id = _safe_text(author.get("user_id")) or _safe_text(note.get("author_id"))
    profile_url = _first_url(
        note.get("author_url"),
        author.get("profile_url"),
        f"https://www.xiaohongshu.com/user/profile/{author_id}" if author_id else "",
    )
    source_identity = f"xiaohongshu|{canonicalize_url(profile_url)}" if profile_url else f"xiaohongshu|curator|{name.casefold()}"
    retrieval = note.get("retrieval") if isinstance(note.get("retrieval"), Mapping) else {}
    retrieval_mode = _retrieval_mode(retrieval)
    source = new_source(
        identity=source_identity,
        source_type="curator",
        platform="xiaohongshu",
        name=name,
        canonical_url=profile_url,
        external_ids={"xiaohongshu_user_id": author_id} if author_id else {},
        topics=[],
        connector="xhs-reader",
        mode=retrieval_mode,
        status="active",
    )

    title = _safe_text(note.get("title"))
    desc = _safe_text(note.get("desc"))
    comment_text = _safe_text(note.get("comments_text"))
    tags_value = note.get("tags")
    tags = _string_list(tags_value)
    tag_text = "Tags: " + ", ".join(tags) if tags else ""
    combined_text = "\n\n".join(part for part in [title, desc, tag_text, comment_text] if part)
    if not combined_text:
        combined_text = _safe_text(note.get("combined_text"))

    raw_urls = [note_url]
    raw_urls.extend(_urls_in_text(combined_text))
    raw_urls.extend(_string_list(note.get("urls")))
    urls = sorted({canonicalize_url(value) for value in raw_urls if canonicalize_url(value)})
    canonical_note_url = canonicalize_url(note_url)
    target_urls = [value for value in urls if value != canonical_note_url]
    candidates = extract_artifact_candidates(combined_text, target_urls, exclude_urls=[canonical_note_url])
    images = note.get("images")
    explicit_candidates: list[Mapping[str, Any]] = []
    image_candidate_count = 0
    for candidate_list in (note.get("artifact_candidates"), note.get("image_artifact_candidates")):
        if isinstance(candidate_list, list):
            explicit_candidates.extend(item for item in candidate_list if isinstance(item, Mapping))
    if isinstance(images, list):
        for image in images:
            if isinstance(image, Mapping) and isinstance(image.get("artifact_candidates"), list):
                image_candidates = [item for item in image["artifact_candidates"] if isinstance(item, Mapping)]
                image_candidate_count += len(image_candidates)
                explicit_candidates.extend(image_candidates)
    candidates = merge_candidates([*candidates, *explicit_candidates])

    media = []
    if isinstance(images, list):
        for image in images:
            if not isinstance(image, Mapping):
                continue
            item: dict[str, Any] = {"kind": "image"}
            for input_key, output_key in (("url", "url"), ("preview_url", "preview_url"), ("image_id", "image_id")):
                safe_url = canonicalize_url(str(image.get(input_key) or "")) if "url" in input_key else _safe_text(image.get(input_key))
                if safe_url:
                    item[output_key] = safe_url
            for dimension in ("width", "height"):
                value = image.get(dimension)
                if isinstance(value, int) and not isinstance(value, bool):
                    item[dimension] = value
            if len(item) > 1:
                media.append(item)

    observation_key = (
        f"xiaohongshu|{note_id}"
        if note_id
        else "|".join(
            [
                f"source:{source['source_id']}",
                f"url:{canonical_note_url}",
                f"published:{str(note.get('published_at') or '')}",
                f"text:{combined_text}",
            ]
        )
    )
    obs = new_observation(
        identity=observation_key,
        source_id=source["source_id"],
        platform="xiaohongshu",
        platform_object_id=note_id or canonical_note_url,
        kind="post",
        title=title,
        text=combined_text,
        urls=urls,
        media=media,
        published_at=str(note.get("published_at") or "") or None,
        observed_at=observed_at,
        topics=tags,
        provenance={
            "retrieval_mode": retrieval_mode,
            "evidence_level": "image_extract" if image_candidate_count else "source_text",
            "source_url": canonical_note_url,
            "collector": "scripts.tools.xhs_note_reader",
        },
        artifact_candidates=candidates,
    )
    return source, obs


def ingest_xhs(
    note: Mapping[str, Any],
    store: Any,
    *,
    observed_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    source, observation = bridge_xhs(note, observed_at=observed_at)
    source = store.upsert_source(source)
    store.append_observation(observation)
    artifact_ids = materialize_artifact_candidates(observation, store)
    return source, observation, artifact_ids


def _retrieval_mode(retrieval: Mapping[str, Any]) -> str:
    if retrieval.get("browser_automation") or retrieval.get("mode") == "real_chrome":
        return "browser"
    if retrieval.get("mode") == "static_html":
        return "html"
    if retrieval.get("mode") in {"api", "rss"}:
        return str(retrieval["mode"])
    return "manual"


def _safe_text(value: object) -> str:
    text = str(value or "").strip()
    text = _URL_RE.sub(lambda match: canonicalize_url(match.group(0).rstrip(".,;:!?)]}")), text)
    text = _SECRET_ASSIGNMENT_RE.sub("[REDACTED]", text)
    return text


def _first_url(*values: object) -> str:
    for value in values:
        safe = canonicalize_url(str(value or ""))
        if safe:
            return safe
    return ""


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _safe_text(item))]


def _urls_in_text(value: str) -> list[str]:
    return [match.group(0).rstrip(".,;:!?)]}") for match in _URL_RE.finditer(value)]


def _extract_note_id(url: str) -> str:
    match = re.search(r"/(?:explore|discovery/item)/([A-Za-z0-9]+)", url)
    if match:
        return match.group(1)
    query_match = re.search(r"(?:[?&]note_id=)([A-Za-z0-9]+)", url)
    return query_match.group(1) if query_match else ""
