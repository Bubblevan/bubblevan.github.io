from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
import time

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.intelligence.feed.feedback_projection import project_feedback
from scripts.intelligence.feed.generation import load_dense_resource
from scripts.intelligence.feed.models import profile_hash, update_profile
from scripts.intelligence.feed.service import apply_feedback, daily_feed, feedback_stats
from scripts.intelligence.feed.storage import FeedRepository
from scripts.intelligence.feed.writer_guard import acquire_ui_writer
from scripts.intelligence.retrieval.corpus import build_snapshot
from scripts.intelligence.store import JsonlStore
from scripts.intelligence.topics import topic_aliases
from scripts.intelligence.runner import load_source_catalog


STORE_DIR = ROOT / "data" / "intelligence" / "events"
RUNTIME_DIR = ROOT / "data" / "intelligence" / "runtime"
PRIVATE_DIR = ROOT / "data" / "intelligence" / "private" / "feed"
_WRITER_MARKER = acquire_ui_writer(PRIVATE_DIR.parent)


@st.cache_resource(show_spinner="加载本机 Dense 索引…")
def cached_dense(corpus_hash: str, model: str, model_revision: str, device: str | None,
                 store_dir: str, runtime_dir: str):
    store = JsonlStore(store_dir)
    snapshot = build_snapshot(store)
    if snapshot.corpus_hash != corpus_hash:
        raise RuntimeError("corpus changed during Dense cache initialization")
    actual_revision = None if model_revision == "main" else model_revision
    return load_dense_resource(snapshot, runtime_dir, model, actual_revision, device)


def dense_factory(snapshot, runtime_dir, model, revision, device):
    from scripts.intelligence.retrieval.dense import _cached_revision
    model_revision = revision or _cached_revision(model) or "main"
    return cached_dense(snapshot.corpus_hash, model, model_revision, device, str(STORE_DIR), runtime_dir)


def _record_and_refresh(repository, store, run, item, action, *, target_id=None):
    result = apply_feedback(repository, store, feed_run_id=run["feed_run_id"],
                            artifact_id=item["artifact_id"], action=action, target_id=target_id)
    if result["status"] == "recorded":
        daily_feed(STORE_DIR, RUNTIME_DIR, PRIVATE_DIR, date=run["feed_date"], refresh=True,
                   dense_resource_factory=dense_factory)
        st.toast("Feedback recorded; showing the next immutable feed revision.")


@st.cache_data(show_spinner=False)
def _catalogs():
    store = JsonlStore(STORE_DIR)
    sources = {str(row["source_id"]): str(row.get("name") or row["source_id"])
               for row in store.iter_records("source")}
    sources.update({str(row["source_id"]): str(row["name"]) for row in load_source_catalog()})
    import yaml
    topic_rows = yaml.safe_load((ROOT / "data/intelligence/topics.yaml").read_text(encoding="utf-8"))["topics"]
    source_rows = load_source_catalog()
    source_options = dict(sources)
    source_options.update({str(row["source_id"]): str(row["name"]) for row in source_rows})
    return ({str(row["topic_id"]): str(row.get("name") or row["topic_id"]) for row in topic_rows}, sources,
            source_options)


def main():
    st.set_page_config(page_title="Research Intelligence · Today", page_icon="🧭", layout="wide")
    st.title("Personal Research Intelligence")
    st.caption("本地个人研究信息流 · deterministic feed-v0")
    repository = FeedRepository(PRIVATE_DIR)
    store = JsonlStore(STORE_DIR)
    profile = repository.load_profile()
    projection = project_feedback(repository.all_feedback(store))
    topic_names, source_names, catalog_sources = _catalogs()
    page = st.sidebar.radio("页面", ["Today", "Saved", "Profile", "Stats"])

    if page == "Today":
        picked_date = st.date_input("Feed date", value=date.today())
        left, right = st.columns([1, 4])
        with left:
            refresh = st.button("Refresh revision", type="primary")
        run = daily_feed(STORE_DIR, RUNTIME_DIR, PRIVATE_DIR, date=picked_date.isoformat(),
                         refresh=refresh, dense_resource_factory=dense_factory)
        st.caption(f"Revision {run['revision']} · {len(run['items'])} cards · corpus {run['corpus_hash'][:12]}")
        if not run["items"]:
            st.info("当前七天窗口内没有符合条件的近期候选。可以稍后重试，或先检查本地 connector 是否已有采集。")
        for item in run["items"]:
            card = item.get("card", {})
            with st.container(border=True):
                st.subheader(f"{item['rank']}. {card.get('title') or item.get('title') or 'Untitled'}")
                metadata = [str(card.get("artifact_type") or "other"),
                            " · ".join(card.get("source_names", [])) or "来源未归属",
                            card.get("published_at") or "发布时间缺失"]
                st.caption(" | ".join(map(str, metadata)))
                if card.get("summary"):
                    st.write(card["summary"])
                if card.get("canonical_url"):
                    st.markdown(f"[打开原文]({card['canonical_url']})")
                st.info(f"为什么推荐：{item.get('why') or '近期内容。'}")
                if item.get("freshness_basis") == "observed_at_fallback":
                    st.caption("时间依据：首次本地观察时间")
                result = apply_feedback(repository, store, feed_run_id=run["feed_run_id"],
                                        artifact_id=item["artifact_id"], action="impression")
                if result["status"] == "recorded":
                    pass
                cols = st.columns(6)
                actions = [("Useful", "useful"), ("Not relevant", "not_relevant"),
                           ("Save", "save"), ("Hide", "hide")]
                for col, (label, action) in zip(cols[:4], actions):
                    with col:
                        if st.button(label, key=f"{run['feed_run_id']}-{item['artifact_id']}-{action}"):
                            _record_and_refresh(repository, store, run, item, action)
                            st.rerun()
                with cols[4]:
                    source_id = next(iter(item.get("source_ids", [])), None)
                    if source_id and st.button("Less source", key=f"{run['feed_run_id']}-{item['artifact_id']}-source"):
                        _record_and_refresh(repository, store, run, item, "show_less_from_source", target_id=source_id)
                        st.rerun()
                with cols[5]:
                    topic_id = next(iter(item.get("topics", [])), None)
                    if topic_id and st.button("Less topic", key=f"{run['feed_run_id']}-{item['artifact_id']}-topic"):
                        _record_and_refresh(repository, store, run, item, "show_less_of_topic", target_id=topic_id)
                        st.rerun()
    elif page == "Saved":
        st.header("Saved")
        saved_ids = projection["saved_artifact_ids"]
        runs = repository.runs()
        for artifact_id in saved_ids:
            run = next((row for row in reversed(runs) if any(item["artifact_id"] == artifact_id for item in row["items"])), None)
            if not run: continue
            item = next(row for row in run["items"] if row["artifact_id"] == artifact_id)
            card = item.get("card", {})
            with st.container(border=True):
                st.subheader(card.get("title") or artifact_id)
                st.caption(" · ".join(card.get("source_names", [])))
                st.write(card.get("summary") or "")
                if card.get("canonical_url"): st.markdown(f"[打开原文]({card['canonical_url']})")
                if st.button("Unsave", key=f"unsave-{artifact_id}"):
                    apply_feedback(repository, store, feed_run_id=run["feed_run_id"], artifact_id=artifact_id, action="unsave")
                    st.rerun()
        if not saved_ids: st.info("还没有保存的内容。")
    elif page == "Profile":
        st.header("Profile")
        selected_topics = st.multiselect("选择主题", list(topic_names),
                                         default=profile["selected_topic_ids"], format_func=lambda key: topic_names.get(key, key))
        followed_sources = st.multiselect("关注来源", list(catalog_sources),
                                          default=[x for x in profile["followed_source_ids"] if x in catalog_sources],
                                          format_func=lambda key: catalog_sources.get(key, key))
        blocked_topics = st.multiselect("屏蔽主题", list(topic_names),
                                        default=profile["blocked_topic_ids"], format_func=lambda key: topic_names.get(key, key))
        blocked_sources = st.multiselect("屏蔽来源", list(catalog_sources),
                                         default=[x for x in profile["blocked_source_ids"] if x in catalog_sources],
                                         format_func=lambda key: catalog_sources.get(key, key))
        if st.button("Save profile", type="primary"):
            updated = update_profile(profile, add={
                "selected_topic_ids": selected_topics, "followed_source_ids": followed_sources,
                "blocked_topic_ids": blocked_topics, "blocked_source_ids": blocked_sources,
            }, remove={
                "selected_topic_ids": [x for x in profile["selected_topic_ids"] if x not in selected_topics],
                "followed_source_ids": [x for x in profile["followed_source_ids"] if x not in followed_sources],
                "blocked_topic_ids": [x for x in profile["blocked_topic_ids"] if x not in blocked_topics],
                "blocked_source_ids": [x for x in profile["blocked_source_ids"] if x not in blocked_sources],
            })
            repository.save_profile(updated)
            if updated != profile:
                daily_feed(STORE_DIR, RUNTIME_DIR, PRIVATE_DIR, date=date.today().isoformat(), refresh=True,
                           dense_resource_factory=dense_factory)
            st.success(f"Profile saved · version {updated['version']} · {profile_hash(updated)[:12]}")
            st.rerun()
        st.caption(f"Profile v{profile['version']} · {profile_hash(profile)}")
    else:
        st.header("Stats")
        st.json(feedback_stats(store, repository))


if __name__ == "__main__":
    main()
