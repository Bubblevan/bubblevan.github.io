from __future__ import annotations

from collections import Counter
from typing import Any
from urllib.parse import urlsplit


# These Hugging Face URL roots are web/catalog routes, not model repository IDs.
# datasets and spaces are valid repository namespaces, but must keep their own type.
HF_RESERVED_NAMESPACE_ROOTS = frozenset({
    "api", "blog", "collections", "datasets", "docs", "join", "organizations",
    "papers", "spaces", "tasks",
})
HF_DOCS_API_ETC_ROOTS = frozenset({"api", "collections", "docs", "join", "organizations", "tasks"})


def audit_huggingface_reserved_namespace_models(store: Any) -> dict[str, Any]:
    """Count model Artifacts whose Hugging Face URL belongs to a reserved root."""
    counts: Counter[str] = Counter()
    for artifact in store.iter_records("artifact"):
        if str(artifact.get("artifact_type") or "") != "model":
            continue
        parts = urlsplit(str(artifact.get("canonical_url") or ""))
        if (parts.hostname or "").casefold().removeprefix("www.") != "huggingface.co":
            continue
        segments = [value for value in parts.path.split("/") if value]
        if segments:
            root = segments[0].casefold()
            if root in HF_RESERVED_NAMESPACE_ROOTS:
                counts[root] += 1

    other = {
        root: counts.get(root, 0)
        for root in sorted(HF_RESERVED_NAMESPACE_ROOTS - {"blog", "papers"} - HF_DOCS_API_ETC_ROOTS)
    }
    checks = {
        "HF blog URLs typed model": counts.get("blog", 0),
        "HF papers URLs typed model": counts.get("papers", 0),
        "HF docs/API/etc typed model": sum(counts.get(root, 0) for root in HF_DOCS_API_ETC_ROOTS),
        "HF other reserved namespaces typed model": other,
    }
    total = sum(counts.values())
    return {
        "schema": "bubblevan/huggingface-reserved-namespace-audit/v1",
        "passed": total == 0,
        "violations_total": total,
        "checks": checks,
    }
