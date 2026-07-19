from __future__ import annotations

import argparse
import sys

from .extract import run_extract
from .promote import run_promote
from .review import run_review
from .validate import run_validate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m scripts.kb")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate content metadata and data ids")
    validate.add_argument("--root", default=".", help="repository root")

    extract = subparsers.add_parser("extract", help="extract explicit markers from markdown")
    extract.add_argument("paths", nargs="+", help="markdown file paths")
    extract.add_argument("--out", default="generated/extraction", help="output directory")
    extract.add_argument("--root", default=".", help="repository root")

    review = subparsers.add_parser("review", help="list pending items from extraction output")
    review.add_argument("--root", default=".", help="repository root")

    promote = subparsers.add_parser("promote", help="promote an extracted item into data/*.yaml")
    promote.add_argument("capture_id", help="item capture_id from review output")
    promote.add_argument("--force", action="store_true", help="re-promote even if already reviewed")
    promote.add_argument("--root", default=".", help="repository root")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate":
        return run_validate(args.root)
    if args.command == "extract":
        return run_extract(args.paths, args.out, args.root)
    if args.command == "review":
        return run_review(args.root)
    if args.command == "promote":
        return run_promote(args.capture_id, args.root, force=args.force)
    return 2


if __name__ == "__main__":
    sys.exit(main())
