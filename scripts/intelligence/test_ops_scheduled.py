from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from .ops.scheduled import build_daily_summary, run_scheduled_pipeline, send_summary


class ScheduledNotificationTests(unittest.TestCase):
    @patch("scripts.intelligence.ops.scheduled.subprocess.run")
    def test_sender_uses_hermes_cli_with_stdin_and_home_target(self, run_process: object) -> None:
        run_process.return_value.returncode = 0

        send_summary("safe aggregate", hermes_path=Path("C:/hermes.exe"), target="weixin")

        run_process.assert_called_once()
        args, kwargs = run_process.call_args
        self.assertEqual(args[0], [str(Path("C:/hermes.exe")), "send", "--to", "weixin", "--quiet"])
        self.assertEqual(kwargs["input"], "safe aggregate")
        self.assertEqual(kwargs["encoding"], "utf-8")
        self.assertIs(kwargs["check"], False)

    def test_summary_contains_aggregate_metrics_and_excludes_raw_errors(self) -> None:
        summary = build_daily_summary({
            "status": "partial",
            "run": {
                "run_date": "2026-10-08",
                "status": "partial",
                "source_summary": {
                    "sources_total": 5,
                    "sources_succeeded": 3,
                    "sources_failed": 1,
                    "sources_deferred": 1,
                    "fetched": 42,
                    "new_observations": 8,
                    "new_artifacts": 6,
                    "results": [{"error": "Authorization: secret-value"}],
                },
                "source_health": {"healthy": 4, "deferred": 1, "stale": 2, "failing": 0, "never_run": 1},
                "feed_metrics": {"selected_count": 12, "revision": 3},
                "corpus_hash_after": "abcdef0123456789",
            },
        })

        self.assertIn("研究情报每日任务｜2026-10-08", summary)
        self.assertIn("状态：部分完成", summary)
        self.assertIn("来源：3/5 成功，1 失败，1 延后", summary)
        self.assertIn("抓取 42 条，新 Observation 8 条，新 Artifact 6 个", summary)
        self.assertIn("语料：abcdef012345", summary)
        self.assertNotIn("secret-value", summary)
        self.assertNotIn("Authorization", summary)

    def test_partial_run_sends_weixin_summary_and_maps_to_task_success(self) -> None:
        calls: list[dict[str, object]] = []

        def pipeline(**kwargs: object) -> dict[str, object]:
            self.assertIs(kwargs["scheduled"], True)
            return {"exit_code": 2, "status": "partial", "run": {"run_date": "2026-10-08", "status": "partial"}}

        def sender(message: str, **kwargs: object) -> None:
            calls.append({"message": message, **kwargs})

        result = run_scheduled_pipeline(
            hermes_path=Path("C:/hermes.exe"), pipeline=pipeline, sender=sender,
        )

        self.assertEqual(result, 0)
        self.assertEqual(calls[0]["target"], "weixin")
        self.assertIn("状态：部分完成", str(calls[0]["message"]))

    def test_delivery_failure_marks_scheduled_task_failed(self) -> None:
        def pipeline(**_kwargs: object) -> dict[str, object]:
            return {"exit_code": 0, "status": "completed", "run": {"status": "completed"}}

        def failed_sender(_message: str, **_kwargs: object) -> None:
            raise RuntimeError("network unavailable")

        result = run_scheduled_pipeline(
            hermes_path=Path("C:/hermes.exe"), pipeline=pipeline, sender=failed_sender,
        )

        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
