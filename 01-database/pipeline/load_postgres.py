"""Postgres sink — full-refresh load of the published app feed into a local DB.

Zero third-party deps: shells out to the `psql` client (stdlib `subprocess` +
`csv` + `json`). This is the real, zero-cost implementation of what
`publish.load_postgres` stubbed out — Postgres only, no S3 evidence bundle.

    python3 load_postgres.py --init       # create the db + table (one-time)
    python3 load_postgres.py --refresh    # full-refresh farms from build/app-farms.json

`run.py --publish` writes `build/app-farms.json` as a complete national snapshot
of every eligible, privacy-cleared record, so a load is always a full refresh:
TRUNCATE + COPY inside one transaction. Idempotent — re-running yields the same
table. The map/query columns are promoted out of the record; the whole record is
kept in a `data` jsonb column so nothing is lost.

Connection: `DATABASE_URL` if set, else local db `farmfinder` (override with
`FARMFINDER_DB`). Local Postgres is free; nothing here talks to a paid service.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
DEFAULT_FEED = BUILD / "app-farms.json"
LOAD_CSV = BUILD / "farms-load.csv"

# app-record key -> promoted CSV/table column. Everything also lands in `data`.
COLUMNS = [
    ("id", "id"),
    ("name", "name"),
    ("state", "state"),
    ("category", "category"),
    ("region", "region"),
    ("parish", "county"),
    ("city", "city"),
    ("contact", "contact"),
    ("website", "website"),
    ("source", "source"),
    ("latitude", "latitude"),
    ("longitude", "longitude"),
    ("geoPrecision", "geo_precision"),
]

DDL = """
CREATE TABLE IF NOT EXISTS farms (
  id            text PRIMARY KEY,
  name          text NOT NULL,
  state         text,
  category      text,
  region        text,
  county        text,
  city          text,
  contact       text,
  website       text,
  source        text,
  latitude      double precision,
  longitude     double precision,
  geo_precision text,
  mappable      boolean,
  data          jsonb NOT NULL,
  loaded_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS farms_state_idx    ON farms(state);
CREATE INDEX IF NOT EXISTS farms_category_idx ON farms(category);
"""

CSV_HEADER = [col for _, col in COLUMNS] + ["mappable", "data"]


def db_name() -> str:
    return os.environ.get("FARMFINDER_DB", "farmfinder")


def psql_argv(extra: list[str]) -> list[str]:
    """psql invocation targeting DATABASE_URL, else the local farmfinder db."""
    dsn = os.environ.get("DATABASE_URL")
    conn = [dsn] if dsn else ["-d", db_name()]
    return ["psql", "-v", "ON_ERROR_STOP=1", "-q", *conn, *extra]


def run_sql(sql: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        psql_argv([]), input=sql, text=True, capture_output=True
    )


def ensure_db() -> None:
    """createdb if the local db is absent (skipped when DATABASE_URL is set —
    a provided DSN is assumed to already point at a live database)."""
    if os.environ.get("DATABASE_URL"):
        return
    name = db_name()
    check = subprocess.run(
        ["psql", "-lqt"], text=True, capture_output=True
    )
    have = any(line.split("|")[0].strip() == name for line in check.stdout.splitlines())
    if not have:
        made = subprocess.run(["createdb", name], text=True, capture_output=True)
        if made.returncode != 0:
            print(made.stderr, file=sys.stderr)
            raise SystemExit(f"could not create database '{name}'")
        print(f"created database '{name}'")


def init() -> None:
    ensure_db()
    res = run_sql(DDL)
    if res.returncode != 0:
        print(res.stderr, file=sys.stderr)
        raise SystemExit("failed to create table")
    print("farms table ready")


def write_csv(feed: Path) -> int:
    records = json.loads(feed.read_text())
    BUILD.mkdir(parents=True, exist_ok=True)
    with LOAD_CSV.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_HEADER)
        for r in records:
            row = [r.get(key) for key, _ in COLUMNS]
            mappable = r.get("geoPrecision") != "ungeocoded"
            row.append("true" if mappable else "false")
            row.append(json.dumps(r, ensure_ascii=False))
            w.writerow(row)
    return len(records)


def refresh(feed: Path) -> None:
    if not feed.exists():
        raise SystemExit(f"no feed to load: {feed} (run: python3 run.py --publish)")
    ensure_db()
    n = write_csv(feed)
    cols = ",".join(CSV_HEADER)
    sql = (
        "BEGIN;\n"
        + DDL
        + "TRUNCATE farms;\n"
        + f"\\copy farms ({cols}) FROM '{LOAD_CSV}' WITH (FORMAT csv, HEADER true)\n"
        + "COMMIT;\n"
    )
    res = run_sql(sql)
    if res.returncode != 0:
        print(res.stderr, file=sys.stderr)
        raise SystemExit("load failed — table left unchanged (transaction rolled back)")
    count = subprocess.run(
        psql_argv(["-tA", "-c", "SELECT count(*) FROM farms;"]),
        text=True, capture_output=True,
    )
    loaded = count.stdout.strip() if count.returncode == 0 else "?"
    target = "DATABASE_URL" if os.environ.get("DATABASE_URL") else db_name()
    print(f"refreshed farms: {n} records from {feed.name} -> {loaded} rows in db '{target}'")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--init", action="store_true", help="create db + table, then exit")
    p.add_argument("--refresh", action="store_true", help="full-refresh load from the app feed")
    p.add_argument("--input", default=str(DEFAULT_FEED), help="app feed json (default build/app-farms.json)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not (args.init or args.refresh):
        raise SystemExit("nothing to do: pass --init and/or --refresh")
    if args.init:
        init()
    if args.refresh:
        refresh(Path(args.input))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
