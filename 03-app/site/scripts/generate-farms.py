#!/usr/bin/env python3
"""Build the public FarmFinder dataset from the current research workbook.

The script merges duplicate farm names, carries forward the verified coordinates
from the 235-farm dashboard, and optionally geocodes only the new city/state
combinations. Geocoder responses are cached so repeat builds stay offline.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd


SITE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SITE_ROOT.parents[1]
WORKBOOK = REPO_ROOT / "research" / "local_farm_database_final.xlsx"
DASHBOARD = REPO_ROOT / "farmfinder-dashboard-v2.html"
OUTPUT = SITE_ROOT / "app" / "data" / "farms.json"
CACHE = SITE_ROOT / "scripts" / "geocode-cache.json"


def clean(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return ""
    return str(value).strip()


def key(value: object) -> str:
    return clean(value).casefold()


def slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value.casefold()).strip("-")
    return slug or "farm"


def yes(value: object) -> bool:
    return key(value) in {"yes", "y", "true", "1"}


def unique_join(values: list[object], separator: str = "; ") -> str:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = clean(value)
        if item and item.casefold() not in seen:
            seen.add(item.casefold())
            result.append(item)
    return separator.join(result)


def load_verified_geocodes() -> tuple[dict[str, dict], dict[tuple[str, str], dict]]:
    html = DASHBOARD.read_text()
    match = re.search(
        r'<script id="data" type="application/json">(.*?)</script>', html, re.S
    )
    if not match:
        raise RuntimeError("Could not find dashboard data payload")
    payload = json.loads(match.group(1))
    by_name: dict[str, dict] = {}
    by_city: dict[tuple[str, str], dict] = {}
    for block in payload["farmSheets"].values():
        for row in block["rows"]:
            record = dict(zip(block["headers"], row))
            location = {
                "latitude": record["Latitude"],
                "longitude": record["Longitude"],
                "precision": record["Geo Precision"],
                "source": record["Geo Source"],
            }
            by_name[key(record["Farm Name"])] = location
            by_city[(key(record["City/Town"]), clean(record["State"]))] = location
    return by_name, by_city


GEOCODE_ALIASES = {
    ("central ms", "MS"): "Jackson, Mississippi",
    ("s. mississippi", "MS"): "Hattiesburg, Mississippi",
    ("n. mississippi", "MS"): "Tupelo, Mississippi",
    ("multiple", "LA"): "Alexandria, Louisiana",
    ("lafayette area", "LA"): "Lafayette, Louisiana",
    ("tylertown area", "MS"): "Tylertown, Mississippi",
    ("hickory/pearl river", "LA"): "Pearl River, Louisiana",
    ("se louisiana", "LA"): "Hammond, Louisiana",
}

# Evidence-backed corrections that must outrank the historical dashboard's by-name
# coordinates. Both farms participate in New Orleans markets but are located in
# Poplarville, Mississippi.
LOCATION_OVERRIDES = {
    "fat cat farm": {
        "latitude": 30.8401495,
        "longitude": -89.5342315,
        "precision": "city",
        "source": "OpenStreetMap Nominatim",
    },
    "pearl river pastures": {
        "latitude": 30.8401495,
        "longitude": -89.5342315,
        "precision": "city",
        "source": "OpenStreetMap Nominatim",
    },
}


def geocode_city(city: str, state: str) -> dict | None:
    query = GEOCODE_ALIASES.get((key(city), state), f"{city}, {state}, USA")
    params = urllib.parse.urlencode(
        {"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "us"}
    )
    request = urllib.request.Request(
        f"https://nominatim.openstreetmap.org/search?{params}",
        headers={"User-Agent": "FarmFinder/0.1 data build"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        results = json.load(response)
    if not results:
        return None
    result = results[0]
    return {
        "latitude": float(result["lat"]),
        "longitude": float(result["lon"]),
        "precision": "city" if "city" not in key(city) and "mississippi" not in key(city) else "region",
        "source": "OpenStreetMap Nominatim",
    }


def normalize_website(value: object) -> str:
    url = clean(value)
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    return url


def product_terms(value: str) -> list[str]:
    terms = re.split(r"[,;/]|\band\b|\bwith\b", value, flags=re.I)
    result: list[str] = []
    seen: set[str] = set()
    for term in terms:
        term = re.sub(r"\([^)]*\)", "", term).strip(" .-")
        if term and len(term) <= 48 and term.casefold() not in seen:
            seen.add(term.casefold())
            result.append(term)
    return result[:14]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--geocode",
        action="store_true",
        help="Look up city/state combinations not already present in the local cache",
    )
    args = parser.parse_args()

    verified_by_name, verified_by_city = load_verified_geocodes()
    cache: dict[str, dict] = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    frame = pd.read_excel(WORKBOOK, sheet_name="All Farms")
    frame["_name_key"] = frame["Farm Name"].map(key)

    locations: dict[str, dict] = {}
    unresolved: list[tuple[str, str]] = []
    for _, row in frame.iterrows():
        name_key = row["_name_key"]
        city_key = (key(row["City/Town"]), clean(row["State"]))
        cache_key = "|".join(city_key)
        location = (
            LOCATION_OVERRIDES.get(name_key)
            or verified_by_name.get(name_key)
            or verified_by_city.get(city_key)
            or cache.get(cache_key)
        )
        if not location and city_key not in unresolved:
            unresolved.append(city_key)
        if location:
            locations[name_key] = location

    if args.geocode and unresolved:
        for index, (city_key, state) in enumerate(unresolved):
            city = next(
                clean(value)
                for value in frame.loc[
                    (frame["City/Town"].map(key) == city_key)
                    & (frame["State"].map(clean) == state),
                    "City/Town",
                ]
            )
            try:
                result = geocode_city(city, state)
            except Exception as exc:  # keep the existing build usable during API issues
                print(f"Geocode failed for {city}, {state}: {exc}")
                result = None
            if result:
                cache[f"{city_key}|{state}"] = result
                for name_key in frame.loc[
                    (frame["City/Town"].map(key) == city_key)
                    & (frame["State"].map(clean) == state),
                    "_name_key",
                ]:
                    locations[name_key] = result
            if index < len(unresolved) - 1:
                time.sleep(1.1)
        CACHE.write_text(json.dumps(cache, indent=2, sort_keys=True) + "\n")

    records: list[dict] = []
    used_slugs: set[str] = set()
    for name_key, group in frame.groupby("_name_key", sort=False):
        first = group.iloc[0]
        location = locations.get(name_key)
        if not location:
            city_key = (key(first["City/Town"]), clean(first["State"]))
            location = cache.get("|".join(city_key))
        if not location:
            print(f"Skipping unmapped farm: {clean(first['Farm Name'])}")
            continue

        name = clean(first["Farm Name"])
        slug = slugify(name)
        if slug in used_slugs:
            slug = f"{slug}-{clean(first['State']).casefold()}"
        used_slugs.add(slug)

        products_text = unique_join(group["Products"].tolist())
        website = next(
            (normalize_website(value) for value in group["Website URL"] if clean(value)),
            "",
        )
        record = {
            "id": slug,
            "name": name,
            "category": clean(first["Category"]) or "Farm",
            "region": clean(first["Region/Zone"]),
            "parish": clean(first["Parish/County"]),
            "state": clean(first["State"]),
            "city": clean(first["City/Town"]),
            "productsText": products_text,
            "products": product_terms(products_text),
            "marketPresence": unique_join(group["Market Presence"].tolist()),
            "website": website,
            "hasWebsite": any(yes(value) for value in group["Has Website"]),
            "onlineStore": any(yes(value) for value in group["Has Online Store"]),
            "facebook": any(yes(value) for value in group["Has Facebook"]),
            "instagram": any(yes(value) for value in group["Has Instagram"]),
            "farmersMarket": any(yes(value) for value in group["Sells at Farmers Market"]),
            "csa": any(yes(value) for value in group["Offers CSA"]),
            "ships": any(yes(value) for value in group["Ships Products"]),
            "onFarm": any(yes(value) for value in group["On-Farm Sales"]),
            "contact": unique_join(group["Contact Info"].tolist(), " · "),
            "notes": unique_join(group["Notes"].tolist()),
            "source": unique_join(group["Source Tab"].tolist()),
            "recordId": clean(first.get("Record ID")),
            "recordStatus": clean(first.get("Record Status")),
            "websiteVerificationStatus": clean(first.get("Website Verification Status")),
            "facebookUrl": clean(first.get("Facebook URL")),
            "instagramUrl": clean(first.get("Instagram URL")),
            "contactStatus": clean(first.get("Contact Status")),
            "lastVerified": clean(first.get("Last Verified")),
            "verificationSource": clean(first.get("Verification Source")),
            "identityNotes": clean(first.get("Identity Notes")),
            "latitude": round(float(location["latitude"]), 6),
            "longitude": round(float(location["longitude"]), 6),
            "geoPrecision": clean(location["precision"]),
        }
        records.append(record)

    records.sort(key=lambda item: item["name"].casefold())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n")
    print(
        f"Wrote {len(records)} unique farms to {OUTPUT.relative_to(SITE_ROOT)} "
        f"({len(unresolved)} city/state combinations needed cache or geocoding)."
    )


if __name__ == "__main__":
    main()
