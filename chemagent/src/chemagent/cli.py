from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import ConfigError
from .governance import audit_all
from .manifest import register_local_file
from .preflight import report_json, run_preflight
from .rag import build_index, grounded_context, search
from .records import build_sft


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chemagent")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate-config", help="validate all project registries")
    subparsers.add_parser("audit", help="show source and book permissions")

    preflight = subparsers.add_parser("preflight", help="run governance or training checks")
    preflight.add_argument("--level", choices=("governance", "training"), default="governance")

    register = subparsers.add_parser("register-local", help="hash and register a local artifact")
    register.add_argument("--file", type=Path, required=True)
    register.add_argument("--source-id", required=True)
    register.add_argument("--purpose", choices=("training", "retrieval"), required=True)
    register.add_argument("--license", required=True)
    register.add_argument("--license-evidence", required=True)
    register.add_argument("--output-dir", type=Path)

    dataset = subparsers.add_parser("build-sft", help="validate and split curated SFT JSONL")
    dataset.add_argument("--input", type=Path, required=True)
    dataset.add_argument("--output", type=Path, required=True)

    index = subparsers.add_parser("build-index", help="build a local SQLite FTS5 index")
    index.add_argument("--input", type=Path, required=True)
    index.add_argument("--output", type=Path, required=True)

    retrieval = subparsers.add_parser("search", help="search a local retrieval index")
    retrieval.add_argument("--index", type=Path, required=True)
    retrieval.add_argument("--query", required=True)
    retrieval.add_argument("--limit", type=int, default=5)

    context = subparsers.add_parser("context", help="render a grounded model prompt")
    context.add_argument("--index", type=Path, required=True)
    context.add_argument("--query", required=True)
    context.add_argument("--limit", type=int, default=5)
    return parser


def _audit_output() -> int:
    result, bundle = audit_all()
    for kind, entries in (("SOURCE", bundle["sources"]), ("BOOK", bundle["books"])):
        for entry_id, entry in entries.items():
            train = "yes" if entry["training_allowed"] else "no"
            retrieve = "yes" if entry["retrieval_allowed"] else "no"
            print(
                f"{kind:6} {entry_id:42} approval={entry['approval']:18} "
                f"train={train:3} rag={retrieve:3} license={entry['license']}"
            )
    for warning in result.warnings:
        print(f"WARNING {warning}", file=sys.stderr)
    for error in result.errors:
        print(f"ERROR {error}", file=sys.stderr)
    return 0 if result.ok else 2


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "validate-config":
            result, _ = audit_all()
            for warning in result.warnings:
                print(f"WARNING {warning}")
            for error in result.errors:
                print(f"ERROR {error}", file=sys.stderr)
            print("PASS" if result.ok else "FAIL")
            return 0 if result.ok else 2
        if args.command == "audit":
            return _audit_output()
        if args.command == "preflight":
            ok, checks = run_preflight(args.level)
            print(report_json(checks))
            return 0 if ok else 2
        if args.command == "register-local":
            destination, manifest = register_local_file(
                args.file,
                args.source_id,
                args.purpose,
                args.license,
                args.license_evidence,
                args.output_dir,
            )
            print(json.dumps({"manifest": str(destination), **manifest}, indent=2))
            return 0
        if args.command == "build-sft":
            summary = build_sft(args.input, args.output)
            print(
                json.dumps(
                    {
                        "counts": summary.counts,
                        "input_sha256": summary.input_sha256,
                        "output_dir": str(summary.output_dir),
                    },
                    indent=2,
                )
            )
            return 0
        if args.command == "build-index":
            count = build_index(args.input, args.output)
            print(json.dumps({"index": str(args.output), "records": count}, indent=2))
            return 0
        if args.command == "search":
            print(
                json.dumps(
                    search(args.index, args.query, args.limit), indent=2, ensure_ascii=False
                )
            )
            return 0
        if args.command == "context":
            hits = search(args.index, args.query, args.limit)
            print(grounded_context(args.query, hits))
            return 0
    except (ConfigError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
