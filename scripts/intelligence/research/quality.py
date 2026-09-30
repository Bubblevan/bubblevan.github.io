from __future__ import annotations

from collections import defaultdict
import ipaddress
import re
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit


FIRST_PARTY_PAPER_HOSTS = {
    "arxiv.org", "openreview.net", "aclanthology.org", "proceedings.mlr.press",
    "proceedings.neurips.cc", "papers.neurips.cc", "jmlr.org", "doi.org",
    "dl.acm.org", "ieeexplore.ieee.org", "nature.com", "sciencedirect.com",
    "link.springer.com", "springer.com",
}
FIRST_PARTY_BLOG_HOSTS = {
    "openai.com", "anthropic.com", "deepmind.google", "blog.google", "ai.google",
    "huggingface.co", "bair.berkeley.edu",
}
CURATOR_HOSTS = {
    "aihot.news", "simonwillison.net", "openalex.org", "huggingface.co",
    "zhihu.com", "xiaohongshu.com", "substack.com",
}
DISCUSSION_HOSTS = {"zhihu.com", "xiaohongshu.com", "reddit.com", "news.ycombinator.com"}

_SYNTHETIC_MARKER = re.compile(
    r"(?:^|[\s/:|])(?:fixture|test-reviewer|unit-test-only)(?:$|[\s/:|])|"
    r"(?:^|[\s/:|])synthetic[-_ ](?:artifact|fixture|record|test)(?:$|[\s/:|])|"
    r"example\.(?:com|test|org|net)\b",
    re.IGNORECASE,
)
_SUBSTANTIVE_EVIDENCE_TYPES = {
    "observation_text", "paper_full_text", "paperqa_full_text", "pdf_full_text", "explicit_first_party_text",
}
_METADATA_EVIDENCE_TYPES = {
    "explicit_provider_metadata", "exact_provider_metadata", "citation_count",
    "graph_relation", "provider_metadata",
}
_CURATOR_ATTRIBUTION = re.compile(
    r"(?:AIHOT|XHS|小红书|知乎|Simon\s+Willison|curator|博主|编辑|摘要)"
    r"[^。！？.!?]{0,40}(?:认为|称|声称|指出|写道|解释|报道|says|said|claims|claimed|argues|argued|reports|reported)",
    re.IGNORECASE,
)
_UNSAFE_PREVIEW_PATTERNS = {
    "signed_social_token": re.compile(r"xsec_token\s*=", re.IGNORECASE),
    "signature": re.compile(r"\bsignature\s*=", re.IGNORECASE),
    "auth_material": re.compile(r"\bauthorization\b|\bauth\s*=", re.IGNORECASE),
    "session_material": re.compile(r"\bsession\b", re.IGNORECASE),
    "localhost": re.compile(r"\blocalhost\b|\b127\.0\.0\.1\b|\[::1\]", re.IGNORECASE),
    "file_url": re.compile(r"file://", re.IGNORECASE),
    "windows_path": re.compile(r"\b[A-Z]:\\", re.IGNORECASE),
    "unix_mount_path": re.compile(r"/mnt/", re.IGNORECASE),
    "private_research_path": re.compile(r"data[\\/]intelligence[\\/]private", re.IGNORECASE),
}


def safe_public_url(value: str | None) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = urlsplit(raw)
        if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
            return None
        host = parsed.hostname.encode("idna").decode("ascii").casefold()
        if host == "localhost" or host.endswith(".localhost"):
            return None
        try:
            if ipaddress.ip_address(host).is_private or ipaddress.ip_address(host).is_loopback:
                return None
        except ValueError:
            pass
        path = parsed.path
        if _SYNTHETIC_MARKER.search(host + path):
            return None
        port = f":{parsed.port}" if parsed.port and parsed.port not in {80, 443} else ""
        return urlunsplit((parsed.scheme.casefold(), host + port, path, "", ""))
    except (UnicodeError, ValueError):
        return None


def _host_matches(host: str, domains: set[str]) -> bool:
    normalized = str(host or "").casefold().rstrip(".")
    return any(normalized == domain or normalized.endswith("." + domain) for domain in domains)


def classify_artifact(artifact: Mapping[str, Any], sources: Mapping[str, Mapping[str, Any]]) -> str:
    artifact_type = str(artifact.get("artifact_type") or "other").casefold()
    url = str(artifact.get("canonical_url") or "")
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").casefold()
        path = parsed.path.casefold()
    except ValueError:
        host, path = "", ""
    source_rows = [sources[item] for item in artifact.get("source_ids", []) if item in sources]
    source_types = {str(row.get("source_type") or "").casefold() for row in source_rows}
    if artifact_type in {"discussion", "social_post"} or _host_matches(host, DISCUSSION_HOSTS):
        return "discussion"
    if _host_matches(host, CURATOR_HOSTS) and not (host == "huggingface.co" and path.startswith("/blog/")):
        return "curator"
    if artifact_type == "paper" and _host_matches(host, FIRST_PARTY_PAPER_HOSTS):
        return "first_party"
    if artifact_type == "repository" and _host_matches(host, {"github.com"}):
        return "first_party"
    if artifact_type in {"blog", "technical_report"} and _host_matches(host, FIRST_PARTY_BLOG_HOSTS):
        return "first_party"
    if "community" in source_types:
        return "discussion"
    if "curator" in source_types:
        return "curator"
    if source_types.intersection({"author", "lab", "publication", "repository"}):
        return "first_party"
    return "metadata"


def evidence_kind(ref: Mapping[str, Any], artifact: Mapping[str, Any],
                  sources: Mapping[str, Mapping[str, Any]]) -> str:
    if str(ref.get("evidence_type") or "") in _METADATA_EVIDENCE_TYPES:
        return "metadata"
    return classify_artifact(artifact, sources)


def classify_evidence(refs: list[dict[str, Any]], artifact_rows: Mapping[str, Mapping[str, Any]],
                      sources: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    refs_by_kind: dict[str, int] = defaultdict(int)
    artifacts_by_kind: dict[str, set[str]] = defaultdict(set)
    substantive_first_party: set[str] = set()
    substantive_by_kind: dict[str, set[str]] = defaultdict(set)
    for ref in refs:
        artifact_id = str(ref.get("artifact_id") or "")
        artifact = artifact_rows.get(artifact_id, {})
        kind = evidence_kind(ref, artifact, sources)
        refs_by_kind[kind] += 1
        artifacts_by_kind[kind].add(artifact_id)
        is_substantive = (str(ref.get("evidence_type") or "") in _SUBSTANTIVE_EVIDENCE_TYPES
                          and bool(str(ref.get("text") or "").strip()))
        if is_substantive:
            substantive_by_kind[kind].add(artifact_id)
        if kind == "first_party" and is_substantive:
            substantive_first_party.add(artifact_id)
    metadata_ref_count = refs_by_kind.get("metadata", 0)
    evidence_count = len(refs)
    return {
        "evidence_kind_refs": {kind: refs_by_kind.get(kind, 0)
                               for kind in ("first_party", "curator", "discussion", "metadata")},
        "first_party_artifacts": len(substantive_first_party),
        "curator_artifacts": len(substantive_by_kind["curator"]),
        "discussion_artifacts": len(substantive_by_kind["discussion"]),
        "metadata_artifacts": len(artifacts_by_kind["metadata"]),
        "metadata_ref_count": metadata_ref_count,
        "substantive_ref_count": evidence_count - metadata_ref_count,
        "metadata_share": metadata_ref_count / evidence_count if evidence_count else 0.0,
        "artifact_kinds": {artifact_id: classify_artifact(artifact_rows.get(artifact_id, {}), sources)
                           for artifact_id in sorted({str(row.get("artifact_id") or "") for row in refs})},
        "evidence_kinds": {str(row.get("evidence_id") or ""): evidence_kind(
            row, artifact_rows.get(str(row.get("artifact_id") or ""), {}), sources) for row in refs},
    }


def is_synthetic_artifact(artifact: Mapping[str, Any], source: Mapping[str, Any] | None = None) -> bool:
    source = source or {}
    url = str(artifact.get("canonical_url") or "")
    source_url = str(source.get("canonical_url") or "")
    metadata = " ".join(str(artifact.get(key) or "") for key in
                         ("title", "artifact_id", "canonical_url", "artifact_type"))
    metadata += " " + " ".join(str(source.get(key) or "") for key in ("name", "source_id", "canonical_url"))
    return bool(_SYNTHETIC_MARKER.search(metadata) or _SYNTHETIC_MARKER.search(url + " " + source_url))


def curator_attribution(text: str) -> bool:
    return bool(_CURATOR_ATTRIBUTION.search(str(text or "")))


def preview_privacy_issues(markdown: str) -> list[str]:
    return sorted(name for name, pattern in _UNSAFE_PREVIEW_PATTERNS.items() if pattern.search(markdown))


def scrub_audit_text(value: str, *, limit: int = 700) -> str:
    text = str(value or "")
    text = re.sub(r"(?i)\b(?:authorization|cookie|set-cookie)\s*[:=]\s*[^\s,;]+", "[redacted]", text)
    text = re.sub(r"(?i)\b(?:access[_-]?token|refresh[_-]?token|api[_-]?key|xsec_token|signature|session)\s*[:=]\s*[^\s,;&]+", "[redacted]", text)
    text = re.sub(r"https?://[^\s<>\])]+", lambda match: safe_public_url(match.group(0)) or "[private link omitted]", text)
    text = re.sub(r"(?i)\b[A-Z]:\\[^\s<>\])]+|/mnt/[^\s<>\])]+|file://[^\s<>\])]+", "[local path omitted]", text)
    return text[:limit]


def quality_metrics(refs: list[dict[str, Any]], brief: Mapping[str, Any],
                    artifact_rows: Mapping[str, Mapping[str, Any]],
                    sources: Mapping[str, Mapping[str, Any]],
                    *, broken_citation_count: int = 0, missing_evidence_count: int = 0) -> dict[str, Any]:
    composition = classify_evidence(refs, artifact_rows, sources)
    provenance = brief.get("model_provenance") or {}
    artifacts = {str(row.get("artifact_id") or "") for row in refs}
    source_ids = {str(row.get("source_id") or "") for row in refs if row.get("source_id")}
    claims = list(brief.get("claims") or [])
    evidence_by_id = {str(row.get("evidence_id") or ""): row for row in refs}
    secondary_only = 0
    metadata_only = 0
    for claim in claims:
        if claim.get("claim_type") != "fact":
            continue
        linked = [evidence_by_id[item] for item in claim.get("evidence_ids", []) if item in evidence_by_id]
        if linked and all(composition["evidence_kinds"].get(str(row.get("evidence_id"))) == "metadata"
                          for row in linked):
            metadata_only += 1
        supported_by_primary = any(composition["evidence_kinds"].get(str(row.get("evidence_id"))) == "first_party"
                                   for row in linked)
        if not supported_by_primary and not curator_attribution(str(claim.get("text") or "")):
            secondary_only += 1
    return {
        "evidence_count": len(refs),
        "artifact_count": len(artifacts),
        "source_count": len(source_ids),
        "first_party_artifacts": composition["first_party_artifacts"],
        "curator_artifacts": composition["curator_artifacts"],
        "discussion_artifacts": composition["discussion_artifacts"],
        "metadata_artifacts": composition["metadata_artifacts"],
        "claim_count": len(claims),
        "supported_fact_count": int((brief.get("metrics") or {}).get("supported_fact_count", 0)),
        "unsupported_fact_count": int((brief.get("metrics") or {}).get("unsupported_fact_count", 0)),
        "secondary_only_fact_count": secondary_only,
        "metadata_only_fact_count": metadata_only,
        "disagreement_count": len(brief.get("disagreements") or []),
        "broken_citation_count": int(broken_citation_count),
        "missing_evidence_count": int(missing_evidence_count),
        "input_tokens": provenance.get("input_tokens"),
        "output_tokens": provenance.get("output_tokens"),
        "evidence_kind_refs": composition["evidence_kind_refs"],
    }


def disagreement_evidence_issues(disagreements: list[dict[str, Any]],
                                 evidence_by_id: Mapping[str, Mapping[str, Any]]) -> int:
    issues = 0
    for item in disagreements:
        ids = [str(value) for value in item.get("evidence_ids", []) if str(value) in evidence_by_id]
        artifact_ids = {str(evidence_by_id[value].get("artifact_id") or "") for value in ids}
        text = str(item.get("text") or "")
        if len(ids) < 2 or (len(artifact_ids) < 2 and "single_source_internal_tension" not in text):
            issues += 1
    return issues
