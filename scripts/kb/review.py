"""Review queue — scan extraction JSON and list pending items."""
from __future__ import annotations

from pathlib import Path
import json

from .promote import load_reviewed


def scan_items(extraction_dir: Path) -> list[dict]:
    items: list[dict] = []
    if not extraction_dir.exists():
        return items
    for fp in sorted(extraction_dir.glob("*.json")):
        payload = json.loads(fp.read_text(encoding="utf-8"))
        src = payload.get("source_path", fp.name)
        for item in payload.get("items", []):
            item["_src"] = src
            items.append(item)
    return items


def run_review(root: str = ".") -> int:
    root_path = Path(root).resolve()
    extraction_dir = root_path / "generated" / "extraction"
    reviewed = load_reviewed(root_path)

    items = scan_items(extraction_dir)
    pending = [it for it in items if it.get("capture_id") not in reviewed]

    if not pending:
        print("Review queue is empty — no pending items.")
        return 0

    print(f"Review Queue  ({len(pending)} pending, {len(reviewed)} reviewed)\n")

    type_label = {"task": "待办", "event": "备忘", "link": "链接", "project_log": "项目笔记"}
    action_label = {
        "task": "promote",
        "event": "promote",
        "link": "promote",
        "project_log": "Phase 3 / retrospective",
    }
    widths = {"id": 26, "type": 8, "text": 48, "action": 24, "src": 40}
    header = (
        f"  {'capture_id':<{widths['id']}}"
        f"  {'type':<{widths['type']}}"
        f"  {'text':<{widths['text']}}"
        f"  {'action':<{widths['action']}}"
        f"  {'source'}"
    )
    print(header)
    print("  " + "-" * (sum(widths.values()) + 6))

    for item in pending:
        cap_id = item.get("capture_id", "?")[:24]
        itype = item.get("type", "?")
        label = type_label.get(itype, itype)
        action = action_label.get(itype, "manual")
        text = item.get("text", "")[:46]
        src = item.get("source_path", item.get("_src", "?"))
        try:
            p = Path(src)
            if len(p.parts) > 2:
                src = "/".join(p.parts[-2:])
        except Exception:
            pass
        src = f"{src}:{item.get('line', '?')}"[:38]

        print(f"  {cap_id:<{widths['id']}}  {label:<{widths['type']}}  {text:<{widths['text']}}  {action:<{widths['action']}}  {src}")

    print(f"\n  promote →  python -m scripts.kb promote <capture_id>")
    print("  project_log → keep for Phase 3 project retrospective flow")
    return 0
