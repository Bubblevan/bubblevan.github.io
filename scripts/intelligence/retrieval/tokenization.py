from __future__ import annotations

import re
import unicodedata


_WORD = re.compile(r"[a-z0-9]+(?:['+._-][a-z0-9]+)*|[\u3400-\u9fff]+", re.IGNORECASE)
_CJK = re.compile(r"[\u3400-\u9fff]+")


def tokenize(value: str) -> list[str]:
    """English word tokenizer plus Jieba segmentation and CJK bigram coverage."""
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    try:
        import jieba
        import logging
        jieba.setLogLevel(logging.WARNING)
    except ImportError:
        jieba = None
    tokens: list[str] = []
    for match in _WORD.finditer(text):
        item = match.group(0)
        if _CJK.fullmatch(item):
            if jieba:
                tokens.extend(piece.strip() for piece in jieba.cut(item, HMM=False) if piece.strip())
            tokens.extend(item[index:index + 2] for index in range(max(1, len(item) - 1)))
            if len(item) == 1:
                tokens.append(item)
        elif len(item) >= 2:
            tokens.append(item)
    return tokens
