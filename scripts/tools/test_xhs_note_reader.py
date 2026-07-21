from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.tools import xhs_note_reader


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


class XhsNoteReaderTests(unittest.TestCase):
    def test_parse_initial_state_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_json = Path(tmp) / "note.json"
            code = xhs_note_reader.main(
                [
                    "--url",
                    "https://www.xiaohongshu.com/discovery/item/abc123",
                    "--html-file",
                    str(FIXTURE_DIR / "xhs_initial_state.html"),
                    "--out-json",
                    str(out_json),
                ]
            )
            self.assertEqual(code, 0)
            data = json.loads(out_json.read_text(encoding="utf-8"))

        self.assertTrue(data["ok"])
        self.assertEqual(data["note_id"], "abc123")
        self.assertEqual(data["title"], "\u0049\u0043\u004d\u004c\u0020\u0032\u0030\u0032\u0036\u0020\u5927\u91cf\u0020\u004c\u004c\u004d\u0073\u0020\u76f8\u5173\u0020\u0049\u006e\u0073\u0069\u0067\u0068\u0074\u0073\u0020\u603b\u7ed3\uff08\u4e00\uff09")
        self.assertEqual(data["author"]["nickname"], "\u5e78\u8fd0\u964d\u4e34\u4e2d")
        self.assertEqual(data["stats"]["likes"], "1.2\u4e07")
        self.assertEqual(data["tags"], ["ICML26", "LLMs", "Agent"])
        self.assertEqual(len(data["images"]), 2)
        self.assertIn("\u4eca\u5e74 ICML", data["combined_text"])

    def test_missing_initial_state_returns_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_json = Path(tmp) / "note.json"
            code = xhs_note_reader.main(
                [
                    "--url",
                    "https://www.xiaohongshu.com/discovery/item/missing",
                    "--html-file",
                    str(FIXTURE_DIR / "xhs_no_initial_state.html"),
                    "--out-json",
                    str(out_json),
                ]
            )
            self.assertEqual(code, 1)
            data = json.loads(out_json.read_text(encoding="utf-8"))

        self.assertFalse(data["ok"])
        self.assertTrue(data["errors"])
        self.assertIn("INITIAL_STATE_NOT_FOUND", data["errors"][0])

    def test_auto_ocr_accepts_good_paddle_result(self) -> None:
        image = Path("image.jpg")

        def paddle_runner(_image: Path) -> xhs_note_reader.OcrResult:
            return xhs_note_reader.OcrResult(
                engine="paddle",
                ocr="\u8fd9\u662f\u4e00\u6bb5\u8db3\u591f\u957f\u7684 OCR \u6587\u672c",
                summary="PaddleOCR extracted 1 text lines.",
                confidence=0.96,
            )

        def vlm_runner(*_args: object, **_kwargs: object) -> xhs_note_reader.OcrResult:
            raise AssertionError("VLM should not be called for good PaddleOCR output")

        result = xhs_note_reader.run_auto_ocr(
            image,
            engine="auto",
            script_path=Path("describe-image.ps1"),
            timeout=1,
            max_tokens=128,
            paddle_min_chars=8,
            paddle_min_confidence=0.5,
            allow_vlm_fallback=True,
            paddle_runner=paddle_runner,
            vlm_runner=vlm_runner,
        )

        self.assertEqual(result.engine, "paddle")
        self.assertEqual(result.fallback_reason, "")

    def test_auto_ocr_falls_back_when_paddle_quality_is_poor(self) -> None:
        image = Path("image.jpg")

        def paddle_runner(_image: Path) -> xhs_note_reader.OcrResult:
            return xhs_note_reader.OcrResult(engine="paddle", ocr="bad", summary="", confidence=0.9)

        def vlm_runner(*_args: object, **_kwargs: object) -> xhs_note_reader.OcrResult:
            return xhs_note_reader.OcrResult(engine="vlm", ocr="VLM OCR text", summary="VLM summary")

        result = xhs_note_reader.run_auto_ocr(
            image,
            engine="auto",
            script_path=Path("describe-image.ps1"),
            timeout=1,
            max_tokens=128,
            paddle_min_chars=8,
            paddle_min_confidence=0.5,
            allow_vlm_fallback=True,
            paddle_runner=paddle_runner,
            vlm_runner=vlm_runner,
        )

        self.assertEqual(result.engine, "vlm")
        self.assertTrue(result.fallback_reason.startswith("too_few_chars"))

    def test_auto_ocr_falls_back_when_paddle_is_unavailable(self) -> None:
        image = Path("image.jpg")

        def paddle_runner(_image: Path) -> xhs_note_reader.OcrResult:
            raise RuntimeError("PaddleOCR unavailable")

        def vlm_runner(*_args: object, **_kwargs: object) -> xhs_note_reader.OcrResult:
            return xhs_note_reader.OcrResult(engine="vlm", ocr="VLM OCR text", summary="VLM summary")

        result = xhs_note_reader.run_auto_ocr(
            image,
            engine="auto",
            script_path=Path("describe-image.ps1"),
            timeout=1,
            max_tokens=128,
            paddle_min_chars=8,
            paddle_min_confidence=0.5,
            allow_vlm_fallback=True,
            paddle_runner=paddle_runner,
            vlm_runner=vlm_runner,
        )

        self.assertEqual(result.engine, "vlm")
        self.assertIn("paddle_failed", result.fallback_reason)


if __name__ == "__main__":
    unittest.main()
