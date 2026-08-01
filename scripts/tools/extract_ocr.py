#!/usr/bin/env python3
"""
Batch OCR for Xiaohongshu image folders using PaddleOCR 3.0 + CUDA 12.9.
Drop-in replacement for extract_paddleocr.py.

Performance (RTX 5060, PaddlePaddle 3.0 nightly + CUDA 12.9): ~0.7s/image.

Usage:
    python extract_ocr.py <image_folder>

Output (stdout):
    JSON mapping filename -> [text lines]
"""

import json
import os
import sys
import time
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}


def ocr_folder(folder: str) -> dict:
    """Run OCR on all images. Returns {filename: [text_lines]} dict."""
    from paddleocr import PaddleOCR

    ocr = PaddleOCR(lang="ch")
    results = {}
    total_start = time.time()
    image_count = 0

    for entry in sorted(Path(folder).iterdir()):
        if not entry.is_file() or entry.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        image_path = str(entry)
        try:
            pred = ocr.predict(image_path)
            item = pred[0]
            texts = item.get("rec_texts", [])
            results[entry.name] = texts
            image_count += 1
            sys.stderr.write(
                f"[{image_count}] {entry.name}: {len(texts)} lines\n"
            )
        except Exception as e:
            results[entry.name] = []
            sys.stderr.write(f"[{image_count}] {entry.name}: ERROR - {e}\n")

    total_elapsed = time.time() - total_start
    if image_count:
        sys.stderr.write(
            f"\nDone: {image_count} images in {total_elapsed:.1f}s "
            f"({total_elapsed / image_count:.1f}s avg)\n"
        )
    else:
        sys.stderr.write("\nDone: 0 images\n")

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Batch OCR using PaddleOCR 3.0 + CUDA 12.9"
    )
    parser.add_argument("folder", help="Path to image folder")
    args = parser.parse_args()

    if not os.path.isdir(args.folder):
        print(json.dumps({"error": f"Not a directory: {args.folder}"}))
        sys.exit(1)

    results = ocr_folder(args.folder)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
