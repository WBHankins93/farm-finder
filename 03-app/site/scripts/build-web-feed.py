#!/usr/bin/env python3
"""Generate the app's runtime feed, derived stats, and publication evidence.

Reads every committed ``01-database/pipeline/data/<ST>.json`` file, applies the
pipeline's publish projection (including its privacy gate), enforces the
publication contract in ``app/data/feed-contract.json``, and writes:

* ``public/national-index.bin`` — the compact column-oriented index the
  bounded ``/v1`` routes query. Served as a static asset rather than inlined
  in the worker bundle, so the deployed script stays small and no isolate
  retains a base64 copy of the dataset. See ``scripts/discovery_index.py``.
* ``app/data/directory-stats.generated.json`` — every count the public page
  displays, computed from the feed that was just published.
* ``public/farms.json`` — the 45 MB client-side feed for the rollback
  explorer. Written **only** when ``FARMFINDER_LEGACY_FEED=1``; Cloudflare
  rejects assets over 25 MiB, so it must never reach a default build.

All three outputs are regenerable and git-ignored. Reading the committed
per-state store directly makes a clean app build independent of a possibly
stale or test-contaminated ``pipeline/build/app-farms.json`` artifact.

    python3 scripts/build-web-feed.py
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from discovery_index import product_counts, write_index

HERE = Path(__file__).resolve().parent
SITE = HERE.parent
PIPELINE = HERE.parents[2] / "01-database" / "pipeline"
DATA = PIPELINE / "data"
PUBLIC_OUT = SITE / "public" / "farms.json"
INDEX_OUT = SITE / "public" / "national-index.bin"
STATS_OUT = SITE / "app" / "data" / "directory-stats.generated.json"
CONTRACT = SITE / "app" / "data" / "feed-contract.json"
VOCABULARY = SITE / "app" / "data" / "product-vocabulary.json"

SERVICE_KEYS = ("farmersMarket", "onFarm", "csa", "ships", "onlineStore")

# The publish projection's exact public shape. Anything outside this set in a
# published record is an internal field that escaped the projection.
PUBLIC_FIELDS = {
    "id", "name", "category", "region", "parish", "state", "city",
    "productsText", "products", "marketPresence", "website", "hasWebsite",
    "onlineStore", "facebook", "instagram", "farmersMarket", "csa", "ships",
    "onFarm", "contact", "notes", "source", "latitude", "longitude",
    "geoPrecision",
}

# A US street address in a field that is only ever allowed to hold phone/email.
ADDRESS_PATTERN = re.compile(
    r"\d{1,6}\s+[\w.'\- ]{2,40}\s+"
    r"(street|st|road|rd|avenue|ave|highway|hwy|lane|ln|drive|dr|court|ct|"
    r"boulevard|blvd|parkway|pkwy|route|rte|way|circle|cir|trail|trl)\b",
    re.IGNORECASE,
)


class ContractViolation(RuntimeError):
    """The feed failed a publication gate. Never write a partial artifact."""


def is_mappable(record: dict) -> bool:
    """Mirror of ``isMappableFarm`` in app/lib/discovery-server.ts."""
    return (
        record["geoPrecision"] != "ungeocoded"
        and not (record["latitude"] == 0 and record["longitude"] == 0)
    )


def build_records(expected_states: set[str]) -> list[dict]:
    sys.path.insert(0, str(PIPELINE))
    from model import Farm
    from publish import to_app_records

    state_files = sorted(DATA.glob("[A-Z][A-Z].json"))
    state_codes = {path.stem for path in state_files}
    if state_codes != expected_states:
        missing = sorted(expected_states - state_codes)
        unexpected = sorted(state_codes - expected_states)
        raise ContractViolation(
            f"national state files differ from the 50-state contract; "
            f"missing={missing}, unexpected={unexpected}"
        )

    farms = []
    ineligible = 0
    for path in state_files:
        rows = json.loads(path.read_text())
        wrong_states = sorted({row.get("state", "") for row in rows} - {path.stem})
        if wrong_states:
            raise ContractViolation(f"{path.name} contains records for {wrong_states}")
        parsed = [Farm.from_record(row) for row in rows]
        ineligible += sum(1 for farm in parsed if not farm.eligible)
        farms.extend(parsed)

    records, _merged = to_app_records(farms, eligible_only=True)
    print(
        f"publication gates: {len(farms)} collected → {len(records)} eligible "
        f"({ineligible} withheld by QA/eligibility)"
    )
    return records


def enforce_contract(records: list[dict], contract: dict) -> None:
    """Fail the build on any privacy or coverage violation.

    These are publication gates, not warnings: a violated gate means an
    artifact that must not be written, so every failure raises.
    """
    failures: list[str] = []

    states = {record["state"] for record in records}
    expected = set(contract["expectedStates"])
    if states != expected:
        failures.append(
            f"published states != contract: missing={sorted(expected - states)}, "
            f"unexpected={sorted(states - expected)}"
        )

    floors = contract["floors"]
    mappable = sum(1 for record in records if is_mappable(record))
    if len(records) < floors["total"]:
        failures.append(f"total {len(records)} below floor {floors['total']}")
    if mappable < floors["mappable"]:
        failures.append(f"mappable {mappable} below floor {floors['mappable']}")
    if len(states) < floors["statesWithFarms"]:
        failures.append(f"{len(states)} states below floor {floors['statesWithFarms']}")

    # Privacy gates, evaluated over every published record.
    leaked_contact = [r["id"] for r in records if r["contact"] and not r["website"]]
    leaked_address = [r["id"] for r in records if ADDRESS_PATTERN.search(r["contact"])]
    zero_island = [
        r["id"] for r in records
        if r["geoPrecision"] != "ungeocoded" and r["latitude"] == 0 and r["longitude"] == 0
    ]
    extra_fields = sorted(
        {key for record in records for key in record} - PUBLIC_FIELDS
    )
    missing_provenance = [r["id"] for r in records if not r["source"]]

    if leaked_contact:
        failures.append(
            f"{len(leaked_contact)} records publish a contact without a farm-published "
            f"website (privacy.py promotes contacts only for website-publishing farms); "
            f"first={leaked_contact[:3]}"
        )
    if leaked_address:
        failures.append(
            f"{len(leaked_address)} public contacts look like street addresses; "
            f"first={leaked_address[:3]}"
        )
    if zero_island:
        failures.append(
            f"{len(zero_island)} geocoded records sit at 0,0; first={zero_island[:3]}"
        )
    if extra_fields:
        failures.append(f"published records carry non-public fields: {extra_fields}")
    if missing_provenance:
        failures.append(
            f"{len(missing_provenance)} records have no source provenance; "
            f"first={missing_provenance[:3]}"
        )

    if failures:
        raise ContractViolation(
            "publication contract failed:\n  - " + "\n  - ".join(failures)
        )

    print(
        f"privacy gates: 0 contacts without a public website, 0 address-shaped "
        f"contacts, 0 null-island points, 0 internal fields, "
        f"{len(records)}/{len(records)} records carry provenance"
    )


def compute_stats(records: list[dict], contract: dict, vocabulary: dict) -> dict:
    """Every number the public page shows, derived from the published feed."""
    # Summed from the same bitmask the app filters on, so the browse tiles and
    # the filtered results can never disagree.
    products = product_counts(records, vocabulary, contract["productGuideIds"])

    precisions: dict[str, int] = {}
    for record in records:
        precisions[record["geoPrecision"]] = precisions.get(record["geoPrecision"], 0) + 1

    return {
        "_comment": (
            "Generated by scripts/build-web-feed.py from the feed it published. "
            "Do not edit and do not commit; every value is derived."
        ),
        "releaseId": contract["releaseId"],
        "updatedLabel": contract["updatedLabel"],
        "total": len(records),
        "states": len({record["state"] for record in records}),
        "mappable": sum(1 for record in records if is_mappable(record)),
        "cityLevel": precisions.get("city", 0),
        "countyApprox": precisions.get("county-approx", 0),
        "farmGate": precisions.get("point", 0),
        "ungeocoded": precisions.get("ungeocoded", 0),
        "withoutWebsite": sum(1 for record in records if not record["website"]),
        "withPublicContact": sum(1 for record in records if record["contact"]),
        "geoPrecision": dict(sorted(precisions.items())),
        "services": {
            key: sum(1 for record in records if record[key]) for key in SERVICE_KEYS
        },
        "products": products,
    }


def main() -> int:
    if not DATA.exists():
        print(f"missing canonical data store: {DATA}", file=sys.stderr)
        return 1

    contract = json.loads(CONTRACT.read_text())
    vocabulary = json.loads(VOCABULARY.read_text())

    try:
        feed = build_records(set(contract["expectedStates"]))
        enforce_contract(feed, contract)
    except ContractViolation as error:
        print(f"\nBUILD BLOCKED — {error}", file=sys.stderr)
        return 1

    report = write_index(feed, contract, vocabulary, INDEX_OUT)
    print(
        f"wrote {INDEX_OUT.relative_to(SITE)} — {report['records']} farms, "
        f"{report['compressedBytes'] / 1e6:.1f} MB on disk, "
        f"{report['containerBytes'] / 1e6:.1f} MB resident "
        f"(search {report['searchBlobBytes'] / 1e6:.1f} MB, "
        f"display {report['displayBlobBytes'] / 1e6:.1f} MB, "
        f"columns {report['columnBytes'] / 1e6:.1f} MB, "
        f"{report['places']} places)"
    )

    stats = compute_stats(feed, contract, vocabulary)
    STATS_OUT.write_text(json.dumps(stats, indent=2) + "\n")
    print(
        f"wrote {STATS_OUT.relative_to(SITE)} — {stats['total']} farms, "
        f"{stats['states']} states, {stats['mappable']} mappable"
    )

    # Cloudflare rejects static assets over 25 MiB and this feed is ~45 MB, so
    # a default build must not produce it. Opt in only to exercise the rollback
    # explorer locally.
    if os.environ.get("FARMFINDER_LEGACY_FEED") == "1":
        PUBLIC_OUT.parent.mkdir(parents=True, exist_ok=True)
        PUBLIC_OUT.write_text(json.dumps(feed, separators=(",", ":"), ensure_ascii=False))
        print(
            f"wrote {PUBLIC_OUT.relative_to(SITE)} — {len(feed)} farms, "
            f"{PUBLIC_OUT.stat().st_size / 1e6:.1f} MB "
            f"(rollback explorer only; too large to deploy)"
        )
    elif PUBLIC_OUT.exists():
        PUBLIC_OUT.unlink()
        print(
            f"removed stale {PUBLIC_OUT.relative_to(SITE)} "
            f"(set FARMFINDER_LEGACY_FEED=1 to rebuild it)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
