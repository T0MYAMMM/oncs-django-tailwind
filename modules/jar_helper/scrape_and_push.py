#!/usr/bin/env python3
"""
Process URIs from Postgres -> scrape via Zyte -> validate -> push to Kafka -> track status.
Logs in structured JSON and persists the final Kafka payload to push_tracking.payload_json.

Usage:
  python scrape_and_push_pg.py "postgresql://USER:PASS@HOST:PORT/DBNAME"

Env:
  API_ZYTE         = <your_zyte_api_key>
  DATABASE_URL     = postgresql://USER:PASS@HOST:PORT/DBNAME   (optional if passed as arg)
  SOURCE_TABLE     = urls_from_jar     (optional; table with a column `uri`)
  KAFKA_BOOTSTRAP  = host1:9092,host2:9092   (optional; overrides default list)
"""

from __future__ import annotations

import os
import sys
import json
import time
import logging
import logging.handlers
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests
from kafka import KafkaProducer
from kafka.errors import KafkaError
from dateutil import parser as dtparser
from dateutil.tz import gettz

# --- Postgres ---
import psycopg2
from psycopg2.extras import RealDictCursor, Json as PGJson

# ---------- Config ----------
KAFKA_BOOTSTRAP_DEFAULT = ['10.130.137.99:9092', '10.130.137.100:9092', '10.130.137.101:9092']
KAFKA_TOPIC = "onm-contents"
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "scrape_and_push.log")
SOURCE_TABLE = os.getenv("SOURCE_TABLE", "urls_from_jar")  # must have column 'uri'

REQUIRED_FIELDS = [
    "link",
    "source_name",
    "title",
    "body",
    "date_published",
    "images",
    "author_list",
    "language",
]

# ---------- Logging ----------
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for k, v in record.__dict__.items():
            if k in ("args", "msg", "levelname", "levelno", "pathname", "filename", "module",
                     "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created",
                     "msecs", "relativeCreated", "thread", "threadName", "processName", "process",
                     "name"):
                continue
            try:
                json.dumps({k: v})
                payload[k] = v
            except Exception:
                payload[k] = str(v)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)

def setup_logging() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=10_000_000, backupCount=5, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(JsonFormatter())
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(JsonFormatter())
    root.handlers.clear()
    root.addHandler(fh)
    root.addHandler(sh)

log_seed = logging.getLogger("scraper.seed")
log_worker = logging.getLogger("scraper.worker")
log_kafka = logging.getLogger("scraper.kafka")
log_zyte = logging.getLogger("scraper.zyte")

def log_event(logger: logging.Logger, event: str, **extra):
    logger.info(event, extra={"event": event, **extra})

# ---------- Postgres helpers ----------
def connect_db(dsn: str):
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    with conn.cursor() as cur:
        cur.execute("SET application_name = 'scrape_and_push_pg';")
    with conn.cursor() as cur:
        cur.execute("SHOW server_version;")
        ver = cur.fetchone()[0]
        log_event(log_worker, "postgres.version", version=ver)
    return conn

def ensure_tables(conn) -> None:
    # Create table if missing
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS push_tracking (
                id BIGSERIAL PRIMARY KEY,
                url TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL,         -- pending|running|success|error
                last_error TEXT,
                retries INTEGER NOT NULL DEFAULT 0,
                started_at TIMESTAMPTZ,
                finished_at TIMESTAMPTZ,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            """
        )
        # Add new columns for payload persistence / audit (safe to re-run)
        cur.execute("ALTER TABLE push_tracking ADD COLUMN IF NOT EXISTS payload_json JSONB;")
        cur.execute("ALTER TABLE push_tracking ADD COLUMN IF NOT EXISTS zyte_article_json JSONB;")
        cur.execute("ALTER TABLE push_tracking ADD COLUMN IF NOT EXISTS kafka_partition INT;")
        cur.execute("ALTER TABLE push_tracking ADD COLUMN IF NOT EXISTS kafka_offset BIGINT;")
        cur.execute("ALTER TABLE push_tracking ADD COLUMN IF NOT EXISTS payload_saved_at TIMESTAMPTZ;")
    conn.commit()

def seed_pending_from_uris(conn) -> int:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            WITH ins AS (
              INSERT INTO push_tracking (url, status, updated_at)
              SELECT u.uri, 'pending', NOW()
              FROM {SOURCE_TABLE} AS u
              ON CONFLICT (url) DO NOTHING
              RETURNING 1
            )
            SELECT COUNT(*) FROM ins;
            """
        )
        count = cur.fetchone()[0]
    conn.commit()
    return int(count)

def acquire_next_pending(conn) -> Optional[dict]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            WITH cte AS (
              SELECT id FROM push_tracking
              WHERE status = 'pending'
              ORDER BY id
              LIMIT 1
              FOR UPDATE SKIP LOCKED
            )
            UPDATE push_tracking AS p
               SET status='running',
                   started_at=NOW(),
                   updated_at=NOW()
              FROM cte
             WHERE p.id = cte.id
         RETURNING p.*;
            """
        )
        row = cur.fetchone()
    conn.commit()
    return dict(row) if row else None

def mark_success(conn, url: str, payload: Dict[str, Any], kafka_meta: Dict[str, Any], zyte_article: Optional[Dict[str, Any]]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE push_tracking
               SET status='success',
                   finished_at=NOW(),
                   updated_at=NOW(),
                   payload_json=%s,
                   zyte_article_json=%s,
                   kafka_partition=%s,
                   kafka_offset=%s,
                   payload_saved_at=NOW()
             WHERE url=%s;
            """,
            (
                PGJson(payload),
                PGJson(zyte_article) if zyte_article is not None else None,
                kafka_meta.get("partition"),
                kafka_meta.get("offset"),
                url,
            ),
        )
    conn.commit()

def mark_error(conn, url: str, message: str, zyte_article: Optional[Dict[str, Any]] = None, attempted_payload: Optional[Dict[str, Any]] = None) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE push_tracking
               SET status='error',
                   last_error=%s,
                   retries=retries+1,
                   finished_at=NOW(),
                   updated_at=NOW(),
                   zyte_article_json = COALESCE(%s, zyte_article_json),
                   payload_json      = COALESCE(%s, payload_json)
             WHERE url=%s;
            """,
            (
                message[:2000],
                PGJson(zyte_article) if zyte_article is not None else None,
                PGJson(attempted_payload) if attempted_payload is not None else None,
                url,
            ),
        )
    conn.commit()

# ---------- Utilities ----------
def extract_source_name(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc

def normalize_list_of_strings(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out = []
        for v in value:
            if isinstance(v, str):
                out.append(v)
            elif isinstance(v, dict):
                for key in ("name", "url", "content", "text"):
                    if key in v and isinstance(v[key], str):
                        out.append(v[key])
                        break
        return out
    if isinstance(value, str):
        return [value]
    return []

def normalize_string(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()

def parse_date_to_iso(raw: Any) -> str:
    if not raw:
        raise ValueError("empty date_published")
    raw_str = normalize_string(raw)
    try:
        dt = dtparser.parse(raw_str, fuzzy=True)
    except Exception as e:
        raise ValueError(f"unparsable date_published: {raw_str!r}") from e
    if dt.year is None or dt.month is None or dt.day is None:
        raise ValueError("date missing Y/M/D")
    if dt.hour is None or dt.minute is None:
        raise ValueError("date missing hour/minute")
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        tz = gettz("Asia/Jakarta") or timezone(timedelta(hours=7))
        dt = dt.replace(tzinfo=tz)
    if dt.second is None:
        dt = dt.replace(second=0)
    return dt.isoformat(timespec="seconds")

# ---------- Zyte API ----------
def request_zyte_api(url: str, extract_options: Dict[str, Any]) -> Dict[str, Any]:
    api_key = "0c671085bb1743bf94aca63032c28ceb"
    t0 = time.perf_counter()
    try:
        resp = requests.post(
            "https://api.zyte.com/v1/extract",
            auth=(api_key, ""),
            json={"url": url, "httpResponseBody": True, **extract_options},
            timeout=60,
        )
        dt_ms = int((time.perf_counter() - t0) * 1000)
        log_event(log_zyte, "zyte.request.done", url=url, http_status=resp.status_code, duration_ms=dt_ms)
        if resp.status_code != 200:
            return {"error": True, "status_code": resp.status_code, "error_message": resp.text}
        return resp.json()
    except Exception as e:
        dt_ms = int((time.perf_counter() - t0) * 1000)
        log_event(log_zyte, "zyte.request.error", url=url, duration_ms=dt_ms, error=str(e))
        return {"error": True, "status_code": -1, "error_message": str(e)}

def request_article(url: str) -> Dict[str, Any]:
    response = request_zyte_api(url, {"article": True, "articleOptions": {"extractFrom": "httpResponseBody"}})
    if response and not response.get("error"):
        return response.get("article") or {}
    return response

# ---------- Kafka ----------
def make_producer() -> KafkaProducer:
    bootstrap_env = os.getenv("KAFKA_BOOTSTRAP")
    bootstrap = [b.strip() for b in bootstrap_env.split(",")] if bootstrap_env else KAFKA_BOOTSTRAP_DEFAULT
    producer = KafkaProducer(
        bootstrap_servers=bootstrap,
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
        linger_ms=50,
        retries=5,
        acks=1,   # or 'all'
    )
    log_event(log_kafka, "kafka.producer.ready", bootstrap_servers=",".join(bootstrap))
    return producer

def push_to_kafka(producer: KafkaProducer, message: Dict[str, Any]) -> Dict[str, Any]:
    fut = producer.send(KAFKA_TOPIC, value=message)
    meta = fut.get(timeout=30)
    log_event(log_kafka, "kafka.produce.success", topic=meta.topic, partition=meta.partition, offset=meta.offset)
    return {"topic": meta.topic, "partition": meta.partition, "offset": meta.offset}

# ---------- Validation & mapping ----------
def build_payload(url: str, article: Dict[str, Any]) -> Dict[str, Any]:
    source_name = extract_source_name(url)
    title = normalize_string(article.get("headline"))
    body = normalize_string(article.get("articleBody"))
    authors_raw = article.get("authors")
    images_raw = article.get("images")
    language = normalize_string(article.get("inLanguage"))
    description = normalize_string(article.get("description") or "")

    author_list = normalize_list_of_strings(authors_raw)
    images = normalize_list_of_strings(images_raw)

    date_raw = (
        article.get("datePublishedRaw")
        or article.get("datePublished")
        or article.get("dateModified")
        or ""
    )
    date_published = parse_date_to_iso(date_raw)

    payload = {
        "link": url,
        "source_name": source_name,
        "title": title,
        "body": body,
        "date_published": date_published,
        "images": images,
        "author_list": author_list,
        "language": language,
        "description": description or "",
    }

    missing = [f for f in REQUIRED_FIELDS if f not in payload]
    if missing:
        raise ValueError(f"missing fields: {missing}")

    for f in ["link", "source_name", "title", "body", "date_published", "language"]:
        if not isinstance(payload[f], str) or not payload[f].strip():
            raise ValueError(f"invalid/empty field: {f}")

    for f in ["images", "author_list"]:
        if not isinstance(payload[f], list):
            raise ValueError(f"{f} must be a list")

    return payload

# ---------- Processing loop ----------
def process_one(conn, producer: KafkaProducer, row: dict) -> None:
    url = row["url"]
    log_event(log_worker, "worker.begin", url=url, status="running")
    zyte_article: Optional[Dict[str, Any]] = None
    attempted_payload: Optional[Dict[str, Any]] = None
    try:
        article = request_article(url)
        zyte_article = article if isinstance(article, dict) else None

        if article and not article.get("error"):
            attempted_payload = build_payload(url, article)
        else:
            err = article.get("error_message") if isinstance(article, dict) else "zyte returned error"
            raise RuntimeError(f"Zyte error: {err}")

        t0 = time.perf_counter()
        kafka_meta = push_to_kafka(producer, attempted_payload)
        dt_ms = int((time.perf_counter() - t0) * 1000)
        log_event(log_worker, "kafka.sent", url=url, duration_ms=dt_ms)

        log_event(
            log_worker,
            "payload.summary",
            url=url,
            title=attempted_payload.get("title"),
            date_published=attempted_payload.get("date_published"),
            source_name=attempted_payload.get("source_name"),
            body_len=len(attempted_payload.get("body", "")),
            images_count=len(attempted_payload.get("images", [])),
            authors=attempted_payload.get("author_list"),
            language=attempted_payload.get("language"),
        )

        mark_success(conn, url, attempted_payload, kafka_meta, zyte_article)
        log_event(log_worker, "status.transition", url=url, status="success")

    except Exception as e:
        # Persist what we have for debugging (article and/or attempted payload)
        mark_error(conn, url, str(e), zyte_article=zyte_article, attempted_payload=attempted_payload)
        log_event(log_worker, "status.transition", url=url, status="error", error=str(e))

def main():
    setup_logging()

    dsn = "postgresql://onm_admin:onmdb@localhost:5432/onm_db" #sys.argv[1] if len(sys.argv) == 2 else os.getenv("DATABASE_URL")
    if not dsn:
        print("ERROR: provide DSN arg or set DATABASE_URL")
        sys.exit(3)

    with connect_db(dsn) as conn:
        ensure_tables(conn)
        added = seed_pending_from_uris(conn)
        if added:
            log_event(log_seed, "seed.inserted", count=added, source_table=SOURCE_TABLE)
        else:
            log_event(log_seed, "seed.noop", source_table=SOURCE_TABLE)

        producer = make_producer()

        processed = 0
        while True:
            row = acquire_next_pending(conn)
            if row is None:
                break
            t0 = time.perf_counter()
            process_one(conn, producer, row)
            processed += 1
            dt_ms = int((time.perf_counter() - t0) * 1000)
            log_event(log_worker, "worker.end", url=row["url"], duration_ms=dt_ms)
            time.sleep(0.05)

        producer.flush()
        log_event(log_worker, "run.complete", processed=processed)
        print(f"Done. Processed: {processed}")

if __name__ == "__main__":
    main()
