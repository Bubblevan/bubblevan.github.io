from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from scripts.tools import xhs_chrome_use, xhs_note_parser, xhs_note_reader
from scripts.tools import xhs_profile_reader


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
NOTE_URL = "https://www.xiaohongshu.com/explore/fixture001"


def fixture_text(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def args_for(url: str = NOTE_URL, *options: str):
    return xhs_note_reader.build_parser().parse_args(["--url", url, *options])


class XhsPureParserTests(unittest.TestCase):
    def test_normal_ssr_initial_state_and_multiple_gallery_images(self) -> None:
        result = xhs_note_parser.parse_html(fixture_text("xhs_initial_state.html"), url=NOTE_URL)

        self.assertTrue(result["ok"])
        self.assertEqual(result["note_id"], "fixture001")
        self.assertEqual(result["title"], "Synthetic multi-image note")
        self.assertEqual(result["author"]["nickname"], "Fixture Author")
        self.assertEqual(result["tags"], ["synthetic", "parser-test"])
        self.assertEqual(result["stats"]["likes"], "12")
        self.assertEqual(result["gallery"]["image_count_available"], 3)
        self.assertEqual(len(result["images"]), 3)

    def test_html_js_literal_undefined_nan_and_strings_are_sanitized(self) -> None:
        result = xhs_note_parser.parse_html(
            fixture_text("xhs_js_values.html"),
            url="https://www.xiaohongshu.com/explore/fixture003",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["title"], "String containing the word undefined")
        self.assertEqual(result["desc"], "NaN and undefined remain ordinary text here.")
        self.assertEqual(result["stats"]["likes"], "")
        self.assertEqual(result["stats"]["collects"], "")
        self.assertEqual(len(result["images"]), 1)

    def test_html_json_parse_assignment_is_supported(self) -> None:
        state = {
            "note": {
                "noteDetailMap": {
                    "fixtureJSONParse": {
                        "note": {
                            "noteId": "fixtureJSONParse",
                            "title": "JSON.parse fixture",
                            "desc": "Synthetic escaped state",
                            "imageList": [{"urlDefault": "https://sns-webpic-qc.xhscdn.com/json-parse.jpg"}],
                        }
                    }
                }
            }
        }
        encoded_state = json.dumps(state, ensure_ascii=False)
        html = f"<script>window.__INITIAL_STATE__ = JSON.parse({json.dumps(encoded_state)});</script>"
        result = xhs_note_parser.parse_html(
            html,
            url="https://www.xiaohongshu.com/explore/fixtureJSONParse",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["title"], "JSON.parse fixture")
        self.assertEqual(len(result["images"]), 1)

    def test_runtime_state_accepts_circular_reactive_style_objects(self) -> None:
        state = json.loads((FIXTURE_DIR / "xhs_runtime_state.json").read_text(encoding="utf-8"))
        state["reactive"] = {"dep": state}
        state["reactive"]["computed"] = state["reactive"]

        result = xhs_note_parser.parse_runtime_state(state, url="https://www.xiaohongshu.com/explore/fixture002")

        self.assertTrue(result["ok"])
        self.assertEqual(result["note_id"], "fixture002")
        self.assertEqual(result["title"], "Synthetic runtime-state note")
        self.assertEqual(len(result["images"]), 2)

    def test_missing_note_id_uses_matching_detail_map_key(self) -> None:
        state = {
            "note": {
                "noteDetailMap": {
                    "fixture009": {
                        "note": {
                            "title": "No embedded note ID",
                            "desc": "Map key identifies this record.",
                            "imageList": [{"urlDefault": "https://sns-webpic-qc.xhscdn.com/keyed.jpg"}],
                        }
                    }
                }
            }
        }

        result = xhs_note_parser.parse_runtime_state(state, url="https://www.xiaohongshu.com/explore/fixture009")
        self.assertTrue(result["ok"])
        self.assertEqual(result["note_id"], "fixture009")
        self.assertEqual(result["title"], "No embedded note ID")

    def test_ambiguous_missing_note_id_fails_closed(self) -> None:
        state = {"notes": [
            {"noteId": "first", "title": "First note", "imageList": []},
            {"noteId": "second", "title": "Second note", "imageList": []},
        ]}
        result = xhs_note_parser.parse_runtime_state(state, url="https://www.xiaohongshu.com/share/link")
        self.assertFalse(result["ok"])
        self.assertTrue(result["errors"][0].startswith("NOTE_ID_MISSING"))

    def test_login_shell_and_security_page_are_classified(self) -> None:
        login = xhs_note_parser.parse_html(
            fixture_text("xhs_login_shell.html"),
            url=NOTE_URL,
            final_url="https://www.xiaohongshu.com/login?redirectPath=%2Fexplore%2Ffixture001",
        )
        security = xhs_note_parser.parse_html(
            fixture_text("xhs_security_300011.html"), url=NOTE_URL
        )

        self.assertFalse(login["ok"])
        self.assertTrue(login["errors"][0].startswith("LOGIN_SHELL"))
        self.assertFalse(security["ok"])
        self.assertTrue(security["errors"][0].startswith("SECURITY_RESTRICTED_300011"))

    def test_300011_mentioned_in_note_content_is_not_a_security_page(self) -> None:
        html = fixture_text("xhs_initial_state.html").replace(
            "Offline parser fixture with no user or share data.",
            "Offline parser fixture discussing 300011 as an example.",
        )
        result = xhs_note_parser.parse_html(html, url=NOTE_URL)
        self.assertTrue(result["ok"])

    def test_xsec_token_is_redacted_in_result_urls(self) -> None:
        url = NOTE_URL + "?xsec_token=fixture-secret&xsec_source=share"
        result = xhs_note_parser.parse_html(fixture_text("xhs_initial_state.html"), url=url)
        self.assertTrue(result["ok"])
        self.assertNotIn("fixture-secret", json.dumps(result))
        self.assertIn("%5Bredacted%5D", result["url"])


class XhsAcquisitionRoutingTests(unittest.TestCase):
    def test_state_file_is_offline_and_normalizes_saved_runtime_json(self) -> None:
        static_loader = Mock(side_effect=AssertionError("state-file mode must not fetch HTML"))
        browser_loader = Mock(side_effect=AssertionError("state-file mode must not use Chrome"))
        result = xhs_note_reader.read_note(
            args_for(
                "https://www.xiaohongshu.com/explore/fixture002?xsec_token=secret",
                "--state-file",
                str(FIXTURE_DIR / "xhs_runtime_state.json"),
            ),
            static_loader=static_loader,
            browser_loader=browser_loader,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["retrieval"]["mode"], "saved_runtime_state")
        self.assertEqual(result["note_id"], "fixture002")
        self.assertNotIn("secret", json.dumps(result))
        static_loader.assert_not_called()
        browser_loader.assert_not_called()

    def test_gate_a_cli_reads_state_file_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            out_path = Path(temp_dir) / "note.json"
            exit_code = xhs_note_reader.main(
                [
                    "--url", "https://www.xiaohongshu.com/explore/fixture002",
                    "--state-file", str(FIXTURE_DIR / "xhs_runtime_state.json"),
                    "--out-json", str(out_path),
                ]
            )
            result = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["note_id"], "fixture002")
        self.assertEqual(result["title"], "Synthetic runtime-state note")
        self.assertEqual(result["author"]["nickname"], "Runtime Fixture")
        self.assertEqual(result["tags"], ["offline"])
        self.assertEqual(len(result["images"]), 2)
        self.assertEqual(result["stats"]["likes"], "8")
        self.assertEqual(result["retrieval"]["mode"], "saved_runtime_state")

    def test_state_file_accepts_sanitized_rendered_page_snapshot(self) -> None:
        snapshot = {
            "snapshot_version": 1,
            "note_id": "fixture001",
            "url": "https://www.xiaohongshu.com/explore/fixture001?xsec_token=discard-this",
            "note": {"noteId": "fixture001", "title": "Sanitized page snapshot", "desc": "Snapshot fixture", "imageList": [
                {"urlDefault": "https://sns-webpic-qc.xhscdn.com/snapshot.jpg"}
            ]},
        }
        result = xhs_note_parser.parse_runtime_json(json.dumps(snapshot), url=NOTE_URL)
        self.assertTrue(result["ok"])
        self.assertEqual(result["title"], "Sanitized page snapshot")
        self.assertEqual(result["retrieval"]["mode"], "saved_runtime_state")
        self.assertNotIn("discard-this", json.dumps(result))

    def test_saved_html_mode_is_offline(self) -> None:
        static_loader = Mock(side_effect=AssertionError("saved HTML must not fetch the URL"))
        browser_loader = Mock(side_effect=AssertionError("saved HTML must not use Chrome"))
        with tempfile.TemporaryDirectory() as temp_dir:
            html_path = Path(temp_dir) / "snapshot.html"
            html_path.write_text(fixture_text("xhs_initial_state.html"), encoding="utf-8")
            result = xhs_note_reader.read_note(
                args_for(NOTE_URL, "--html-file", str(html_path)),
                static_loader=static_loader,
                browser_loader=browser_loader,
            )
        self.assertTrue(result["ok"])
        self.assertEqual(result["retrieval"]["mode"], "saved_html")
        static_loader.assert_not_called()
        browser_loader.assert_not_called()

    def test_static_success_never_invokes_chrome_adapter(self) -> None:
        browser_loader = Mock(side_effect=AssertionError("static success must not start browser acquisition"))
        result = xhs_note_reader.read_note(
            args_for(NOTE_URL, "--browser-adapter", "chrome-use"),
            static_loader=lambda _url, timeout: (fixture_text("xhs_initial_state.html"), NOTE_URL),
            browser_loader=browser_loader,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["retrieval"]["mode"], "static_html")
        browser_loader.assert_not_called()

    def test_static_login_shell_uses_chrome_only_when_explicitly_selected(self) -> None:
        snapshot = {
            "snapshot_version": 1,
            "url": NOTE_URL,
            "note_id": "fixture001",
            "note": {"noteId": "fixture001", "title": "Real Chrome result", "desc": "Visible note", "imageList": []},
        }
        browser_loader = Mock(return_value=(snapshot, Path(".cache/xhs-extracted/fixture001-runtime-snapshot.json")))
        result = xhs_note_reader.read_note(
            args_for(NOTE_URL, "--browser-adapter", "chrome-use"),
            static_loader=lambda _url, timeout: (
                fixture_text("xhs_login_shell.html"),
                "https://www.xiaohongshu.com/login?redirectPath=%2Fexplore%2Ffixture001",
            ),
            browser_loader=browser_loader,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["retrieval"]["mode"], "real_chrome")
        self.assertTrue(result["retrieval"]["logged_in"])
        self.assertTrue(result["retrieval"]["used_user_profile"])
        self.assertEqual(result["retrieval"]["browser_automation"], "chrome-use")
        browser_loader.assert_called_once()

    def test_security_error_never_retries_in_chrome(self) -> None:
        browser_loader = Mock(side_effect=AssertionError("security page is a hard stop"))
        result = xhs_note_reader.read_note(
            args_for(NOTE_URL, "--browser-adapter", "chrome-use"),
            static_loader=lambda _url, timeout: (fixture_text("xhs_security_300011.html"), NOTE_URL),
            browser_loader=browser_loader,
        )
        self.assertFalse(result["ok"])
        self.assertTrue(result["errors"][0].startswith("SECURITY_RESTRICTED_300011"))
        browser_loader.assert_not_called()


class ChromeUseAdapterTests(unittest.TestCase):
    def test_extractors_are_read_only_and_profile_gate_is_handled_before_state_walk(self) -> None:
        note_script = xhs_chrome_use._safe_note_extractor_js(NOTE_URL)
        profile_script = xhs_chrome_use._safe_profile_extractor_js(
            "https://www.xiaohongshu.com/user/profile/userfixture"
        )
        self.assertIn("new WeakSet()", note_script)
        self.assertIn("if (pageError) return", note_script)
        self.assertIn("if (pageError) return", profile_script)
        self.assertIn("stateReady || (profileMarker && domCardsReady)", profile_script)
        self.assertIn(
            'const id = text(unwrap(read(raw,["noteId","note_id","id"])) || unwrap(read(entry,["noteId","note_id","id"])))',
            profile_script,
        )
        self.assertNotIn("document.body?.innerText?.length > 200", profile_script)
        for script in (note_script, profile_script):
            self.assertNotIn("localStorage", script)
            self.assertNotIn("document.cookie", script)

    def test_adopts_matching_existing_tab_and_writes_only_sanitized_snapshot(self) -> None:
        calls: list[tuple[list[str], str | None]] = []
        snapshot = {
            "snapshot_version": 1,
            "url": NOTE_URL + "?xsec_token=secret",
            "note_id": "fixture001",
            "note": {"noteId": "fixture001", "title": "Sanitized", "desc": "Fixture", "imageList": []},
        }

        def runner(command, *, input, **_kwargs):
            calls.append((list(command), input))
            operation = command[2:]
            if operation == ["status"]:
                output = json.dumps({"data": {"extension": {"relayUp": True}}, "success": True})
            elif operation == ["tab", "list"]:
                output = json.dumps([{"targetId": "target-fixture", "url": NOTE_URL}])
            elif operation[:2] == ["tab", "adopt"]:
                output = "{}"
            elif operation == ["snapshot", "-i"]:
                output = "{}"
            elif operation == ["eval", "--stdin"]:
                output = json.dumps(json.dumps(snapshot))
            else:
                raise AssertionError(f"unexpected chrome-use command: {operation}")
            return subprocess.CompletedProcess(command, 0, output, "")

        with tempfile.TemporaryDirectory() as temp_dir:
            client = xhs_chrome_use.ChromeUseClient(runner=runner)
            result, path = xhs_chrome_use.acquire_note_snapshot(
                NOTE_URL + "?xsec_token=secret",
                cache_dir=Path(temp_dir),
                client=client,
            )
            saved = path.read_text(encoding="utf-8")

        operations = [call[0][2:] for call in calls]
        self.assertEqual(operations, [["status"], ["tab", "list"], ["tab", "adopt", "target-fixture"], ["snapshot", "-i"], ["eval", "--stdin"]])
        self.assertEqual(result["note"]["title"], "Sanitized")
        self.assertNotIn("secret", saved)
        self.assertNotIn("--user-data-dir", json.dumps([call[0] for call in calls]))
        self.assertNotIn("--launch", json.dumps([call[0] for call in calls]))
        extractor_script = calls[-1][1] or ""
        self.assertIn("new WeakSet()", extractor_script)
        self.assertNotIn("localStorage", extractor_script)
        self.assertNotIn("document.cookie", extractor_script)

    def test_opens_target_in_existing_chrome_when_no_matching_tab_exists(self) -> None:
        calls: list[list[str]] = []

        def runner(command, *, input, **_kwargs):
            calls.append(list(command))
            operation = command[2:]
            if operation == ["status"]:
                output = json.dumps({"data": {"extension": {"relayUp": True}}, "success": True})
            elif operation == ["tab", "list"]:
                output = json.dumps([{"targetId": "tab-other", "url": "https://example.com/"}])
            elif operation[:1] == ["open"]:
                output = "{}"
            elif operation == ["snapshot", "-i"]:
                output = "{}"
            elif operation == ["eval", "--stdin"]:
                output = json.dumps(json.dumps({"snapshot_version": 1, "url": NOTE_URL, "note_id": "fixture001", "note": {"title": "Open result", "imageList": []}}))
            else:
                raise AssertionError(f"unexpected command {operation}")
            return subprocess.CompletedProcess(command, 0, output, "")

        with tempfile.TemporaryDirectory() as temp_dir:
            client = xhs_chrome_use.ChromeUseClient(runner=runner)
            xhs_chrome_use.acquire_note_snapshot(NOTE_URL, cache_dir=Path(temp_dir), client=client)

        operations = [command[2:] for command in calls]
        self.assertEqual(operations[:3], [["status"], ["tab", "list"], ["open", NOTE_URL]])
        self.assertNotIn("--user-data-dir", json.dumps(calls))
        self.assertNotIn("--launch", json.dumps(calls))

    def test_disconnected_relay_fails_before_tab_list_or_open(self) -> None:
        calls: list[list[str]] = []

        def runner(command, **_kwargs):
            calls.append(list(command))
            operation = command[2:]
            if operation == ["status"]:
                output = json.dumps({"data": {"extension": {"relayUp": False}}, "success": True})
            else:
                raise AssertionError(f"disconnected relay must fail before {operation}")
            return subprocess.CompletedProcess(command, 0, output, "")

        client = xhs_chrome_use.ChromeUseClient(runner=runner)
        with self.assertRaisesRegex(xhs_chrome_use.ChromeUseError, "refusing to start"):
            client.eval_json(NOTE_URL, "document.title")
        self.assertEqual([call[2:] for call in calls], [["status"], ["status"]])

    def test_rechecks_a_transiently_disconnected_relay_once(self) -> None:
        calls: list[list[str]] = []

        def runner(command, *, input, **_kwargs):
            calls.append(list(command))
            operation = command[2:]
            if operation == ["status"]:
                relay_up = len([call for call in calls if call[2:] == ["status"]]) > 1
                output = json.dumps({"data": {"extension": {"relayUp": relay_up}}, "success": True})
            elif operation == ["tab", "list"]:
                output = json.dumps([{"targetId": "transient-tab", "url": NOTE_URL}])
            elif operation[:2] == ["tab", "adopt"] or operation == ["snapshot", "-i"]:
                output = "{}"
            elif operation == ["eval", "--stdin"]:
                output = json.dumps(json.dumps({
                    "snapshot_version": 1,
                    "url": NOTE_URL,
                    "note_id": "fixture001",
                    "note": {"title": "Recovered after relay recheck", "imageList": []},
                }))
            else:
                raise AssertionError(f"unexpected command: {operation}")
            return subprocess.CompletedProcess(command, 0, output, "")

        client = xhs_chrome_use.ChromeUseClient(runner=runner)
        result = client.eval_json(NOTE_URL, "document.title")
        self.assertEqual(result["note"]["title"], "Recovered after relay recheck")
        self.assertEqual([call[2:] for call in calls[:3]], [["status"], ["status"], ["tab", "list"]])

    def test_profile_adapter_adopts_existing_tab_and_saves_redacted_snapshot(self) -> None:
        profile_url = "https://www.xiaohongshu.com/user/profile/userfixture?xsec_token=secret"
        snapshot = {
            "snapshot_version": 1,
            "url": profile_url,
            "profile": {"user_id": "userfixture", "nickname": "Synthetic Author"},
            "notes": [{"note_id": "fixture001", "title": "Synthetic card", "cover_url": "https://sns-webpic-qc.xhscdn.com/cover.jpg"}],
            "pagination": {"has_more": False},
            "page_has_profile_content": True,
        }
        calls: list[tuple[list[str], str | None]] = []

        def runner(command, *, input, **_kwargs):
            calls.append((list(command), input))
            operation = command[2:]
            if operation == ["status"]:
                output = json.dumps({"data": {"extension": {"relayUp": True}}, "success": True})
            elif operation == ["tab", "list"]:
                output = json.dumps([{"targetId": "profile-tab", "url": profile_url}])
            elif operation[:2] == ["tab", "adopt"] or operation == ["snapshot", "-i"]:
                output = "{}"
            elif operation[:1] in (["scroll"], ["wait"]):
                output = "{}"
            elif operation == ["eval", "--stdin"]:
                output = json.dumps(json.dumps(snapshot))
            else:
                raise AssertionError(f"unexpected profile command: {operation}")
            return subprocess.CompletedProcess(command, 0, output, "")

        with tempfile.TemporaryDirectory() as temp_dir:
            client = xhs_chrome_use.ChromeUseClient(runner=runner)
            result, path = xhs_chrome_use.acquire_profile_snapshot(
                profile_url,
                cache_dir=Path(temp_dir),
                scroll_steps=1,
                client=client,
            )
            saved = path.read_text(encoding="utf-8")

        operations = [call[0][2:] for call in calls]
        self.assertEqual(operations[:4], [["status"], ["tab", "list"], ["tab", "adopt", "profile-tab"], ["snapshot", "-i"]])
        self.assertIn(["scroll", "down", "800"], operations)
        self.assertEqual(result["profile"]["nickname"], "Synthetic Author")
        self.assertNotIn("secret", saved)
        self.assertNotIn("--user-data-dir", json.dumps([call[0] for call in calls]))
        self.assertNotIn("--launch", json.dumps([call[0] for call in calls]))

    def test_profile_reader_reports_gate_without_claiming_profile_content(self) -> None:
        result = xhs_profile_reader.enrich_result({
            "url": "https://www.xiaohongshu.com/user/profile/userfixture?xsec_token=secret",
            "page_error": "SECURITY_RESTRICTED_300011",
            "page_has_profile_content": False,
            "security_code": "300011",
            "profile": {"user_id": "userfixture"},
            "notes": [],
            "pagination": {},
        })
        self.assertFalse(result["page_has_profile_content"])
        self.assertTrue(result["errors"][0].startswith("SECURITY_RESTRICTED_300011"))
        self.assertEqual(result["retrieval"]["mode"], "real_chrome")
        self.assertNotIn("secret", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
