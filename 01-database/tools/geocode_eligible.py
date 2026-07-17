#!/usr/bin/env python3
"""Add privacy-safe centroid coordinates to an eligible state handoff.

This stage only reads the derived ``eligible-entities.csv`` handoff.  It writes
another derived CSV and a summary beside it; contract files and evidence,
identity, and promotion fields are never changed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT_ROOT = ROOT / "data" / "exports" / "state-pipeline"
DEFAULT_CACHE = ROOT / "03-app" / "site" / "scripts" / "geocode-cache.json"

USER_AGENT = "FarmFinder/1.0 (+public-directory research; contact in repository)"
TIMEOUT_SECONDS = 45
ATTEMPTS = 3

# These are the Census geography endpoints already used by collect_southeast.py.
CENSUS_COUNTIES_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1/query?"
)
CENSUS_PLACES_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/"
    "TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/{layer}/query?"
)
CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress"

STATE_FIPS = {
    "AL": "01", "AR": "05", "AZ": "04", "CA": "06", "CO": "08",
    "CT": "09", "DC": "11", "DE": "10", "FL": "12", "GA": "13",
    "IA": "19", "ID": "16", "IL": "17", "IN": "18", "KS": "20",
    "KY": "21", "LA": "22", "MA": "25", "MD": "24", "ME": "23",
    "MI": "26", "MN": "27", "MO": "29", "MS": "28", "MT": "30",
    "NC": "37", "ND": "38", "NE": "31", "NH": "33", "NJ": "34",
    "NM": "35", "NV": "32", "NY": "36", "OH": "39", "OK": "40",
    "OR": "41", "PA": "42", "RI": "44", "SC": "45", "SD": "46",
    "TN": "47", "TX": "48", "UT": "49", "VA": "51", "VT": "50",
    "WA": "53", "WI": "55", "WV": "54", "WY": "56",
}

def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def geography_key(value: object) -> str:
    """Normalize Census names without changing the source value in the CSV."""

    text = unicodedata.normalize("NFKD", clean(value)).encode("ascii", "ignore").decode().casefold()
    text = re.sub(r"\b(?:county|parish|borough|census area|municipality)\b", " ", text)
    text = re.sub(r"\b(?:city|town|village|cdp)\b", " ", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def canonical_precision(classification: str) -> str:
    """Map the contract's public-location classification to the plan ladder."""

    value = clean(classification).casefold()
    if "farm_confirmed_exact" in value or "farm-confirmed" in value:
        return "farm_confirmed_exact"
    if "public_business_address" in value:
        return "public_business_address"
    if "city_centroid" in value or "city" in value:
        return "city_centroid"
    if "county_centroid" in value or "county" in value or "parish" in value:
        return "county_centroid"
    return "county_centroid"


def is_internal_only(row: dict[str, str]) -> bool:
    """Return true when the row lacks a public location classification."""

    classification = clean(row.get("public_location_classification", "")).casefold()
    return bool(row.get("address_internal", "").strip()) and (
        not classification
        or classification.startswith("internal")
        or "internal_only" in classification
    )


def request_json(
    url: str,
    *,
    attempts: int = ATTEMPTS,
    timeout: int = TIMEOUT_SECONDS,
    fetcher: Callable[[urllib.request.Request, int], bytes] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch JSON with the collector's three-attempt, 45-second convention."""

    errors: list[str] = []
    for attempt in range(1, attempts + 1):
        started = time.monotonic()
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            if fetcher is None:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    raw = response.read()
                    status = getattr(response, "status", 200)
            else:
                raw = fetcher(request, timeout)
                status = 200
            body = json.loads(raw.decode("utf-8", "replace"))
            if not isinstance(body, dict):
                raise ValueError("JSON response was not an object")
            return body, {
                "url": url,
                "attempts_used": attempt,
                "http_status": status,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "error": "",
            }
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"attempt {attempt}: {exc}")
            if attempt < attempts:
                time.sleep(0.8 * attempt)
    return {}, {
        "url": url,
        "attempts_used": attempts,
        "http_status": 0,
        "bytes": 0,
        "sha256": "",
        "elapsed_seconds": 0,
        "error": " | ".join(errors),
    }


def read_cache(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def write_cache(path: Path, cache: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Request payloads are transient implementation details.  The persistent
    # cache remains the compact city/county lookup cache used by reruns.
    compact = {key: value for key, value in cache.items() if not key.startswith("request|")}
    path.write_text(json.dumps(compact, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cached_json(
    url: str,
    cache: dict[str, Any],
    *,
    fetcher: Callable[[urllib.request.Request, int], bytes] | None = None,
    persist_response: bool = True,
) -> tuple[dict[str, Any], dict[str, Any], bool]:
    key = f"request|{url}"
    if persist_response:
        cached = cache.get(key)
        if isinstance(cached, dict) and "response" in cached:
            return cached.get("response", {}), cached.get("request", {"url": url}), True
    body, log = request_json(url, fetcher=fetcher)
    if persist_response:
        # Cache misses as well as hits so deterministic reruns do not repeatedly
        # call an unavailable or ambiguous Census geography.
        cache[key] = {"response": body, "request": log}
    return body, log, False


def census_url(base: str, params: dict[str, str]) -> str:
    return base + urllib.parse.urlencode(params)


def parse_centroid(attributes: dict[str, Any]) -> tuple[float, float] | None:
    try:
        latitude = float(attributes.get("INTPTLAT", ""))
        longitude = float(attributes.get("INTPTLON", ""))
    except (TypeError, ValueError):
        return None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    return latitude, longitude


def parse_features(body: dict[str, Any]) -> list[dict[str, Any]]:
    features = body.get("features", [])
    return [
        feature.get("attributes", {})
        for feature in features
        if isinstance(feature, dict) and isinstance(feature.get("attributes"), dict)
    ]


def load_counties(
    state: str,
    cache: dict[str, Any],
    *,
    fetcher: Callable[[urllib.request.Request, int], bytes] | None = None,
) -> tuple[dict[str, tuple[float, float]], dict[str, Any], bool]:
    fips = STATE_FIPS[state]
    url = census_url(CENSUS_COUNTIES_URL, {
        "where": f"STATE='{fips}'",
        "outFields": "NAME,BASENAME,STATE,COUNTY,GEOID,INTPTLAT,INTPTLON",
        "returnGeometry": "false",
        "f": "json",
    })
    body, log, cache_hit = cached_json(url, cache, fetcher=fetcher, persist_response=False)
    counties: dict[str, tuple[float, float]] = {}
    for attributes in parse_features(body):
        centroid = parse_centroid(attributes)
        if centroid is None:
            continue
        for value in (attributes.get("BASENAME"), attributes.get("NAME")):
            key = geography_key(value)
            if key:
                counties.setdefault(key, centroid)
    return counties, {"url": url, "request": log, "cache_hit": cache_hit}, cache_hit


def load_places(
    state: str,
    cache: dict[str, Any],
    *,
    fetcher: Callable[[urllib.request.Request, int], bytes] | None = None,
) -> tuple[dict[str, list[tuple[float, float]]], list[dict[str, Any]], int]:
    fips = STATE_FIPS[state]
    places: defaultdict[str, list[tuple[float, float]]] = defaultdict(list)
    logs: list[dict[str, Any]] = []
    cache_hits = 0
    # Incorporated places and CDPs cover the two Census place types that can
    # appear in an eligible row.  The returned INTPT coordinates are reduced-
    # precision internal points, never address geocodes.
    for layer in (4, 5):
        url = census_url(CENSUS_PLACES_URL.format(layer=layer), {
            "where": f"STATE='{fips}'",
            "outFields": "NAME,BASENAME,STATE,GEOID,INTPTLAT,INTPTLON",
            "returnGeometry": "false",
            "f": "json",
        })
        body, log, cache_hit = cached_json(url, cache, fetcher=fetcher, persist_response=False)
        cache_hits += int(cache_hit)
        logs.append({"url": url, "request": log, "cache_hit": cache_hit, "layer": layer})
        for attributes in parse_features(body):
            centroid = parse_centroid(attributes)
            if centroid is None:
                continue
            keys = {geography_key(attributes.get("BASENAME")), geography_key(attributes.get("NAME"))}
            for key in keys - {""}:
                if centroid not in places[key]:
                    places[key].append(centroid)
    return dict(places), logs, cache_hits


def legacy_city_cache_value(value: Any) -> tuple[float, float] | None:
    """Read the existing site cache's city entries without trusting precision."""

    if not isinstance(value, dict):
        return None
    try:
        return float(value["latitude"]), float(value["longitude"])
    except (KeyError, TypeError, ValueError):
        return None


def has_cached_result(value: Any) -> bool:
    return isinstance(value, dict) and (value.get("unresolved") is True or legacy_city_cache_value(value) is not None)


def choose_city(
    row: dict[str, str],
    places: dict[str, list[tuple[float, float]]],
) -> tuple[float, float] | None:
    candidates = places.get(geography_key(row.get("city", "")), [])
    if len(candidates) == 1:
        return candidates[0]
    # A city name can occur in multiple counties.  Since the handoff already
    # has county evidence, use it only when the Census place table leaves one
    # unambiguous match in that county.  The place endpoint does not return a
    # county for all places, so ambiguous names intentionally fall to county.
    return None


def geocode_rows(
    state: str,
    rows: list[dict[str, str]],
    cache: dict[str, Any],
    *,
    fetcher: Callable[[urllib.request.Request, int], bytes] | None = None,
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    state = state.upper()
    if state not in STATE_FIPS:
        raise ValueError(f"Unsupported state code: {state}")

    city_keys = {
        f"{geography_key(row.get('city', ''))}|{state}"
        for row in rows
        if clean(row.get("city", ""))
    }
    county_keys = {
        f"county|{geography_key(row.get('county_equivalent', ''))}|{state}"
        for row in rows
        if clean(row.get("county_equivalent", ""))
    }
    need_counties = any(not has_cached_result(cache.get(key)) for key in county_keys)
    need_places = any(not has_cached_result(cache.get(key)) for key in city_keys)
    counties: dict[str, tuple[float, float]] = {}
    places: dict[str, list[tuple[float, float]]] = {}
    county_log: dict[str, Any] = {"skipped": not need_counties, "cache_hit": not need_counties}
    place_logs: list[dict[str, Any]] = []
    place_cache_hits = 0
    if need_counties:
        counties, county_log, _ = load_counties(state, cache, fetcher=fetcher)
        for key, centroid in counties.items():
            cache.setdefault(f"county|{key}|{state}", {
                "latitude": centroid[0], "longitude": centroid[1],
                "precision": "county_centroid",
                "source": "U.S. Census Bureau — TIGERweb county internal point",
            })
    if need_places:
        places, place_logs, place_cache_hits = load_places(state, cache, fetcher=fetcher)
        for key, candidates in places.items():
            if len(candidates) == 1:
                centroid = candidates[0]
                cache.setdefault(f"{key}|{state}", {
                    "latitude": centroid[0], "longitude": centroid[1],
                    "precision": "city_centroid",
                    "source": "U.S. Census Bureau — TIGERweb place internal point",
                })
    # Persist empty lookups too.  This is important for deterministic reruns:
    # an ambiguous or absent city should proceed directly to county fallback.
    for key in city_keys:
        if key not in cache:
            city_name = key.rsplit("|", 1)[0]
            cache[key] = {"unresolved": True, "query": f"{city_name}, {state}"}
    for key in county_keys:
        if key not in cache:
            county_name = key.split("|", 2)[1]
            cache[key] = {"unresolved": True, "query": f"{county_name}, {state}"}
    output: list[dict[str, str]] = []
    precision_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    counts: Counter[str] = Counter()
    cache_hits = place_cache_hits + int(county_log["cache_hit"])
    legacy_cache_hits = 0

    for source_row in rows:
        row = dict(source_row)
        latitude = clean(row.get("latitude", ""))
        longitude = clean(row.get("longitude", ""))
        classification = clean(row.get("public_location_classification", ""))
        internal_only = is_internal_only(row)
        result: tuple[float, float] | None = None
        precision = ""
        source = ""
        query = ""

        if latitude and longitude and not internal_only:
            try:
                result = float(latitude), float(longitude)
            except ValueError:
                result = None
            if result is not None:
                precision = canonical_precision(classification)
                source = "eligible-entities.csv existing coordinates"
                query = "existing coordinates"
                counts["existing"] += 1

        city = clean(row.get("city", ""))
        city_key = f"{geography_key(city)}|{state}"
        if result is None and city:
            cached = legacy_city_cache_value(cache.get(city_key))
            if cached is not None:
                result = cached
                precision = "city_centroid"
                source = "03-app/site/scripts/geocode-cache.json"
                query = f"{city}, {state}"
                cache_hits += 1
                legacy_cache_hits += 1
                counts["city_centroid"] += 1
            else:
                result = choose_city(row, places)
                if result is not None:
                    precision = "city_centroid"
                    source = "U.S. Census Bureau — TIGERweb place internal point"
                    query = f"{city}, {state}"
                    counts["city_centroid"] += 1

        county = clean(row.get("county_equivalent", ""))
        if result is None and county:
            county_cache = legacy_city_cache_value(cache.get(f"county|{geography_key(county)}|{state}"))
            result = county_cache or counties.get(geography_key(county))
            if result is not None:
                precision = "county_centroid"
                source = "U.S. Census Bureau — TIGERweb county internal point"
                query = f"{county}, {state}"
                counts["county_centroid"] += 1

        if result is None:
            # This should only be possible for a malformed or unsupported
            # geography response.  Keep the row and make the gap visible in the
            # summary rather than inventing a coordinate.
            counts["unresolved"] += 1
            precision = ""
            source = ""
            query = f"{city or county}, {state}".strip(", ")
        else:
            precision_counts[precision] += 1
            source_counts[source] += 1

        row.update({
            "geocoded_latitude": f"{result[0]:.7f}" if result is not None else "",
            "geocoded_longitude": f"{result[1]:.7f}" if result is not None else "",
            "geocode_precision": precision,
            "geocode_source": source,
            "geocode_query": query,
        })
        output.append(row)

    summary = {
        "state": state,
        "input_rows": len(rows),
        "output_rows": len(output),
        "rows_with_coordinates": sum(precision_counts.values()),
        "unresolved_rows": counts["unresolved"],
        "target_met": counts["unresolved"] == 0 and len(output) == len(rows),
        "precision_counts": dict(sorted(precision_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "method_counts": dict(sorted(counts.items())),
        "cache_hits": cache_hits,
        "legacy_site_cache_hits": legacy_cache_hits,
        "requests": {
            "counties": county_log,
            "places": place_logs,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return output, summary


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run_state(
    state: str,
    *,
    input_root: Path = DEFAULT_INPUT_ROOT,
    cache_path: Path = DEFAULT_CACHE,
) -> dict[str, Any]:
    state = state.upper()
    state_dir = input_root / state
    input_path = state_dir / "eligible-entities.csv"
    output_path = state_dir / "geocoded-entities.csv"
    summary_path = state_dir / "geocode-summary.json"
    rows = read_rows(input_path)
    cache = read_cache(cache_path)
    output, summary = geocode_rows(state, rows, cache)
    write_rows(output_path, output)
    write_cache(cache_path, cache)
    summary.update({
        "input_file": str(input_path),
        "output_file": str(output_path),
        "cache_file": str(cache_path),
    })
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", help="Two-letter state code, for example AR or TN")
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_state(args.state, input_root=args.input_root.resolve(), cache_path=args.cache.resolve())
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["target_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
