from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .config import ConfigError, sha256_file
from .governance import audit_all, require_license, require_permission
from .records import _iter_jsonl


def _query_expression(query: str) -> str:
    tokens = re.findall(r"[\w-]+", query, flags=re.UNICODE)
    if not tokens:
        raise ConfigError("Retrieval query has no searchable terms")
    return " OR ".join(f'"{token}"' for token in tokens[:32])


def build_index(input_path: Path, output_path: Path) -> int:
    if output_path.exists():
        raise ConfigError(f"Index already exists; refusing overwrite: {output_path}")
    audit, bundle = audit_all()
    if not audit.ok:
        raise ConfigError("Project configuration audit failed before indexing")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(output_path)
    count = 0
    seen: set[str] = set()
    try:
        connection.execute(
            "CREATE VIRTUAL TABLE documents USING fts5("
            "record_id UNINDEXED, title, text, citation UNINDEXED, "
            "source_ids UNINDEXED, license UNINDEXED)"
        )
        connection.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        for line_number, document in _iter_jsonl(input_path):
            required = {"record_id", "title", "text", "citation", "source_ids", "license"}
            missing = sorted(required - document.keys())
            if missing:
                raise ConfigError(f"line {line_number}: missing {', '.join(missing)}")
            record_id = document["record_id"]
            if record_id in seen:
                raise ConfigError(f"line {line_number}: duplicate record_id {record_id}")
            seen.add(record_id)
            if not document["citation"]:
                raise ConfigError(f"line {line_number}: citation is required")
            source_ids = document["source_ids"]
            if not isinstance(source_ids, list) or not source_ids:
                raise ConfigError(f"line {line_number}: source_ids must be non-empty")
            require_license(bundle["policy"], document["license"], "retrieval")
            for source_id in source_ids:
                source = bundle["sources"].get(source_id)
                if source is None:
                    raise ConfigError(f"line {line_number}: unknown source {source_id}")
                require_permission(source, "retrieval", document["license"])
            connection.execute(
                "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?)",
                (
                    record_id,
                    document["title"],
                    document["text"],
                    document["citation"],
                    json.dumps(source_ids),
                    document["license"],
                ),
            )
            count += 1
        connection.execute(
            "INSERT INTO metadata VALUES (?, ?)", ("input_sha256", sha256_file(input_path))
        )
        connection.execute("INSERT INTO metadata VALUES (?, ?)", ("record_count", str(count)))
        connection.commit()
    except Exception:
        connection.close()
        output_path.unlink(missing_ok=True)
        raise
    finally:
        connection.close()
    return count


def search(index_path: Path, query: str, limit: int = 5) -> list[dict[str, Any]]:
    if not index_path.is_file():
        raise ConfigError(f"Retrieval index does not exist: {index_path}")
    if limit < 1 or limit > 100:
        raise ConfigError("limit must be between 1 and 100")
    expression = _query_expression(query)
    connection = sqlite3.connect(index_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            "SELECT record_id, title, text, citation, source_ids, license, "
            "bm25(documents) AS score FROM documents WHERE documents MATCH ? "
            "ORDER BY score LIMIT ?",
            (expression, limit),
        ).fetchall()
    finally:
        connection.close()
    return [
        {
            "record_id": row["record_id"],
            "title": row["title"],
            "text": row["text"],
            "citation": row["citation"],
            "source_ids": json.loads(row["source_ids"]),
            "license": row["license"],
            "score": row["score"],
        }
        for row in rows
    ]


def grounded_context(query: str, hits: list[dict[str, Any]]) -> str:
    evidence = "\n\n".join(
        f"[{hit['record_id']}] {hit['title']}\n{hit['text']}\nSource: {hit['citation']}"
        for hit in hits
    )
    return (
        "Answer the research question using only supported evidence and named scientific "
        "tools. Distinguish observed, calculated, predicted and uncertain claims. Cite "
        "retrieved evidence as [record_id]. Do not invent numerical results or sources.\n\n"
        f"Question:\n{query}\n\nRetrieved evidence:\n{evidence or 'No evidence retrieved.'}"
    )

