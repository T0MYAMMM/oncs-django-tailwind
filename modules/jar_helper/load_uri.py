#!/usr/bin/env python3
from __future__ import annotations
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Tuple

import psycopg2
import psycopg2.extras as pgx
from psycopg2.extras import execute_values


def extract_urls_from_json_obj(obj) -> List[str]:
    """Return [uri] if present in a dict; or collect urls across a list."""
    urls: List[str] = []
    if isinstance(obj, dict):
        uri = obj.get("uri")
        if isinstance(uri, str):
            urls.append(uri)
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                u = item.get("uri")
                if isinstance(u, str):
                    urls.append(u)
    return urls


def extract_urls_from_file(fp: Path) -> List[str]:
    """Try standard JSON first; if that fails, try NDJSON."""
    try:
        with fp.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return extract_urls_from_json_obj(data)
    except json.JSONDecodeError:
        urls: List[str] = []
        with fp.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    urls.extend(extract_urls_from_json_obj(obj))
                except json.JSONDecodeError:
                    # skip bad lines
                    continue
        return urls


def connect_pg(dsn: str):
    conn = psycopg2.connect(dsn)
    conn.autocommit = False  # we’ll manage commits
    with conn.cursor() as cur:
        # Optional: a recognizable app name in pg_stat_activity
        cur.execute("SET application_name = 'load_urls_pg';")
    return conn


def ensure_table(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS urls (
                id BIGSERIAL PRIMARY KEY,
                uri TEXT NOT NULL UNIQUE,
                source_file TEXT,
                inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
    conn.commit()


def insert_urls(conn, rows: List[Tuple[str, str, datetime]]) -> Tuple[int, int]:
    """
    Insert rows of (uri, source_file, inserted_at).
    Uses ON CONFLICT DO NOTHING to dedupe by uri.
    Returns (inserted_count, skipped_dups) best-effort.
    """
    if not rows:
        return 0, 0

    with conn.cursor() as cur:
        # execute_values is fast and safe for bulk inserts
        query = """
            INSERT INTO urls (uri, source_file, inserted_at)
            VALUES %s
            ON CONFLICT (uri) DO NOTHING
        """
        # execute_values returns None; we approximate counts
        before = count_rows(conn)
        execute_values(cur, query, rows, page_size=1000)
    conn.commit()
    after = count_rows(conn)
    inserted = max(0, after - before)
    skipped = len(rows) - inserted
    return inserted, skipped


def count_rows(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM urls;")
        return cur.fetchone()[0]


def main():
    if len(sys.argv) not in (2, 3):
        print("Usage: python load_urls_pg.py /path/to/folder \"postgresql://USER:PASS@HOST:PORT/DBNAME\"")
        print("   Or: DATABASE_URL=... python load_urls_pg.py /path/to/folder")
        sys.exit(1)

    folder = Path(sys.argv[1]).expanduser().resolve()
    if not folder.is_dir():
        print(f"Error: {folder} is not a directory")
        sys.exit(2)

    dsn = (sys.argv[2] if len(sys.argv) == 3 else os.getenv("DATABASE_URL"))
    if not dsn:
        print("Error: missing DSN. Pass it as arg 2 or set DATABASE_URL.")
        sys.exit(3)

    conn = connect_pg(dsn)
    try:
        ensure_table(conn)

        now_dt = datetime.now(timezone.utc)
        json_files = sorted(folder.rglob("*.json"))

        total_files = len(json_files)
        total_found = 0
        total_inserted = 0
        total_skipped = 0

        # Build a single bulk list (simple and safe for a few thousand rows)
        bulk_rows: List[Tuple[str, str, datetime]] = []
        for fp in json_files:
            urls = extract_urls_from_file(fp)
            total_found += len(urls)
            bulk_rows.extend((u, str(fp), now_dt) for u in urls)

        inserted, skipped = insert_urls(conn, bulk_rows)
        total_inserted += inserted
        total_skipped += skipped

        print("=== Import Summary ===")
        print(f"Folder:        {folder}")
        print(f"DB (Postgres): {dsn}")
        print(f"JSON files:    {total_files}")
        print(f"urls found:    {total_found}")
        print(f"Inserted:      {total_inserted}")
        print(f"Skipped (dup): {total_skipped}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
