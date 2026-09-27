from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import re
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from scripts.pkb.normalize_url import normalize_url

from .ids import normalize_identity


_SENSITIVE_QUERY_KEYS = {
    "authorization", "auth", "cookie", "session", "sessionid", "session_id",
    "session_token", "token", "access_token", "refresh_token", "xsec_token",
}
_ARXIV_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:arxiv\s*:\s*)?((?:\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?)(?![A-Za-z0-9])",
    re.IGNORECASE,
)
_DOI_RE = re.compile(r"\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.IGNORECASE)
_URL_RE = re.compile(r"https?://[^\s<>\u0000-\u0020\"']+", re.IGNORECASE)
_TRAILING_URL_PUNCTUATION = ".,;:!?)]}"


def canonicalize_url(url: str) -> str:
    """Reuse PKB URL rules while removing credentials and private query values."""
    value = str(url or "").strip()
    if not value:
        return ""
    try:
        parts = urlsplit(value)
        if not parts.scheme and not parts.netloc:
            parts = urlsplit("https://" + value)
        host = parts.hostname or ""
        if not host:
            return normalize_url(value)
        try:
            port = parts.port
        except ValueError:
            return ""
        netloc = host.lower()
        if ":" in host and not host.startswith("["):
            netloc = f"[{netloc}]"
        if port and not ((parts.scheme or "https").lower() == "https" and port == 443) and not (
            (parts.scheme or "https").lower() == "http" and port == 80
        ):
            netloc = f"{netloc}:{port}"
        safe_query = [
            (key, val)
            for key, val in parse_qsl(parts.query, keep_blank_values=True)
            if not _is_sensitive_query_key(key)
        ]
        safe = urlunsplit((parts.scheme or "https", netloc, parts.path, _encode_query(safe_query), ""))
        return normalize_url(safe)
    except (TypeError, ValueError):
        return ""


def _encode_query(items: list[tuple[str, str]]) -> str:
    from urllib.parse import urlencode

    return urlencode(items, doseq=True)


def _is_sensitive_query_key(key: str) -> bool:
    lowered = key.strip().casefold()
    return (
        lowered in _SENSITIVE_QUERY_KEYS
        or lowered.startswith("xsec_")
        or lowered.endswith("_token")
        or lowered.endswith("_session")
    )


def extract_arxiv_id(value: str) -> str | None:
    text = str(value or "")
    match = _ARXIV_RE.search(text)
    if not match:
        # arXiv URLs contain the identifier after /abs/ or /pdf/.
        url_match = re.search(r"arxiv\.org/(?:abs|pdf)/([^?#]+)", text, re.IGNORECASE)
        if not url_match:
            return None
        candidate = url_match.group(1).removesuffix(".pdf")
    else:
        candidate = match.group(1)
    return re.sub(r"v\d+$", "", candidate.lower())


def extract_doi(value: str) -> str | None:
    text = str(value or "").strip()
    if "doi.org/" in text.casefold():
        text = re.split(r"doi\.org/", text, flags=re.IGNORECASE)[-1]
    match = _DOI_RE.search(text)
    if not match:
        return None
    return match.group(1).rstrip(".,;:!?)]}").casefold()


def extract_github_repo(value: str) -> str | None:
    parts = urlsplit(str(value or "").strip())
    if (parts.hostname or "").casefold() not in {"github.com", "www.github.com"}:
        return None
    segments = [segment for segment in parts.path.split("/") if segment]
    if len(segments) < 2:
        return None
    owner, repo = segments[0], segments[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not owner or not repo or owner.casefold() in {"features", "topics", "collections", "marketplace"}:
        return None
    return f"{owner}/{repo}".casefold()


def extract_huggingface_repo(value: str) -> str | None:
    parts = urlsplit(str(value or "").strip())
    if (parts.hostname or "").casefold() not in {"huggingface.co", "www.huggingface.co"}:
        return None
    segments = [segment for segment in parts.path.split("/") if segment]
    if segments and segments[0] in {"models", "datasets", "spaces"}:
        segments = segments[1:]
    if len(segments) < 2:
        return None
    return f"{segments[0]}/{segments[1]}".casefold()


def artifact_identity(candidate: Mapping[str, object]) -> str:
    """Resolve identity by DOI, arXiv, GitHub, Hugging Face, URL, then title."""
    identifiers = candidate.get("identifiers")
    identifiers = identifiers if isinstance(identifiers, Mapping) else {}
    canonical_url = canonicalize_url(str(candidate.get("canonical_url") or ""))

    doi = extract_doi(str(identifiers.get("doi") or "")) or extract_doi(canonical_url)
    if doi:
        return f"doi:{doi}"
    arxiv = extract_arxiv_id(str(identifiers.get("arxiv") or "")) or extract_arxiv_id(canonical_url)
    if arxiv:
        return f"arxiv:{arxiv}"
    github = str(identifiers.get("github") or "")
    github_repo = extract_github_repo(github) or _normalize_repo_id(github)
    if not github_repo:
        github_repo = extract_github_repo(canonical_url)
    if github_repo:
        return f"github:{github_repo}"
    hf = str(identifiers.get("huggingface") or "")
    hf_repo = extract_huggingface_repo(hf) or _normalize_repo_id(hf)
    if not hf_repo:
        hf_repo = extract_huggingface_repo(canonical_url)
    if hf_repo:
        return f"huggingface:{hf_repo}"
    if canonical_url:
        return f"url:{canonical_url}"
    title = normalize_identity(candidate.get("title"))
    if title:
        return f"title:{title}"
    raise ValueError("artifact candidate needs a DOI, arXiv ID, repository, URL, or title")


def _normalize_repo_id(value: str) -> str | None:
    text = str(value or "").strip().strip("/")
    if text.endswith(".git"):
        text = text[:-4]
    if re.fullmatch(r"[^/\s]+/[^/\s]+", text):
        return text.casefold()
    return None


def _base_candidate(
    *,
    artifact_type: str = "other",
    title: str = "",
    canonical_url: str = "",
    identifiers: dict[str, str | None] | None = None,
) -> dict[str, object]:
    return {
        "artifact_type": artifact_type,
        "title": title.strip(),
        "canonical_url": canonicalize_url(canonical_url),
        "identifiers": {
            "doi": None,
            "arxiv": None,
            "github": None,
            "huggingface": None,
            **(identifiers or {}),
        },
        "authors": [],
        "organizations": [],
        "summary": "",
        "topics": [],
    }


def candidate_from_url(url: str) -> dict[str, object]:
    canonical = canonicalize_url(url)
    if not canonical:
        raise ValueError("candidate URL is invalid")
    doi = extract_doi(canonical)
    if doi:
        return _base_candidate(
            artifact_type="paper",
            canonical_url=f"https://doi.org/{doi}",
            identifiers={"doi": doi},
        )
    arxiv = extract_arxiv_id(canonical)
    if arxiv:
        return _base_candidate(
            artifact_type="paper",
            canonical_url=f"https://arxiv.org/abs/{arxiv}",
            identifiers={"arxiv": arxiv},
        )
    github = extract_github_repo(canonical)
    if github:
        return _base_candidate(
            artifact_type="repository",
            canonical_url=f"https://github.com/{github}",
            identifiers={"github": github},
        )
    hf = extract_huggingface_repo(canonical)
    if hf:
        path = urlsplit(canonical).path.split("/")
        artifact_type = "dataset" if "datasets" in path else "model"
        return _base_candidate(
            artifact_type=artifact_type,
            canonical_url=f"https://huggingface.co/{hf}",
            identifiers={"huggingface": hf},
        )
    return _base_candidate(canonical_url=canonical)


def normalize_candidate(value: Mapping[str, object]) -> dict[str, object]:
    """Normalize a candidate already explicitly surfaced by a sanitized reader."""
    raw_identifiers = value.get("identifiers")
    raw_identifiers = raw_identifiers if isinstance(raw_identifiers, Mapping) else {}
    canonical_url = canonicalize_url(str(value.get("canonical_url") or value.get("url") or ""))
    url_candidate = candidate_from_url(canonical_url) if canonical_url else None
    identifiers: dict[str, str | None] = {
        "doi": extract_doi(str(raw_identifiers.get("doi") or "")),
        "arxiv": extract_arxiv_id(str(raw_identifiers.get("arxiv") or "")),
        "github": extract_github_repo(str(raw_identifiers.get("github") or ""))
        or _normalize_repo_id(str(raw_identifiers.get("github") or "")),
        "huggingface": extract_huggingface_repo(str(raw_identifiers.get("huggingface") or ""))
        or _normalize_repo_id(str(raw_identifiers.get("huggingface") or "")),
    }
    if url_candidate:
        for key, item in url_candidate["identifiers"].items():
            identifiers[key] = identifiers[key] or item
    title = str(value.get("title") or "").strip()

    if identifiers["doi"]:
        canonical_url = f"https://doi.org/{identifiers['doi']}"
        artifact_type = "paper"
    elif identifiers["arxiv"]:
        canonical_url = f"https://arxiv.org/abs/{identifiers['arxiv']}"
        artifact_type = "paper"
    elif identifiers["github"]:
        canonical_url = f"https://github.com/{identifiers['github']}"
        artifact_type = "repository"
    elif identifiers["huggingface"]:
        canonical_url = f"https://huggingface.co/{identifiers['huggingface']}"
        artifact_type = str(
            value.get("artifact_type")
            or (url_candidate["artifact_type"] if url_candidate else "")
            or "model"
        )
    else:
        artifact_type = str(
            value.get("artifact_type")
            or (url_candidate["artifact_type"] if url_candidate else "")
            or "other"
        )
    allowed = {
        "paper", "blog", "repository", "model", "dataset", "technical_report",
        "discussion", "social_post", "course", "tool", "other",
    }
    if artifact_type not in allowed:
        artifact_type = "other"
    candidate = _base_candidate(
        artifact_type=artifact_type,
        title=title,
        canonical_url=canonical_url,
        identifiers=identifiers,
    )
    candidate["authors"] = sorted(set(_string_values(value.get("authors"))))
    candidate["organizations"] = sorted(set(_string_values(value.get("organizations"))))
    candidate["summary"] = str(value.get("summary") or "").strip()
    candidate["topics"] = sorted(set(_string_values(value.get("topics"))))
    return candidate


def merge_candidates(values: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    candidates: dict[str, dict[str, object]] = {}
    for value in values:
        _add_candidate(candidates, normalize_candidate(value))
    return [candidates[key] for key in sorted(candidates)]


def _string_values(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def extract_artifact_candidates(
    text: str,
    urls: Sequence[str] = (),
    *,
    exclude_urls: Sequence[str] = (),
) -> list[dict[str, object]]:
    """Extract conservative candidates; unresolved references stay type=other."""
    excluded = {canonicalize_url(url) for url in exclude_urls if canonicalize_url(url)}
    candidates: dict[str, dict[str, object]] = {}
    combined = str(text or "")

    for value in (match.group(0).rstrip(_TRAILING_URL_PUNCTUATION) for match in _URL_RE.finditer(combined)):
        if canonicalize_url(value) not in excluded:
            _add_candidate(candidates, candidate_from_url(value))
    for value in urls:
        if canonicalize_url(value) and canonicalize_url(value) not in excluded:
            _add_candidate(candidates, candidate_from_url(value))

    doi_values = {match.group(1).rstrip(".,;:!?)]}").casefold() for match in _DOI_RE.finditer(combined)}
    for doi in sorted(doi_values):
        _add_candidate(
            candidates,
            _base_candidate(
                artifact_type="paper",
                canonical_url=f"https://doi.org/{doi}",
                identifiers={"doi": doi},
            ),
        )
    arxiv_values = {match.group(1).lower() for match in _ARXIV_RE.finditer(combined)}
    for arxiv in sorted(arxiv_values):
        _add_candidate(
            candidates,
            _base_candidate(
                artifact_type="paper",
                canonical_url=f"https://arxiv.org/abs/{arxiv}",
                identifiers={"arxiv": arxiv},
            ),
        )
    return [candidates[key] for key in sorted(candidates)]


def _add_candidate(target: dict[str, dict[str, object]], candidate: dict[str, object]) -> None:
    try:
        key = artifact_identity(candidate)
    except ValueError:
        return
    current = target.get(key)
    if current is None:
        target[key] = candidate
        return
    merged = dict(current)
    titles = [str(item) for item in (current.get("title"), candidate.get("title")) if item]
    if titles:
        merged["title"] = min(titles, key=lambda item: (-len(item), item.casefold(), item))
    summaries = [str(item) for item in (current.get("summary"), candidate.get("summary")) if item]
    if summaries:
        merged["summary"] = min(summaries, key=lambda item: (-len(item), item.casefold(), item))
    for field in ("authors", "organizations", "topics"):
        merged[field] = sorted(set(_string_values(current.get(field)) + _string_values(candidate.get(field))))
    merged_identifiers = dict(current.get("identifiers", {}))
    for field, value in dict(candidate.get("identifiers", {})).items():
        if value:
            merged_identifiers[field] = value
    merged["identifiers"] = merged_identifiers
    type_rank = {
        "other": 0, "blog": 1, "discussion": 1, "social_post": 1,
        "repository": 2, "model": 2, "dataset": 2, "tool": 2,
        "course": 2, "technical_report": 2, "paper": 3,
    }
    left_type = str(current.get("artifact_type") or "other")
    right_type = str(candidate.get("artifact_type") or "other")
    merged["artifact_type"] = max((left_type, right_type), key=lambda item: (type_rank.get(item, 0), item))
    if key.startswith("doi:"):
        merged["canonical_url"] = "https://doi.org/" + key.removeprefix("doi:")
    elif key.startswith("arxiv:"):
        merged["canonical_url"] = "https://arxiv.org/abs/" + key.removeprefix("arxiv:")
    elif key.startswith("github:"):
        merged["canonical_url"] = "https://github.com/" + key.removeprefix("github:")
    elif key.startswith("huggingface:"):
        merged["canonical_url"] = "https://huggingface.co/" + key.removeprefix("huggingface:")
    else:
        urls = [str(item) for item in (current.get("canonical_url"), candidate.get("canonical_url")) if item]
        merged["canonical_url"] = min(urls) if urls else ""
    target[key] = merged
