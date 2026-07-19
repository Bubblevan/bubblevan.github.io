from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .markdown import find_data_ids, read_markdown


ALLOWED_CONTENT_KINDS = {
    "blog",
    "daily",
    "doc",
    "paper",
    "project",
    "project_decision",
    "retrospective",
    "bookmark",
    "star",
}

REQUIRED_FIELDS = {"schema", "id", "content_kind", "title", "date", "status", "visibility"}


@dataclass
class Issue:
    level: str
    path: Path
    message: str


def run_validate(root: str = ".") -> int:
    root_path = Path(root).resolve()
    issues: list[Issue] = []

    project_ids = set(find_data_ids(root_path / "data" / "projects.yaml"))
    validate_data_ids(root_path, issues)
    validate_markdown(root_path, project_ids, issues)

    errors = [issue for issue in issues if issue.level == "error"]
    warnings = [issue for issue in issues if issue.level == "warning"]

    for issue in issues:
        rel = issue.path.relative_to(root_path) if issue.path.is_absolute() else issue.path
        print(f"{issue.level.upper()}: {rel}: {issue.message}")

    print(f"Validation complete: {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


def validate_data_ids(root: Path, issues: list[Issue]) -> None:
    required_non_empty = {Path("data/projects.yaml")}
    for relative in [Path("data/projects.yaml"), Path("data/bookmarks.yaml"), Path("data/reminders.yaml"), Path("data/sources.yaml")]:
        path = root / relative
        ids = find_data_ids(path)
        if not path.exists():
            issues.append(Issue("error", path, "required data file is missing"))
            continue
        if not ids and relative in required_non_empty:
            issues.append(Issue("warning", path, "no ids found"))
        for duplicate in duplicates(ids):
            issues.append(Issue("error", path, f"duplicate data id: {duplicate}"))


def validate_markdown(root: Path, project_ids: set[str], issues: list[Issue]) -> None:
    seen_ids: dict[str, Path] = {}
    content_root = root / "content"
    if not content_root.exists():
        issues.append(Issue("error", content_root, "content directory is missing"))
        return

    for path in content_root.rglob("*.md"):
        md = read_markdown(path)
        fm = md.frontmatter
        should_validate = (
            fm.get("schema") == "bubblevan/v1"
            or is_under(path, content_root / "projects")
            or is_under(path, content_root / "career")
        )
        if not should_validate:
            continue

        missing = sorted(field for field in REQUIRED_FIELDS if not fm.get(field))
        for field in missing:
            issues.append(Issue("error", path, f"missing required frontmatter field: {field}"))

        content_id = fm.get("id")
        if isinstance(content_id, str) and content_id:
            if content_id in seen_ids:
                issues.append(Issue("error", path, f"duplicate content id also used by {seen_ids[content_id]}"))
            else:
                seen_ids[content_id] = path

        content_kind = fm.get("content_kind")
        if isinstance(content_kind, str) and content_kind not in ALLOWED_CONTENT_KINDS:
            issues.append(Issue("error", path, f"unsupported content_kind: {content_kind}"))

        projects = fm.get("projects", [])
        if isinstance(projects, list):
            for project in projects:
                if project and project not in project_ids:
                    issues.append(Issue("error", path, f"unknown project reference: {project}"))

        if fm.get("visibility") == "private" and is_under(path, content_root):
            issues.append(Issue("warning", path, "visibility private is metadata only in this public content tree"))


def duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    dupes: list[str] = []
    for value in values:
        if value in seen and value not in dupes:
            dupes.append(value)
        seen.add(value)
    return dupes


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
