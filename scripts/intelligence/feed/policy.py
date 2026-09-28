from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
import statistics
from typing import Any, Mapping

from .models import utc_datetime


def rank_and_select(candidates: list[dict[str, Any]], *, profile: Mapping[str, Any], projection: Mapping[str, Any],
                    feed_date: str, target_size: int = 12, min_size: int = 10,
                    source_cap: int = 2, topic_cap: int = 4) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    hidden = set(projection.get("hidden_artifact_ids", []))
    blocked_sources = set(profile.get("blocked_source_ids", [])) | set(projection.get("blocked_source_ids", []))
    blocked_topics = set(profile.get("blocked_topic_ids", [])) | set(projection.get("blocked_topic_ids", []))
    exposures = projection.get("impression_counts", {})
    not_relevant = set(projection.get("not_relevant_artifact_ids", []))
    pool = []
    for candidate in candidates:
        sources = set(candidate.get("source_ids", []))
        topics = set(candidate.get("topics", []))
        if candidate["artifact_id"] in hidden or sources.intersection(blocked_sources) or topics.intersection(blocked_topics):
            continue
        row = dict(candidate)
        row["previously_seen"] = int(exposures.get(row["artifact_id"], 0)) > 0
        row["previously_not_relevant"] = row["artifact_id"] in not_relevant
        row["interest_tier"] = _interest_tier(row, profile)
        row["why"] = _reason(row)
        pool.append(row)
    pool.sort(key=_rank_key)
    selected: list[dict[str, Any]] = []
    source_limit, topic_limit = source_cap, topic_cap
    while True:
        selected = _greedy(pool, target_size, source_limit, topic_limit)
        if len(selected) >= min_size or len(selected) >= len(pool) or (source_limit >= target_size and topic_limit >= target_size):
            break
        source_limit += 1
        topic_limit += 1
    if len(selected) >= min_size and len(selected) < target_size and len(selected) < len(pool):
        relaxed = _greedy(pool, target_size, source_limit + 1, topic_limit + 1)
        relaxed_metrics = feed_metrics(relaxed, candidate_count=len(candidates), feed_date=feed_date,
                                       hidden_ids=hidden, source_cap_used=source_limit + 1,
                                       topic_cap_used=topic_limit + 1)
        if (len(relaxed) > len(selected) and relaxed_metrics["max_source_share"] <= 0.45
                and relaxed_metrics["max_topic_share"] <= 0.6):
            selected = relaxed
            source_limit += 1
            topic_limit += 1
    for index, row in enumerate(selected, 1):
        row["rank"] = index
    metrics = feed_metrics(selected, candidate_count=len(candidates), feed_date=feed_date,
                           hidden_ids=hidden, source_cap_used=source_limit, topic_cap_used=topic_limit)
    return selected, metrics


def _rank_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        int(bool(row.get("previously_seen"))),
        int(bool(row.get("previously_not_relevant"))),
        int(row.get("interest_tier", 4)),
        int(not bool(row.get("topic_exact"))),
        row.get("dense_best_rank") if row.get("dense_best_rank") is not None else 10**9,
        row.get("bm25_best_rank") if row.get("bm25_best_rank") is not None else 10**9,
        int(row.get("mention_role") != "primary"),
        -_content_time(row).timestamp() if _content_time(row) else float("inf"),
        str(row["artifact_id"]),
    )


def _interest_tier(row: Mapping[str, Any], profile: Mapping[str, Any]) -> int:
    source = set(profile.get("followed_source_ids", []))
    topics = set(profile.get("selected_topic_ids", []))
    source_match = bool(source.intersection(row.get("source_ids", [])))
    topic_match = bool(topics.intersection(row.get("topics", [])))
    if source_match and topic_match: return 0
    if topic_match: return 1
    if row.get("followed_source_match"): return 2
    if row.get("useful_exemplar_matches"): return 3
    return 4


def _reason(row: Mapping[str, Any]) -> str:
    topic_names = row.get("selected_topic_names") or row.get("selected_topic_matches")
    if row.get("followed_source_match") and topic_names:
        reason = f"来自已关注来源，且匹配主题：{_names(topic_names)}。"
    elif topic_names:
        reason = f"匹配你选择的主题：{_names(topic_names)}。"
    elif row.get("followed_source_match"):
        reason = "来自你关注的来源。"
    elif row.get("useful_exemplar_matches"):
        reason = "与标记为有用的内容语义相近。"
    elif row.get("topic_exact") and row.get("topics"):
        reason = f"近期内容，精确匹配主题：{_names(row.get('topic_names') or row['topics'])}。"
    else:
        reason = "近期新内容。"
    if row.get("previously_not_relevant"):
        reason += "你此前标记过不相关，因此优先级下调。"
    elif row.get("previously_seen"):
        reason += "你此前看过，因此优先级下调。"
    return reason


def _names(values: Any) -> str:
    return "、".join(str(item) for item in sorted(values))


def _greedy(pool: list[dict[str, Any]], target: int, source_cap: int, topic_cap: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    source_counts: Counter[str] = Counter()
    topic_counts: Counter[str] = Counter()
    selected_ids: set[str] = set()
    for row in pool:
        if row["artifact_id"] in selected_ids:
            continue
        sources = set(map(str, row.get("source_ids", [])))
        topics = set(map(str, row.get("topics", [])))
        if any(source_counts[source] >= source_cap for source in sources):
            continue
        if any(topic_counts[topic] >= topic_cap for topic in topics):
            continue
        selected.append(dict(row))
        selected_ids.add(row["artifact_id"])
        source_counts.update(sources)
        topic_counts.update(topics)
        if len(selected) >= target:
            break
    return selected


def feed_metrics(selected: list[Mapping[str, Any]], *, candidate_count: int, feed_date: str,
                 hidden_ids: set[str], source_cap_used: int, topic_cap_used: int) -> dict[str, Any]:
    sources = Counter(source for row in selected for source in set(row.get("source_ids", [])))
    topics = Counter(topic for row in selected for topic in set(row.get("topics", [])))
    ages = []
    for row in selected:
        moment = _content_time(row)
        if moment:
            reference = datetime.combine(date.fromisoformat(feed_date), datetime.max.time(), tzinfo=timezone.utc)
            ages.append(max(0.0, (reference - moment).total_seconds() / 3600))
    return {
        "candidate_count": candidate_count,
        "selected_count": len(selected),
        "unique_sources": len(sources),
        "max_source_share": round(max(sources.values(), default=0) / len(selected), 4) if selected else 0.0,
        "unique_topics": len(topics),
        "max_topic_share": round(max(topics.values(), default=0) / len(selected), 4) if selected else 0.0,
        "median_age_hours": round(statistics.median(ages), 2) if ages else None,
        "observed_at_fallback_count": sum(row.get("freshness_basis") == "observed_at_fallback" for row in selected),
        "previously_seen_count": sum(bool(row.get("previously_seen")) for row in selected),
        "hidden_leak_count": sum(row.get("artifact_id") in hidden_ids for row in selected),
        "items_with_reason": sum(bool(row.get("why")) for row in selected),
        "source_cap_used": source_cap_used,
        "topic_cap_used": topic_cap_used,
    }


def _content_time(row: Mapping[str, Any]) -> datetime | None:
    value = row.get("published_at") or row.get("first_observed_at")
    try:
        return utc_datetime(str(value)) if value else None
    except ValueError:
        return None
