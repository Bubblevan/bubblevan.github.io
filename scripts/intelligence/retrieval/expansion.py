from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Iterable, Mapping

import yaml

from ..topics import CATALOG


_TECHNICAL = {
    "rag": "retrieval augmented generation",
    "opd": "on policy distillation",
    "rl": "reinforcement learning",
    "cot": "chain of thought",
    "vllm": "inference serving",
}
_BILINGUAL = {
    "搜索智能体": ("search agent", "information search agent"),
    "search agent": ("search agents", "search agent training"),
    "后训练": ("post-training", "post training"),
    "强化学习": ("reinforcement learning",),
    "记忆": ("memory", "agent memory"),
    "推理服务": ("inference serving",),
    "多模态智能体": ("multimodal agent",),
}


def expand_query(query: str, *, topics_path: str | Path = CATALOG,
                 entity_names: Iterable[str] = (), entity_aliases: Mapping[str, str] | None = None) -> list[str]:
    original = str(query).strip()
    terms: set[str] = set()
    normalized = original.casefold()
    for abbreviation, expansion in _TECHNICAL.items():
        if re.search(rf"(?<![a-z0-9]){re.escape(abbreviation)}(?![a-z0-9])", normalized):
            terms.add(expansion)
    for alias, expansions in _BILINGUAL.items():
        if alias.casefold() in normalized:
            terms.update(expansions)
    if (re.search(r"\bsearch agents?\b", normalized)
            and re.search(r"post[ -]?training|后训练", normalized)):
        # Search-Agent post-training is frequently indexed under its concrete
        # policy-learning vocabulary rather than the phrase "post-training".
        terms.update(("reinforcement learning for search agents",
                      "search agent policy optimization", "search agent rewards"))
    for name in entity_names:
        display = str(name).strip()
        if display and display.casefold() in normalized:
            terms.add(display)
    for alias, display in (entity_aliases or {}).items():
        if alias and alias.casefold() in normalized and display.strip():
            terms.add(display.strip())
    payload: Any = yaml.safe_load(Path(topics_path).read_text(encoding="utf-8"))
    for topic in payload.get("topics", []) if isinstance(payload, dict) else []:
        if not isinstance(topic, dict):
            continue
        names = [str(topic.get("name") or ""), *(str(item) for item in topic.get("aliases", []))]
        topic_id = str(topic.get("topic_id") or "")
        searchable = [*names, topic_id.replace("topic-", "").replace("-", " ")]
        if any(name and name.casefold() in normalized for name in searchable):
            terms.update(name for name in names if name)
    terms.discard(original)
    return sorted(terms, key=lambda item: (item.casefold(), item))


def expanded_query_text(query: str, expanded_terms: list[str] | tuple[str, ...]) -> str:
    return " ".join([query, *expanded_terms]).strip()
