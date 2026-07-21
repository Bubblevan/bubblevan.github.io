#!/usr/bin/env python3
"""
PaddleOCR 2.x GPU 批量 OCR 工具。

适用于：
- Python 3.7
- PaddlePaddle GPU 2.5.2
- PaddleOCR 2.7.x

stdout：只输出 JSON
stderr：输出进度和错误
"""

import json
import sys
import time
from pathlib import Path

import paddle
from paddleocr import PaddleOCR


def log(message):
    print(message, file=sys.stderr, flush=True)


def find_images(directory):
    supported = {
        ".jpg",
        ".jpeg",
        ".png",
        ".bmp",
        ".tif",
        ".tiff",
        ".webp",
    }

    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in supported
    )


def create_ocr():
    use_gpu = (
        paddle.is_compiled_with_cuda()
        and paddle.device.cuda.device_count() > 0
    )

    log("PaddlePaddle: {}".format(paddle.__version__))
    log("CUDA compiled: {}".format(paddle.is_compiled_with_cuda()))
    log("GPU count: {}".format(paddle.device.cuda.device_count()))
    log("OCR device: {}".format("GPU" if use_gpu else "CPU"))
    log("正在初始化 PaddleOCR……")

    started = time.time()

    ocr = PaddleOCR(
        lang="ch",
        use_gpu=use_gpu,

        # 小红书截图一般方向正常，关闭可加快速度
        use_angle_cls=False,

        # 关闭 PaddleOCR 自身日志
        show_log=False,
    )

    log("初始化完成，耗时 {:.2f} 秒。".format(time.time() - started))
    return ocr


def extract_texts(ocr, image_path):
    # cls=False，因为初始化时关闭了方向分类
    result = ocr.ocr(str(image_path), cls=False)

    texts = []

    if not result:
        return texts

    # PaddleOCR 2.x 通常返回：
    # [
    #   [
    #     [box, (text, confidence)],
    #     ...
    #   ]
    # ]
    page_result = result[0] if len(result) > 0 else None

    if not page_result:
        return texts

    for line in page_result:
        if not line or len(line) < 2:
            continue

        recognition = line[1]

        if not recognition or len(recognition) < 1:
            continue

        text = recognition[0]

        if text and str(text).strip():
            texts.append(str(text))

    return texts


def process_images(directory):
    directory_path = Path(directory)

    if not directory_path.is_dir():
        raise FileNotFoundError("目录不存在：{}".format(directory))

    image_files = find_images(directory_path)

    if not image_files:
        log("没有找到图片。")
        return {}

    total = len(image_files)
    log("共找到 {} 张图片。".format(total))

    ocr = create_ocr()
    results = {}

    total_started = time.time()

    for index, image_path in enumerate(image_files, 1):
        relative_path = image_path.relative_to(directory_path).as_posix()
        started = time.time()

        log("[{}/{}] 正在识别：{}".format(
            index,
            total,
            relative_path,
        ))

        try:
            texts = extract_texts(ocr, image_path)
            results[relative_path] = texts

            log(
                "[{}/{}] 完成：{}，{} 行，耗时 {:.2f} 秒。".format(
                    index,
                    total,
                    relative_path,
                    len(texts),
                    time.time() - started,
                )
            )

        except Exception as exc:
            results[relative_path] = []

            log(
                "[{}/{}] 失败：{}；错误：{}".format(
                    index,
                    total,
                    relative_path,
                    exc,
                )
            )

    log("全部完成，总耗时 {:.2f} 秒。".format(
        time.time() - total_started
    ))

    return results


def main():
    if len(sys.argv) < 2:
        log(
            "用法：python extract_paddleocr_v2.py "
            "<图片目录>"
        )
        return 2

    target_directory = sys.argv[1]

    try:
        results = process_images(target_directory)
    except Exception as exc:
        log("处理失败：{}".format(exc))
        return 1

    json.dump(
        results,
        sys.stdout,
        ensure_ascii=False,
        indent=2,
    )
    sys.stdout.write("\n")
    sys.stdout.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())

