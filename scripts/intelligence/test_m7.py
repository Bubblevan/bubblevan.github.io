from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from .bridge_xhs import bridge_xhs
from .bridge_zhihu import bridge_zhihu
from .connectors.base import ConnectorCheckpoint, ConnectorContext, ConnectorFailure, ConnectorSpec, FetchResult
from .connectors.openalex_works import probe_openalex_query
from .connectors.state import ConnectorStateStore
from .coverage.report import source_coverage
from .discovery.source_proposals import SourceProbeResult, SourceProposalStore, source_from_proposal
from .models import new_source
from .ops.health import source_health
from .retrieval.corpus import CorpusSnapshot
from .retrieval.manifest import dense_freshness
from .schema_validator import validate_record
from .social.base import BrowserStatus, SocialItem
from .social.chrome_use_driver import ChromeUseDriver
from .social.runner import (add_social_url, normalize_social_url, propose_zhihu_rsshub,
                            sync_urls)
from .social.storage import SocialInbox, SocialRuntime
from .social.xiaohongshu import XiaohongshuAcquirer, _xhs_status, canonical_xhs_url
from .social.zhihu import ZhihuAcquirer, _status as zhihu_status, canonical_zhihu_url
from .store import JsonlStore
from .connectors.registry import ConnectorRegistry
from .runner import run_all_sources


NOW = "2026-09-30T00:00:00Z"
ZH_URL = "https://www.zhihu.com/question/2071486982732223991/answer/2071745067723776921"
XHS_URL = "https://www.xiaohongshu.com/explore/6a42a097000000000f02b56f"


class FakeConnector:
    spec = ConnectorSpec("m7-fake", "1", ("api",), frozenset({"pull"}))

    def __init__(self):
        self.calls: list[str] = []

    def fetch(self, source, checkpoint, context):
        self.calls.append(str(source["name"]))
        if source["name"] == "broken":
            raise ConnectorFailure(cause_class="OfflineFailure")
        return FetchResult([], ConnectorCheckpoint(last_success_at=NOW), True, {"pages": 1})


def source(name: str, *, identity: str | None = None, platform: str = "test",
           url: str = "", mode: str = "scheduled"):
    return new_source(identity=identity or "m7|" + name, source_type="feed", platform=platform,
                      name=name, canonical_url=url, connector="m7-fake", mode="api",
                      operations={"acquisition_mode": mode})


def note_record(note_id: str = "6a42a097000000000f02b56f") -> dict:
    return {"ok": True, "note_id": note_id,
            "canonical_url": f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token=secret-value",
            "url": f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token=secret-value",
            "title": "推荐一个新的 AI 研究方法", "desc": "值得看：arXiv:2601.12345",
            "comments_text": "", "tags": [], "images": [],
            "author": {"user_id": "60a72ded000000000101de6e", "nickname": "Curator"},
            "retrieval": {"mode": "browser_assisted"}, "published_at": None}


class M7SocialTests(unittest.TestCase):
    def test_openalex_probe_accepts_explicit_environment_without_leaking_key(self):
        class Client:
            def __init__(self):
                self.request = None

            def get(self, url, headers=None):
                self.request = (url, headers or {})
                return type("Response", (), {"status": 200, "body": b'{"results": []}', "headers": {}})()

        client = Client()
        secret = "m7-only-test-secret"
        result = probe_openalex_query({"topic_ids": ["T10456"]}, http=client, now=NOW,
                                      environment={"OPENALEX_API_KEY": secret})
        self.assertEqual(result.status, "valid")
        self.assertEqual(client.request[1]["Authorization"], f"Bearer {secret}")
        self.assertNotIn(secret, json.dumps(result.__dict__))

    def test_run_all_isolates_a_broken_source_and_skips_interactive_sources(self):
        first = source("good"); broken = source("broken"); third = source("good-after")
        interactive = source("browser", platform="xiaohongshu", url=XHS_URL, mode="interactive")
        connector = FakeConnector()
        with tempfile.TemporaryDirectory() as temp:
            store = JsonlStore(Path(temp) / "events")
            result = run_all_sources([first, broken, third, interactive], ConnectorRegistry([connector]),
                                     ConnectorStateStore(Path(temp) / "runtime"), store,
                                     ConnectorContext(store=store, now=lambda: NOW))
        self.assertEqual(connector.calls, ["good", "broken", "good-after"])
        self.assertEqual((result["sources_total"], result["succeeded"], result["failed"], result["skipped"]),
                         (4, 2, 1, 1))
        self.assertEqual(result["results"][-1]["status"], "skipped")
        self.assertNotIn("xsec_token", json.dumps(result))

    def test_xhs_bridge_is_token_independent_and_materializes_primary_social_post(self):
        source_row, observation = bridge_xhs(note_record())
        validate_record("source", source_row)
        validate_record("observation", observation)
        self.assertEqual(observation["kind"], "recommendation")
        self.assertEqual(observation["provenance"]["retrieval_mode"], "browser_assisted")
        self.assertEqual(observation["provenance"]["collector"], "chrome-use")
        self.assertEqual(observation["urls"], [XHS_URL])
        primary = next(row for row in observation["artifact_candidates"]
                       if row["mention"].get("role") == "primary")
        self.assertEqual(primary["artifact_type"], "social_post")
        self.assertNotIn("secret-value", json.dumps(observation))
        _, replay = bridge_xhs({**note_record(), "url": XHS_URL})
        self.assertEqual(replay["observation_id"], observation["observation_id"])

    def test_zhihu_bridge_materializes_answer_not_question_and_uses_public_member_identity(self):
        answer = {"canonical_url": ZH_URL + "?utm_source=private", "question_id": "2071486982732223991",
                  "answer_id": "2071745067723776921", "question_title": "AI 研究方向如何选择？",
                  "body": "讨论 autonomous research；参见 https://github.com/org/project?tracking=1",
                  "author_name": "Public Author", "author_url": "https://www.zhihu.com/people/public-member",
                  "created_at": NOW, "updated_at": NOW, "links": ["https://arxiv.org/abs/2601.12345?from=zhihu"]}
        source_row, observation = bridge_zhihu(answer)
        validate_record("source", source_row)
        validate_record("observation", observation)
        self.assertEqual(source_row["external_ids"]["zhihu_member_id"], "public-member")
        self.assertEqual(source_row["canonical_url"], "https://www.zhihu.com/people/public-member")
        self.assertEqual(observation["kind"], "discussion")
        primary = next(row for row in observation["artifact_candidates"]
                       if row["mention"].get("role") == "primary")
        self.assertEqual(primary["artifact_type"], "discussion")
        self.assertEqual(primary["canonical_url"], ZH_URL)
        self.assertNotIn("/question/2071486982732223991\"", json.dumps(primary))
        self.assertNotIn("utm_source=private", json.dumps(observation))
        self.assertEqual(observation["provenance"]["source_url"], ZH_URL)

    def test_url_normalization_removes_queries_and_rejects_non_object_routes(self):
        platform, value = normalize_social_url(XHS_URL + "?xsec_token=secret&share=1")
        self.assertEqual(platform, "xiaohongshu")
        self.assertEqual(value, XHS_URL)
        self.assertEqual(canonical_xhs_url("https://www.xiaohongshu.com/discovery/item/abc?token=x"),
                         "https://www.xiaohongshu.com/explore/abc")
        self.assertEqual(canonical_zhihu_url(ZH_URL + "?share=1"), ZH_URL)
        self.assertEqual(canonical_zhihu_url("https://www.zhihu.com/question/12"), "")

    def test_inbox_and_checkpoint_are_private_and_store_no_token_or_page_body(self):
        with tempfile.TemporaryDirectory() as temp:
            added = add_social_url(XHS_URL + "?xsec_token=do-not-store", private_root=Path(temp) / "private")
            inbox_path = Path(temp) / "private" / "social" / "inbox.jsonl"
            inbox_text = inbox_path.read_text(encoding="utf-8")
            self.assertEqual(added["url"], XHS_URL)
            self.assertNotIn("do-not-store", inbox_text)
            self.assertEqual(len(SocialInbox(Path(temp) / "private").list()), 1)
            runtime = SocialRuntime(Path(temp) / "runtime")
            source_id = "src-" + "a" * 24
            value = runtime.load(source_id, "xiaohongshu")
            value.update({"last_status": "completed", "last_success_at": NOW,
                          "last_seen_object_ids": ["6a42a097000000000f02b56f"],
                          "last_run": {"fetched": 1, "new_observations": 1,
                                       "duplicate_observations": 0, "artifacts_touched": 1,
                                       "pages": 1, "login_required": 0,
                                       "challenge_required": 0, "dom_changed": 0}})
            runtime.save(value)
            saved = (Path(temp) / "runtime" / "social" / f"{source_id}.json").read_text(encoding="utf-8")
            self.assertNotIn("cookie", saved.casefold())
            self.assertNotIn("https://", saved)
            self.assertNotIn("page body", saved)

    def test_chrome_driver_passes_shell_false_and_a_bounded_timeout(self):
        calls = []
        def runner(args, **kwargs):
            calls.append((args, kwargs))
            kwargs["stdout"].write('{"data":{"relayUp":true}}')
            return subprocess.CompletedProcess(args, 0)
        driver = ChromeUseDriver(executable="chrome-use.exe", timeout_seconds=900, runner=runner)
        self.assertTrue(driver.status()["relay_up"])
        self.assertIs(calls[0][1]["shell"], False)
        self.assertEqual(calls[0][1]["timeout"], 60)
        self.assertEqual(calls[0][0][-1], "status")
        self.assertNotIn("capture_output", calls[0][1])

    def test_chrome_driver_uses_full_tab_identity_but_strips_url_secrets(self):
        driver = ChromeUseDriver(executable="chrome-use.exe", runner=lambda args, **kwargs: None)
        calls = []
        def run(args):
            calls.append(args)
            return {"success": True, "data": {"tabs": [{
                "tabId": "t1", "targetId": "target-1", "ownership": "adopted",
                "url": "https://www.xiaohongshu.com/explore/abc?xsec_token=private",
            }]}}
        with patch.object(driver, "_run", side_effect=run):
            tabs = driver.tabs()
        self.assertIn(["tab", "list", "--full"], calls)
        self.assertEqual(tabs[0]["url"], "https://www.xiaohongshu.com/explore/abc")
        self.assertNotIn("private", repr(tabs))

    def test_chrome_driver_pins_the_user_selected_browser_profile(self):
        from .social import chrome_use_driver
        calls = []
        def runner(args, **kwargs):
            calls.append(args)
            kwargs["stdout"].write('{"data":{"relayUp":true}}')
            return subprocess.CompletedProcess(args, 0)
        with patch.object(chrome_use_driver, "environment_value",
                   side_effect=lambda name: "profile-fixture" if name == "CHROME_USE_BROWSER" else ""):
            driver = ChromeUseDriver(executable="chrome-use.exe", runner=runner)
        driver._run(["open", "https://example.org"])
        self.assertEqual(calls[0][-2:], ["--browser", "profile-fixture"])

    def test_chrome_driver_reuses_the_selected_session_and_avoids_browser_flag_on_status(self):
        from .social import chrome_use_driver
        calls = []
        def runner(args, **kwargs):
            calls.append(args)
            kwargs["stdout"].write('{"data":{"relayUp":true}}')
            return subprocess.CompletedProcess(args, 0)
        def setting(name):
            return {"CHROME_USE_SESSION": "default"}.get(name, "")
        with patch.object(chrome_use_driver, "environment_value", side_effect=setting):
            driver = ChromeUseDriver(executable="chrome-use.exe", runner=runner)
        self.assertTrue(driver.status()["relay_up"])
        self.assertEqual(calls[0], ["chrome-use.exe", "--json", "--session", "default", "status"])

    def test_chrome_driver_can_adopt_an_existing_zhihu_column_tab_for_answer_navigation(self):
        driver = ChromeUseDriver(executable="chrome-use.exe", runner=lambda args, **kwargs:
                                 subprocess.CompletedProcess(args, 0, stdout="{}", stderr=""))
        rows = [{"tab_id": "t9", "target_id": "target-9",
                 "url": "https://zhuanlan.zhihu.com/p/2078061173409432156", "ownership": "foreign"}]
        with patch.object(driver, "status", return_value={"relay_up": True}), \
                patch.object(driver, "tabs", side_effect=[rows, [{**rows[0], "ownership": "adopted"}]]):
            selected = driver.adopt_tab("zhihu")
        self.assertEqual(selected["tab_id"], "t9")
        self.assertEqual(driver.target_id, "target-9")

    def test_chrome_driver_can_navigate_a_tab_created_by_the_same_chrome_use_session(self):
        driver = ChromeUseDriver(executable="chrome-use.exe", runner=lambda args, **kwargs:
                                 subprocess.CompletedProcess(args, 0))
        row = {"tab_id": "t1", "target_id": "target-1",
               "url": "https://zhuanlan.zhihu.com/p/2078061173409432156", "ownership": "created"}
        driver.tab_id, driver.target_id = row["tab_id"], row["target_id"]
        calls = []
        with patch.object(driver, "tabs", side_effect=[[row], [row]]), \
                patch.object(driver, "_run", side_effect=lambda args, **kwargs: calls.append(args) or {}):
            driver.navigate_selected_tab("https://www.zhihu.com/question/1/answer/2")
        self.assertEqual(calls[0], ["tab", "select", "t1"])
        self.assertEqual(calls[1], ["open", "https://www.zhihu.com/question/1/answer/2"])

    def test_chrome_driver_finds_installed_windows_cli_when_sandbox_path_omits_it(self):
        from .social import chrome_use_driver
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "chrome-use.exe"
            binary.write_bytes(b"fixture")
            with patch.object(chrome_use_driver, "environment_value", return_value=None), \
                    patch.object(chrome_use_driver.shutil, "which", return_value=None), \
                    patch.object(chrome_use_driver, "_windows_default_path", return_value=binary):
                self.assertEqual(ChromeUseDriver().executable, str(binary))

    def test_login_challenge_and_rendered_login_modal_statuses(self):
        self.assertEqual(_xhs_status({"ok": False}, {"login_page": True}), BrowserStatus.LOGIN_REQUIRED)
        self.assertEqual(_xhs_status({"ok": False, "error_code": "CAPTCHA_CHALLENGE"}, {}),
                         BrowserStatus.CHALLENGE_REQUIRED)
        self.assertEqual(_xhs_status({"ok": True, "note_id": "a", "canonical_url": XHS_URL,
                                     "title": "visible body"}, {}), BrowserStatus.CONTENT_READABLE)
        self.assertEqual(zhihu_status({"login_page": True}), BrowserStatus.LOGIN_REQUIRED)
        self.assertEqual(zhihu_status({"challenge": True}), BrowserStatus.CHALLENGE_REQUIRED)
        self.assertEqual(zhihu_status({"login_page": False, "question_title": "q", "body": "rendered answer"}),
                         BrowserStatus.CONTENT_READABLE)
        self.assertEqual(_xhs_status({"ok": True, "note_id": "6a42a097000000000f02b56f",
                                      "url": XHS_URL, "title": "parsed note"}, {}),
                         BrowserStatus.CONTENT_READABLE)

    def test_zhihu_acquirer_closes_a_visible_login_overlay_before_extracting(self):
        class FakeDriver:
            def __init__(self): self.clicked = []
            def navigate_selected_tab(self, url): self.url = url
            def snapshot(self):
                return {"data": {"refs": {"e1": {"role": "button", "name": "密码登录"}}}}
            def click_role(self, role, name): self.clicked.append((role, name))
            def eval_json(self, script):
                return {"question_id": "2071486982732223991", "answer_id": "2071745067723776921",
                        "question_title": "AI 研究方向如何选择？", "body": "公开回答正文",
                        "author_name": "", "author_url": "", "created_at": "", "updated_at": "",
                        "links": [], "login_page": False, "challenge": False, "not_found": False}
        driver = FakeDriver()
        item = ZhihuAcquirer(driver).acquire(ZH_URL)
        self.assertEqual(driver.clicked, [("button", "关闭")])
        self.assertEqual(item.status, BrowserStatus.CONTENT_READABLE)
        self.assertEqual(item.record["body"], "公开回答正文")

    def test_xhs_acquirer_keeps_an_existing_signed_note_tab_without_persisting_its_query(self):
        class FakeDriver:
            def __init__(self): self.navigations = []
            def selected_tab_url(self): return XHS_URL
            def navigate_selected_tab(self, url): self.navigations.append(url)
            def snapshot(self): return {}
            def eval_json(self, script): return {"note_id": "6a42a097000000000f02b56f"}
        driver = FakeDriver()
        parsed = {"ok": True, "note_id": "6a42a097000000000f02b56f",
                  "canonical_url": XHS_URL, "title": "AI note", "desc": "public body"}
        with patch("scripts.tools.xhs_chrome_use._safe_note_extractor_js", return_value="fixed extractor"), \
                patch("scripts.tools.xhs_note_parser.parse_rendered_snapshot", return_value=parsed):
            item = XiaohongshuAcquirer(driver).acquire(XHS_URL)
        self.assertEqual(driver.navigations, [])
        self.assertEqual(item.canonical_url, XHS_URL)
        self.assertEqual(item.status, BrowserStatus.CONTENT_READABLE)
        self.assertNotIn("xsec_token", json.dumps(item.record))

    def test_xhs_profile_discovery_returns_only_canonical_note_paths(self):
        class FakeDriver:
            def __init__(self): self.navigations = []; self.eval_results = []
            def navigate_selected_tab(self, url): self.navigations.append(url)
            def eval_json(self, script): return self.eval_results.pop(0)
            def selected_tab_url(self): return "https://www.xiaohongshu.com/user/profile/60a72ded000000000101de6e"
            def click_selector(self, selector): self.selector = selector
            def snapshot(self): return {}
            def _run(self, args): return {}
        driver = FakeDriver()
        driver.eval_results = [[XHS_URL + "?xsec_token=unit-secret"]]
        acquirer = XiaohongshuAcquirer(driver)
        profile = "https://www.xiaohongshu.com/user/profile/60a72ded000000000101de6e"
        found = acquirer.discover(profile, limit=1)
        self.assertEqual(found, {"status": BrowserStatus.READY, "urls": [XHS_URL]})
        self.assertEqual(acquirer._profile_url, profile)
        self.assertNotIn("unit-secret", json.dumps(found))

    def test_xhs_profile_acquisition_clicks_by_note_id_instead_of_opening_signed_url(self):
        class FakeDriver:
            def __init__(self): self.navigations = []; self.eval_results = []; self.clicks = []
            def navigate_selected_tab(self, url): self.navigations.append(url)
            def eval_json(self, script): return self.eval_results.pop(0)
            def selected_tab_url(self): return "https://www.xiaohongshu.com/user/profile/60a72ded000000000101de6e"
            def click_selector(self, selector): self.clicks.append(selector)
            def snapshot(self): return {}
            def _run(self, args): return {}
        driver = FakeDriver()
        driver.eval_results = [[XHS_URL + "?xsec_token=unit-secret"],
                               {"note_id": "6a42a097000000000f02b56f"}]
        acquirer = XiaohongshuAcquirer(driver)
        profile = "https://www.xiaohongshu.com/user/profile/60a72ded000000000101de6e"
        parsed = {"ok": True, "note_id": "6a42a097000000000f02b56f",
                  "url": XHS_URL, "title": "AI note", "desc": "public body"}
        with patch("scripts.tools.xhs_chrome_use._safe_note_extractor_js", return_value="fixed extractor"), \
                patch("scripts.tools.xhs_note_parser.parse_rendered_snapshot", return_value=parsed):
            found = acquirer.discover(profile, limit=1)
            item = acquirer.acquire(found["urls"][0])
        self.assertEqual(driver.clicks, ['a[href*="/explore/6a42a097000000000f02b56f"]'])
        self.assertNotIn("unit-secret", json.dumps(driver.clicks))
        self.assertNotIn(XHS_URL, driver.navigations)
        self.assertEqual(item.status, BrowserStatus.CONTENT_READABLE)

    def test_rsshub_is_optional_and_valid_proposals_require_approval(self):
        profile = "https://www.zhihu.com/people/public-member"
        with patch.dict(os.environ, {"RSSHUB_BASE_URL": ""}):
            absent = propose_zhihu_rsshub(profile, environment={})
        self.assertEqual(absent, {"status": "unavailable", "detail": "rsshub_unconfigured"})
        with patch.dict(os.environ, {"RSSHUB_BASE_URL": ""}):
            unsafe = propose_zhihu_rsshub(profile, environment={"RSSHUB_BASE_URL": "https://feed.example/base?token=secret"})
        self.assertEqual(unsafe["status"], "unavailable")
        from .social import runner as social_runner
        with tempfile.TemporaryDirectory() as temp:
            store = SourceProposalStore(Path(temp) / "proposals.jsonl")
            with patch.object(social_runner, "probe_rss_endpoint",
                              return_value=SourceProbeResult("auth_required", "http_auth_required", "https://feed.example/route", 0)):
                deferred = propose_zhihu_rsshub(profile,
                    environment={"RSSHUB_BASE_URL": "https://feed.example"}, proposals=store)
            self.assertEqual(deferred["status"], "deferred")
            self.assertEqual(store.list()[0]["status"], "deferred")
            store.path.unlink()
            with patch.object(social_runner, "probe_rss_endpoint",
                              return_value=SourceProbeResult("valid", "feed_valid", "https://feed.example/zhihu/answers/member", 2)):
                result = propose_zhihu_rsshub(profile,
                    environment={"RSSHUB_BASE_URL": "https://feed.example"}, proposals=store)
            self.assertEqual(result["status"], "valid")
            proposal = store.list()[0]
            self.assertEqual(proposal["status"], "pending")
            self.assertEqual(proposal["acquisition"]["via"], "rsshub")
            approved = dict(proposal, status="pending")
            source_row = source_from_proposal(approved)
            self.assertEqual(source_row["acquisition"]["via"], "rsshub")
            self.assertEqual(source_row["operations"]["acquisition_mode"], "scheduled")

    def test_interactive_source_health_and_coverage_do_not_fabricate_polls(self):
        interactive = source("XHS curator", platform="xiaohongshu", url=XHS_URL, mode="interactive")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            empty = source_health(runtime_dir=root / "runtime", now=NOW, sources=[interactive])
            self.assertEqual(empty["never_synced"], 1)
            self.assertEqual(empty["never_run"], 0)
            checkpoint = SocialRuntime(root / "runtime").load(interactive["source_id"], "xiaohongshu")
            checkpoint.update({"last_success_at": NOW, "last_status": "completed",
                               "last_seen_object_ids": ["abc123"], "consecutive_failures": 0,
                               "last_run": {"fetched": 1, "new_observations": 1,
                                            "duplicate_observations": 0, "artifacts_touched": 1,
                                            "pages": 1, "login_required": 0,
                                            "challenge_required": 0, "dom_changed": 0}})
            SocialRuntime(root / "runtime").save(checkpoint)
            health = source_health(runtime_dir=root / "runtime", now=NOW, sources=[interactive])
            self.assertEqual(health["interactive_ready"], 1)
            coverage = source_coverage(JsonlStore(root / "events"), root / "runtime", [interactive],
                                       days=7, today="2026-09-30")
            row = coverage["sources"][0]
            self.assertEqual(row["polls"], 0)
            self.assertEqual(row["new_items"], 1)
            self.assertEqual(row["last_interactive_status"], "completed")

    def test_dense_freshness_distinguishes_missing_stale_and_fresh(self):
        snapshot = CorpusSnapshot((), "a" * 64, "tree")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(dense_freshness(snapshot, root)["dense_status"], "missing")
            manifest = root / "retrieval" / "dense" / "manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(json.dumps({"corpus_hash": "b" * 64}), encoding="utf-8")
            self.assertEqual(dense_freshness(snapshot, root)["dense_status"], "stale")
            manifest.write_text(json.dumps({"corpus_hash": snapshot.corpus_hash}), encoding="utf-8")
            self.assertEqual(dense_freshness(snapshot, root)["dense_status"], "fresh")

    def test_social_sync_replays_same_note_without_duplicate_observation(self):
        class Driver:
            def adopt_tab(self, platform):
                self.platform = platform

        class Adapter:
            platform = "xiaohongshu"
            def __init__(self):
                self.calls = 0
            def acquire(self, url):
                self.calls += 1
                value = note_record()
                return SocialItem(self.platform, value["note_id"], XHS_URL, value)

        from .social import runner as social_runner
        adapter = Adapter()
        catalog_source = source("XHS note", platform="xiaohongshu", url=XHS_URL, mode="interactive")
        with tempfile.TemporaryDirectory() as temp, patch.object(social_runner, "_adapter", return_value=adapter):
            store = JsonlStore(Path(temp) / "events")
            first = sync_urls(catalog_source, [XHS_URL], store, Path(temp) / "runtime", driver=Driver())
            second = sync_urls(catalog_source, [XHS_URL], store, Path(temp) / "runtime", driver=Driver())
            self.assertEqual(first["new_observations"], 1)
            self.assertEqual(second["new_observations"], 0)
            self.assertEqual(second["duplicate_observations"], 1)
            observations = list(store.iter_records("observation"))
            self.assertEqual(len(observations), 1)
            artifacts = list(store.iter_records("artifact"))
            self.assertTrue(any(item["artifact_type"] == "social_post" for item in artifacts))
            self.assertEqual(adapter.calls, 2)


if __name__ == "__main__":
    unittest.main()
