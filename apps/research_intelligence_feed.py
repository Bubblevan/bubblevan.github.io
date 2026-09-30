from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.intelligence.feed.feedback_projection import project_feedback
from scripts.intelligence.feed.environment import feed_private_dir, normalize_feed_mode
from scripts.intelligence.feed.models import profile_hash
from scripts.intelligence.feed.service import apply_feedback, daily_feed, feedback_stats, mutate_profile
from scripts.intelligence.feed.storage import FeedRepository
from scripts.intelligence.ops.health import ops_status
from scripts.intelligence.ops.locks import LockContended
from scripts.intelligence.retrieval.corpus import build_snapshot
from scripts.intelligence.retrieval.manifest import dense_freshness
from scripts.intelligence.research import ResearchService
from scripts.intelligence.research.evidence.local_corpus import LocalCorpusEvidenceBackend
from scripts.intelligence.research.rendering import render_brief_markdown
from scripts.intelligence.store import JsonlStore
from scripts.intelligence.topics import topic_aliases
from scripts.intelligence.runner import load_merged_source_catalog
from scripts.intelligence.social.runner import add_social_url, sync_inbox, sync_source
from scripts.intelligence.social.storage import SocialInbox


STORE_DIR = ROOT / "data" / "intelligence" / "events"
RUNTIME_DIR = ROOT / "data" / "intelligence" / "runtime"
FEED_MODE = normalize_feed_mode()
PRIVATE_DIR = feed_private_dir(FEED_MODE)


def _record_and_refresh(repository, store, run, item, action, *, target_id=None):
    result = apply_feedback(repository, store, feed_run_id=run["feed_run_id"],
                            artifact_id=item["artifact_id"], action=action, target_id=target_id)
    if result["status"] == "recorded":
        daily_feed(STORE_DIR, RUNTIME_DIR, PRIVATE_DIR, date=run["feed_date"], refresh=True,
                   dense_enabled=False)
        st.toast("Feedback recorded; showing the next immutable feed revision.")
    return result


def _locked(call):
    try:
        return call()
    except LockContended:
        st.warning("another intelligence writer is active")
        return None


def _freshness_banner():
    status = ops_status(store_dir=STORE_DIR, runtime_dir=RUNTIME_DIR, mode=FEED_MODE)
    latest = status.get("latest_pipeline")
    if latest:
        labels = {"completed": "完成", "partial": "部分成功", "failed": "失败"}
        st.caption(f"数据更新时间：{latest.get('finished_at') or 'unknown'} · "
                   f"最近日管线：{labels.get(latest.get('status'), latest.get('status', 'unknown'))} · "
                   f"{status['healthy_sources']} / {status['active_sources']} sources healthy · "
                   f"{status['deferred_sources']} deferred · {status['stale_sources']} stale")
        if latest.get("status") == "partial":
            st.warning("最近一次日管线部分成功；当前 Feed 可用，失败来源详情见 Ops。")
        elif latest.get("status") == "failed":
            st.error("最近一次日管线失败；当前 Feed 可能基于较旧数据，请查看 Ops。")
    else:
        st.caption("Daily pipeline 尚未运行；以下只显示本机当前已采集数据。")
    if status.get("feed_refresh_pending"):
        st.info("新的采集数据已就绪，刷新今日 Feed 后会创建新的不可变修订。")
    return status


@st.cache_data(show_spinner=False)
def _catalogs():
    store = JsonlStore(STORE_DIR)
    sources = {str(row["source_id"]): str(row.get("name") or row["source_id"])
               for row in store.iter_records("source")}
    sources.update({str(row["source_id"]): str(row["name"]) for row in load_merged_source_catalog()})
    import yaml
    topic_rows = yaml.safe_load((ROOT / "data/intelligence/topics.yaml").read_text(encoding="utf-8"))["topics"]
    source_rows = load_merged_source_catalog()
    source_options = dict(sources)
    source_options.update({str(row["source_id"]): str(row["name"]) for row in source_rows})
    return ({str(row["topic_id"]): str(row.get("name") or row["topic_id"]) for row in topic_rows}, sources,
            source_options)


def _research_service():
    return ResearchService(STORE_DIR, RUNTIME_DIR, ROOT / "data" / "intelligence" / "private",
                           repository_root=ROOT,
                           evidence_backend=LocalCorpusEvidenceBackend(STORE_DIR, RUNTIME_DIR, allow_dense=False))


def _research_from_artifact(artifact_id: str, *, feed_run_id: str | None = None):
    service = _research_service()
    session = service.start(artifact_ids=[artifact_id], source_feed_run_id=feed_run_id)
    evidence = service.collect_evidence(session["research_session_id"])
    st.session_state["research_session_id"] = session["research_session_id"]
    st.session_state["research_selected_session"] = session["research_session_id"]
    st.session_state["page"] = "Research"
    st.session_state["research_evidence_count"] = evidence["evidence_count"]


@st.cache_data(ttl=60, show_spinner=False)
def _dense_index_status():
    current_snapshot = build_snapshot(JsonlStore(STORE_DIR))
    return dense_freshness(current_snapshot, RUNTIME_DIR)


def _render_research_page():
    st.header("Research")
    st.caption("研究是独立于保存/有用标记的显式动作。会话、证据和草稿保存在本机私有目录。")
    store = JsonlStore(STORE_DIR)
    dense_status = _dense_index_status()
    st.info(f"Dense index: **{dense_status['dense_status']}**")
    if dense_status["dense_status"] != "fresh":
        st.caption("当前研究会跳过 Dense，使用 BM25、Topic、Source 和精确 Graph evidence。")
        st.code("python -m scripts.intelligence.cli retrieval-build --routes dense", language="powershell")
    service = _research_service()
    artifact_rows = list(service.artifacts.iter_canonical())
    artifact_labels = {str(row["artifact_id"]): f"{row.get('title') or row['artifact_id']} · {row['artifact_id']}"
                       for row in artifact_rows}
    with st.form("research-start-form"):
        question = st.text_area("Research question", key="research-question")
        seeds = st.multiselect("Optional seed Artifacts", list(artifact_labels),
                               format_func=lambda item: artifact_labels.get(item, item))
        start = st.form_submit_button("Collect evidence", type="primary")
    if start:
        try:
            session = service.start(question, artifact_ids=seeds)
            gathered = service.collect_evidence(session["research_session_id"])
            st.session_state["research_session_id"] = session["research_session_id"]
            st.session_state["research_selected_session"] = session["research_session_id"]
            st.success(f"Evidence ready · {gathered['evidence_count']} references · corpus {str(gathered.get('corpus_hash') or '')[:12]}")
        except Exception as exc:
            st.error(f"Unable to collect research evidence: {type(exc).__name__}")

    sessions = service.list_sessions()
    session_ids = [str(row["research_session_id"]) for row in sessions]
    selected = st.session_state.get("research_selected_session") or st.session_state.get("research_session_id")
    if selected not in session_ids and session_ids:
        selected = session_ids[0]
    if not session_ids:
        st.info("Start a question or use “Research this” on a Feed/Saved item to begin.")
        return
    if st.session_state.get("research_evidence_count") is not None:
        st.success(f"Evidence ready · {st.session_state.pop('research_evidence_count')} references")
    selected = st.selectbox("Research session", session_ids, index=session_ids.index(selected) if selected in session_ids else 0,
                            format_func=lambda item: f"{item} · {next((row['status'] for row in sessions if row['research_session_id'] == item), '')}")
    st.session_state["research_selected_session"] = selected
    session = service.get_session(selected)
    st.markdown(f"**Question:** {session['question']}")
    evidence = []
    if session.get("evidence_path"):
        try:
            evidence = service.load_evidence(session)
            st.caption(f"Evidence: {len(evidence)} references · set `{session.get('evidence_set_hash')}`")
            with st.expander("Evidence sources", expanded=False):
                for ref in evidence:
                    title = ref.get("title") or ref.get("locator", {}).get("value")
                    link = f" · [{ref['canonical_url']}]({ref['canonical_url']})" if ref.get("canonical_url") else ""
                    st.markdown(f"- `{ref['evidence_id']}` · {title} · `{ref['artifact_id']}`{link}")
        except ValueError as exc:
            st.error(str(exc))
    if st.button("Generate research brief", type="primary", disabled=not evidence,
                 key=f"research-generate-{selected}"):
        with st.spinner("Generating a cited brief from the frozen evidence packet…"):
            result = service.generate(selected)
        if result["status"] == "synthesis_unavailable":
            st.warning(f"Synthesis unavailable ({result.get('reason')}). The local evidence packet is ready.")
        else:
            st.success(f"Draft revision {result['revision']} saved privately.")
        st.rerun()
    try:
        brief = service.get_brief(selected)
        if brief.get("evidence_set_hash") != session.get("evidence_set_hash"):
            st.warning("当前 EvidenceSet 已变化；旧 brief 只保留为历史修订，请重新生成后再 review 或 preview。")
            brief = None
        else:
            st.markdown(render_brief_markdown(brief, evidence))
            st.json(brief["metrics"])
    except ValueError:
        brief = None

    reviewer = st.text_input("Reviewer name", key=f"research-reviewer-{selected}")
    if brief and session["status"] in {"synthesized", "reviewed"}:
        if st.button("Mark reviewed", key=f"research-review-{selected}"):
            try:
                service.review(selected, reviewer=reviewer)
                st.success("Review recorded; approval remains a separate action.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    if brief:
        target = st.text_input("Hugo target (relative Markdown path)", key=f"research-target-{selected}")
        if st.button("Create private promotion preview", disabled=not target,
                     key=f"research-preview-{selected}"):
            try:
                preview = service.promotion_preview(selected, target=target)
                st.session_state["research_preview"] = preview["preview_path"]
                st.session_state["research_preview_target"] = target.replace("\\", "/")
                st.session_state["research_preview_session"] = selected
                st.session_state["research_preview_eligible"] = bool(preview["gate"]["eligible"])
            except (ValueError, OSError) as exc:
                st.error(str(exc))
        preview_path = st.session_state.get("research_preview")
        has_current_preview = (st.session_state.get("research_preview_session") == selected
                               and preview_path and Path(preview_path).exists())
        if has_current_preview:
            st.markdown(f"Preview target: `{st.session_state['research_preview_target']}` · "
                        f"eligible: `{st.session_state.get('research_preview_eligible', False)}`")
            st.code(Path(preview_path).with_suffix(".md").read_text(encoding="utf-8"), language="markdown")
        if brief and session["status"] == "reviewed":
            st.warning("检查上方完整预览与来源后，再单独批准。")
            if st.button("Approve for Hugo", key=f"research-approve-{selected}",
                          disabled=not has_current_preview or not st.session_state.get("research_preview_eligible", False)):
                try:
                    service.approve(selected, approver=reviewer)
                    st.success("Explicit approval recorded.")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        if session["status"] == "approved" and has_current_preview:
            if st.button("Promote approved brief to Hugo", key=f"research-promote-{selected}"):
                try:
                    result = service.promote(selected, target=st.session_state["research_preview_target"])
                    st.success(f"{result['status']}: {result['target']}")
                    st.rerun()
                except (ValueError, OSError) as exc:
                    st.error(str(exc))


def main():
    st.set_page_config(page_title="Research Intelligence · Today", page_icon="🧭", layout="wide")
    st.title("Personal Research Intelligence")
    st.caption("本地个人研究信息流 · deterministic feed-v0")
    repository = FeedRepository(PRIVATE_DIR)
    store = JsonlStore(STORE_DIR)
    profile = repository.load_profile()
    projection = project_feedback(repository.all_feedback())
    topic_names, source_names, catalog_sources = _catalogs()
    page = st.sidebar.radio("页面", ["Today", "Saved", "Research", "Profile", "Sources", "Social", "Stats", "Ops"],
                            key="page")

    if page == "Social":
        st.header("Social acquisition")
        st.caption("仅在你明确点击同步时使用已打开的 Chrome 标签页；登录验证和安全挑战会立即停止。")
        with st.form("social_add_url", clear_on_submit=True):
            pasted = st.text_input("公开的小红书笔记或知乎回答/作者 URL")
            add = st.form_submit_button("加入私有收件箱")
        if add and pasted.strip():
            try:
                added = add_social_url(pasted, private_root=ROOT / "data" / "intelligence" / "private")
                st.success(f"已加入 {added['platform']} 收件箱。")
            except ValueError as exc:
                st.error(str(exc))
        pending = [row for row in SocialInbox(ROOT / "data" / "intelligence" / "private").list()
                   if row.get("status") == "pending"]
        left, right = st.columns([3, 1])
        with left:
            st.subheader(f"待处理 URL · {len(pending)}")
            for row in pending[:30]:
                st.write(f"{row['platform']} · {row['url']}")
        with right:
            if st.button("同步收件箱", disabled=not pending, type="primary"):
                with st.spinner("正在使用当前 Chrome 标签页…"):
                    result = _locked(lambda: sync_inbox(
                        store, RUNTIME_DIR, ROOT / "data" / "intelligence" / "private", limit=10,
                    ))
                if result is not None:
                    st.json(result)
        st.subheader("交互式来源")
        health = ops_status(store_dir=STORE_DIR, runtime_dir=RUNTIME_DIR, mode=FEED_MODE)
        social_health = {str(row["source_id"]): row for row in health["source_health"]
                         if row.get("acquisition_mode") == "interactive"}
        interactive_sources = [row for row in load_merged_source_catalog()
                               if row.get("status") == "active"
                               and (row.get("operations") or {}).get("acquisition_mode") == "interactive"]
        if not interactive_sources:
            st.info("尚无已批准的交互式来源。可先通过来源订阅审批，再在这里触发同步。")
        for source in interactive_sources[:3]:
            status = social_health.get(source["source_id"], {}).get("status", "never_synced")
            with st.container(border=True):
                st.markdown(f"**{source['name']}** · `{source['platform']}` · `{status}`")
                if st.button("同步此来源", key=f"social-sync-{source['source_id']}"):
                    with st.spinner("正在使用当前 Chrome 标签页…"):
                        result = _locked(lambda: sync_source(source, store, RUNTIME_DIR, limit=10))
                    if result is not None:
                        st.json(result)
    elif page == "Today":
        health = _freshness_banner()
        picked_date = st.date_input("Feed date", value=date.today())
        left, right = st.columns([1, 4])
        with left:
            refresh = st.button("Refresh today's Feed" if health.get("feed_refresh_pending")
                                else "Refresh revision", type="primary")
        run = _locked(lambda: daily_feed(STORE_DIR, RUNTIME_DIR, PRIVATE_DIR,
                                         date=picked_date.isoformat(), refresh=refresh,
                                         dense_enabled=False,
                                         lock_timeout_seconds=5.0))
        if run is None:
            return
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
                _locked(lambda: apply_feedback(repository, store, feed_run_id=run["feed_run_id"],
                                               artifact_id=item["artifact_id"], action="impression"))
                cols = st.columns(7)
                actions = [("Useful", "useful"), ("Not relevant", "not_relevant"),
                           ("Save", "save"), ("Hide", "hide")]
                for col, (label, action) in zip(cols[:4], actions):
                    with col:
                        if st.button(label, key=f"{run['feed_run_id']}-{item['artifact_id']}-{action}"):
                            if _locked(lambda: _record_and_refresh(repository, store, run, item, action)) is not None:
                                st.rerun()
                with cols[4]:
                    source_id = next(iter(item.get("source_ids", [])), None)
                    if source_id and st.button("Less source", key=f"{run['feed_run_id']}-{item['artifact_id']}-source"):
                        if _locked(lambda: _record_and_refresh(repository, store, run, item, "show_less_from_source", target_id=source_id)) is not None:
                            st.rerun()
                with cols[5]:
                    topic_id = next(iter(item.get("topics", [])), None)
                    if topic_id and st.button("Less topic", key=f"{run['feed_run_id']}-{item['artifact_id']}-topic"):
                        if _locked(lambda: _record_and_refresh(repository, store, run, item, "show_less_of_topic", target_id=topic_id)) is not None:
                            st.rerun()
                with cols[6]:
                    st.button("Research this", key=f"{run['feed_run_id']}-{item['artifact_id']}-research",
                              on_click=_research_from_artifact, args=(item["artifact_id"],),
                              kwargs={"feed_run_id": run["feed_run_id"]})
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
                st.button("Research this", key=f"saved-research-{artifact_id}",
                          on_click=_research_from_artifact, args=(artifact_id,),
                          kwargs={"feed_run_id": run["feed_run_id"]})
                if st.button("Unsave", key=f"unsave-{artifact_id}"):
                    if _locked(lambda: apply_feedback(repository, store, feed_run_id=run["feed_run_id"],
                                                      artifact_id=artifact_id, action="unsave")) is not None:
                        st.rerun()
        if not saved_ids: st.info("还没有保存的内容。")
    elif page == "Research":
        _render_research_page()
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
            updated = _locked(lambda: mutate_profile(repository, add={
                "selected_topic_ids": selected_topics, "followed_source_ids": followed_sources,
                "blocked_topic_ids": blocked_topics, "blocked_source_ids": blocked_sources,
            }, remove={
                "selected_topic_ids": [x for x in profile["selected_topic_ids"] if x not in selected_topics],
                "followed_source_ids": [x for x in profile["followed_source_ids"] if x not in followed_sources],
                "blocked_topic_ids": [x for x in profile["blocked_topic_ids"] if x not in blocked_topics],
                "blocked_source_ids": [x for x in profile["blocked_source_ids"] if x not in blocked_sources],
            }))
            if updated is None:
                return
            if updated != profile:
                refreshed = _locked(lambda: daily_feed(
                    STORE_DIR, RUNTIME_DIR, PRIVATE_DIR, date=date.today().isoformat(), refresh=True,
                    dense_enabled=False, lock_timeout_seconds=5.0))
                if refreshed is None:
                    return
            st.success(f"Profile saved · version {updated['version']} · {profile_hash(updated)[:12]}")
            st.rerun()
        st.caption(f"Profile v{profile['version']} · {profile_hash(profile)}")
    elif page == "Sources":
        from scripts.intelligence.discovery.source_candidates import SourceCandidateStore
        from scripts.intelligence.discovery.source_proposals import (
            PROPOSAL_PATH, SUBSCRIPTION_PATH, SourceProposalStore,
            SourceSubscriptionRegistry, discover_rss_proposals, source_from_proposal,
        )
        from scripts.intelligence.ops.locks import store_writer_lock

        st.header("Sources")
        st.caption("新 RSS 只从页面声明的 RSS/Atom alternate link 发现。探测有效仍需逐条批准后才会订阅。")
        source_rows = load_merged_source_catalog()
        proposals = SourceProposalStore(PROPOSAL_PATH)
        subscriptions = SourceSubscriptionRegistry(SUBSCRIPTION_PATH)
        active_tab, proposal_tab, rejected_tab, health_tab = st.tabs(
            ["Active", "Proposals", "Rejected", "Health"])
        with active_tab:
            private_ids = {str(row["source_id"]) for row in subscriptions.list()}
            active_rows = [row for row in source_rows if row.get("status") == "active"]
            st.dataframe([{"name": row["name"], "platform": row["platform"],
                           "connector": row["acquisition"]["connector"],
                           "origin": "approved subscription" if row["source_id"] in private_ids else "seed",
                           "url": row["canonical_url"]} for row in active_rows], hide_index=True)
        with proposal_tab:
            if st.button("Discover RSS/Atom proposals", type="primary"):
                def _discover():
                    with store_writer_lock(RUNTIME_DIR, timeout_seconds=5.0):
                        return discover_rss_proposals(
                            SourceCandidateStore(STORE_DIR).iter_candidates(), store.iter_records("entity"),
                            proposals, max_candidates=12)
                found = _locked(_discover)
                if found is not None:
                    st.success(f"Checked source candidates; {len(found)} feed endpoint proposal(s) recorded.")
                    st.rerun()
            pending = proposals.list(status="pending")
            if not pending:
                st.info("No pending RSS proposals. Discovery only proposes standard alternate feed links.")
            for proposal in pending:
                with st.container(border=True):
                    st.subheader(proposal["name"])
                    st.caption(f"Probe: {proposal['probe_status']} · {proposal['probe_detail']} · "
                               f"Candidate: {proposal.get('candidate_id') or 'manual'}")
                    st.caption(f"Topics: {', '.join(proposal.get('topics', [])) or 'none'}")
                    st.write(f"Discovered via: {proposal['discovered_via']}")
                    if proposal.get("evidence_path"):
                        st.json(proposal["evidence_path"])
                    st.code(proposal["canonical_url"])
                    left, middle, right = st.columns(3)
                    if left.button("Approve and subscribe", key=f"approve-{proposal['proposal_id']}",
                                   disabled=proposal["probe_status"] != "valid"):
                        def _approve():
                            with store_writer_lock(RUNTIME_DIR, timeout_seconds=5.0):
                                row = source_from_proposal(proposal)
                                subscriptions.add(row)
                                proposals.review(proposal["proposal_id"], "approved")
                                return row
                        approved = _locked(_approve)
                        if approved is not None:
                            st.success(f"Subscribed: {approved['name']}")
                            st.rerun()
                    if middle.button("Reject", key=f"reject-{proposal['proposal_id']}"):
                        _locked(lambda: proposals.review(proposal["proposal_id"], "rejected",
                                                         reason_code="human_rejected"))
                        st.rerun()
                    if right.button("Defer", key=f"defer-{proposal['proposal_id']}"):
                        _locked(lambda: proposals.review(proposal["proposal_id"], "deferred"))
                        st.rerun()
        with rejected_tab:
            rejected = proposals.list(status="rejected")
            if rejected:
                st.dataframe([{"name": row["name"], "url": row["canonical_url"],
                               "reason": row.get("reason_code"), "reviewed_at": row.get("reviewed_at")}
                              for row in rejected], hide_index=True)
            else:
                st.info("No rejected source proposals.")
        with health_tab:
            health = ops_status(store_dir=STORE_DIR, runtime_dir=RUNTIME_DIR, mode=FEED_MODE)
            st.dataframe(health.get("source_health", []), hide_index=True)
    elif page == "Stats":
        st.header("Stats")
        st.json(feedback_stats(store, repository))
    else:
        st.header("Operations")
        status = ops_status(store_dir=STORE_DIR, runtime_dir=RUNTIME_DIR, mode=FEED_MODE)
        pipeline = status.get("latest_pipeline")
        st.caption(f"Environment: {FEED_MODE} · active sources: {status['active_sources']} · "
                   f"healthy: {status['healthy_sources']} · deferred: {status['deferred_sources']} · "
                   f"stale: {status['stale_sources']} · failing: {status['failed_sources']}")
        if pipeline:
            st.write("Latest pipeline")
            st.json({key: pipeline.get(key) for key in (
                "run_id", "run_date", "attempt", "status", "started_at", "finished_at",
                "corpus_hash_before", "corpus_hash_after", "feed_run_id", "feed_refresh_pending",
                "source_summary", "feed_metrics", "source_health")})
            st.write("Stages")
            st.json(pipeline.get("stages", []))
        else:
            st.info("Daily pipeline 尚未运行。")
        st.write("Source health")
        st.dataframe(status.get("source_health", []), hide_index=True)
        st.code("python -m scripts.intelligence.cli intelligence-daily --mode production --force", language="powershell")


if __name__ == "__main__":
    main()
