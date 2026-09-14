#!/usr/bin/env python3
"""Build the compact discovery index the bounded ``/v1`` routes query.

Why this exists
---------------
The obvious implementation — expand the published feed into 68,618 JavaScript
objects once per worker isolate — measures at ~152 MB retained. A Cloudflare
Workers isolate is capped at 128 MB, so that design passes locally under Node
and then fails on the deploy target.

This module emits a column-oriented binary index instead:

* numeric and boolean facets live in typed arrays (~3 MB total),
* searchable text lives in one packed ASCII-folded blob queried with
  ``String.prototype.indexOf`` (no per-record strings),
* display text lives in packed UTF-8 bytes, decoded only for the handful of
  records a response actually returns,
* place centroids and dataset totals are precomputed here rather than derived
  by walking every record at isolate start.

The result is served as a static asset, not inlined in the worker bundle, so
the deployed script stays small and no base64 copy of the dataset is retained.

Container layout (little-endian), every section padded to an 8-byte boundary so
the runtime can create typed-array views without copying:

    magic       8 bytes   "FFIDX1\\0\\0"
    headerLen   uint32    byte length of the header JSON
    header      utf-8     JSON: counts, lookup tables, section offsets
    sections    ...       raw section bytes at the offsets the header names

The whole container is gzip-compressed on disk: it keeps the asset under
Cloudflare's 25 MiB per-file limit, and the runtime inflates it once.
"""
from __future__ import annotations

import gzip
import json
import re
import struct
import unicodedata
from pathlib import Path

MAGIC = b"FFIDX1\0\0"
ALIGNMENT = 8

# Bit positions in the per-record `flags` column. Mirrored by
# app/lib/discovery-index.ts — change both together.
FLAG_BITS = {
    "farmersMarket": 0,
    "onFarm": 1,
    "csa": 2,
    "ships": 3,
    "onlineStore": 4,
    "hasWebsite": 5,
    "facebook": 6,
    "instagram": 7,
    "mappable": 8,
}

# Order of the packed display fields. Mirrored by app/lib/discovery-index.ts.
DISPLAY_FIELDS = (
    "id", "name", "category", "region", "parish", "state", "city",
    "productsText", "products", "marketPresence", "website", "contact",
    "notes", "source",
)

UNIT_SEPARATOR = "\x01"   # between display fields
LIST_SEPARATOR = "\x02"   # between entries of the `products` list


def fold_ascii(value: str) -> str:
    """Lowercase and strip to ASCII.

    The search blob must be pure ASCII so V8 keeps it in its one-byte string
    representation: a single non-ASCII character would double the blob's
    resident size. ``app/lib/discovery-index.ts::foldAscii`` performs the same
    transformation on incoming queries, so the two must stay in lockstep.
    """
    lowered = value.casefold()
    decomposed = unicodedata.normalize("NFKD", lowered)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return stripped.encode("ascii", "ignore").decode("ascii")


def name_sort_key(record: dict) -> tuple[str, str, str]:
    """Deterministic alphabetical key for a farm name.

    Folds case and diacritics and ignores leading punctuation so "'"Health
    Happens'" Farmers' Market" files under H, then falls back to the raw name
    and id so the order is total.
    """
    folded = re.sub(r"\s+", " ", fold_ascii(record["name"])).strip()
    leading = re.sub(r"^[^a-z0-9]+", "", folded)
    return (leading or folded, record["name"], record["id"])


def is_mappable(record: dict) -> bool:
    return (
        record["geoPrecision"] != "ungeocoded"
        and not (record["latitude"] == 0 and record["longitude"] == 0)
    )


def _pad(buffer: bytearray) -> None:
    while len(buffer) % ALIGNMENT:
        buffer.append(0)


class _Sections:
    """Accumulates named byte sections and records their offsets."""

    def __init__(self) -> None:
        self.body = bytearray()
        self.index: dict[str, dict[str, int]] = {}

    def add(self, name: str, payload: bytes) -> None:
        _pad(self.body)
        self.index[name] = {"offset": len(self.body), "length": len(payload)}
        self.body.extend(payload)


def product_haystack(record: dict) -> str:
    """The text a product filter matches against."""
    return " ".join([
        record["productsText"], " ".join(record["products"]),
        record["category"], record["notes"],
    ]).lower()


def _token_matcher(vocabulary: dict):
    """Compile each vocabulary token into a matcher.

    Most tokens are deliberate prefixes ("apiar" catches apiary/apiaries,
    "berr" catches berry/berries), so plain substring matching is right for
    them. A few are ordinary words that are also substrings of unrelated ones,
    and those are listed in `wholeWordTokens` and matched at word boundaries
    with an optional plural — otherwise "bee" tags every beef producer as a
    honey producer.
    """
    whole_word = set(vocabulary.get("wholeWordTokens", []))
    compiled: dict[str, list] = {}
    for key, tokens in vocabulary["productTokens"].items():
        matchers = []
        for token in tokens:
            if token in whole_word:
                pattern = re.compile(rf"(?<![a-z0-9]){re.escape(token)}s?(?![a-z0-9])")
                matchers.append(pattern.search)
            else:
                matchers.append(lambda haystack, token=token: token in haystack)
        compiled[key] = matchers
    return compiled


def _product_masks(records: list[dict], vocabulary: dict, product_ids: list[str]) -> list[int]:
    """Precompute the product-filter bitmask.

    The app filters on this mask and the public product counts are summed from
    it, which is what keeps a browsed count and a filtered result set from ever
    disagreeing.
    """
    matchers = _token_matcher(vocabulary)
    masks = []
    for record in records:
        haystack = product_haystack(record)
        mask = 0
        for position, key in enumerate(product_ids):
            if any(matches(haystack) for matches in matchers[key]):
                mask |= 1 << position
        masks.append(mask)
    return masks


def product_counts(records: list[dict], vocabulary: dict, product_ids: list[str]) -> dict[str, int]:
    """Public product counts, summed from the same masks the app filters on."""
    masks = _product_masks(records, vocabulary, product_ids)
    return {
        product: sum(1 for mask in masks if mask & (1 << position))
        for position, product in enumerate(product_ids)
    }


def _places(records: list[dict]) -> list[dict]:
    """City centroids for the place autocomplete, averaged over mappable rows.

    Precomputed so an isolate never has to walk the full record set to answer
    the first autocomplete keystroke.
    """
    grouped: dict[str, dict] = {}
    for record in records:
        city = record["city"].strip()
        state = record["state"].strip().upper()
        if not city or not state:
            continue
        slug = f"{fold_ascii(city).replace(' ', '-')}-{state.lower()}"
        slug = "-".join(part for part in slug.split("-") if part)
        entry = grouped.setdefault(
            slug,
            {"city": city, "state": state, "lat": 0.0, "lng": 0.0, "mappable": 0, "farms": 0},
        )
        entry["farms"] += 1
        if is_mappable(record):
            entry["lat"] += record["latitude"]
            entry["lng"] += record["longitude"]
            entry["mappable"] += 1

    places = [
        {
            "slug": slug,
            "name": entry["city"],
            "state": entry["state"],
            "label": f"{entry['city']}, {entry['state']}",
            "lat": entry["lat"] / entry["mappable"],
            "lng": entry["lng"] / entry["mappable"],
            "farmCount": entry["farms"],
        }
        for slug, entry in grouped.items()
        if entry["mappable"] > 0
    ]
    places.sort(key=lambda place: (-place["farmCount"], place["label"]))
    return places


def build_container(records: list[dict], contract: dict, vocabulary: dict) -> tuple[bytes, dict]:
    count = len(records)
    product_ids = list(contract["productGuideIds"])

    categories: list[str] = []
    precisions: list[str] = []
    category_index: dict[str, int] = {}
    precision_index: dict[str, int] = {}

    latitudes = bytearray()
    longitudes = bytearray()
    flags = bytearray()
    category_column = bytearray()
    precision_column = bytearray()
    product_column = bytearray()

    search_parts: list[str] = []
    text_start: list[int] = []
    name_end: list[int] = []
    products_end: list[int] = []
    place_end: list[int] = []

    display_parts: list[bytes] = []
    display_start: list[int] = []

    masks = _product_masks(records, vocabulary, product_ids)

    text_cursor = 0
    display_cursor = 0

    for position, record in enumerate(records):
        if record["category"] not in category_index:
            category_index[record["category"]] = len(categories)
            categories.append(record["category"])
        if record["geoPrecision"] not in precision_index:
            precision_index[record["geoPrecision"]] = len(precisions)
            precisions.append(record["geoPrecision"])

        latitudes.extend(struct.pack("<d", record["latitude"]))
        longitudes.extend(struct.pack("<d", record["longitude"]))

        bits = 0
        for key, bit in FLAG_BITS.items():
            if key == "mappable":
                value = is_mappable(record)
            elif key == "hasWebsite":
                value = bool(record["website"])
            else:
                value = bool(record[key])
            if value:
                bits |= 1 << bit
        flags.extend(struct.pack("<H", bits))
        category_column.append(category_index[record["category"]])
        precision_column.append(precision_index[record["geoPrecision"]])
        product_column.extend(struct.pack("<H", masks[position]))

        # Four weighted search fields, packed contiguously. The runtime scores
        # a hit by which field range its offset falls in.
        name_text = fold_ascii(record["name"])
        products_text = fold_ascii(f"{record['productsText']} {' '.join(record['products'])}")
        place_text = fold_ascii(
            f"{record['city']} {record['state']} {record['parish']} {record['region']}"
        )
        other_text = fold_ascii(
            f"{record['category']} {record['marketPresence']} {record['notes']}"
        )

        text_start.append(text_cursor)
        text_cursor += len(name_text)
        name_end.append(text_cursor)
        text_cursor += 1 + len(products_text)
        products_end.append(text_cursor)
        text_cursor += 1 + len(place_text)
        place_end.append(text_cursor)
        text_cursor += 1 + len(other_text)
        search_parts.append(f"{name_text} {products_text} {place_text} {other_text}")

        display = UNIT_SEPARATOR.join(
            LIST_SEPARATOR.join(record[field]) if field == "products" else str(record[field])
            for field in DISPLAY_FIELDS
        ).encode("utf-8")
        display_start.append(display_cursor)
        display_cursor += len(display)
        display_parts.append(display)

    text_start.append(text_cursor)
    display_start.append(display_cursor)

    search_blob = "".join(search_parts).encode("ascii")
    assert len(search_blob) == text_cursor, "search blob length disagrees with its offsets"
    display_blob = b"".join(display_parts)

    # Records sorted by a folded, punctuation-leading-trimmed name;
    # `nameRank[i]` lets the runtime order a matched subset by name with an
    # integer compare instead of a string one.
    #
    # This ordering is deliberately precomputed rather than left to
    # `String.localeCompare` at request time: cursor pagination needs one total
    # order, and localeCompare's result depends on the runtime's default locale,
    # which is not guaranteed to be the same in a Worker as it is under Node.
    order = sorted(range(count), key=lambda i: name_sort_key(records[i]))
    name_rank = [0] * count
    for rank, original in enumerate(order):
        name_rank[original] = rank

    places = _places(records)

    sections = _Sections()
    sections.add("latitude", bytes(latitudes))
    sections.add("longitude", bytes(longitudes))
    sections.add("flags", bytes(flags))
    sections.add("category", bytes(category_column))
    sections.add("precision", bytes(precision_column))
    sections.add("productMask", bytes(product_column))
    sections.add("nameRank", struct.pack(f"<{count}I", *name_rank))
    sections.add("textStart", struct.pack(f"<{count + 1}I", *text_start))
    sections.add("textNameEnd", struct.pack(f"<{count}I", *name_end))
    sections.add("textProductsEnd", struct.pack(f"<{count}I", *products_end))
    sections.add("textPlaceEnd", struct.pack(f"<{count}I", *place_end))
    sections.add("searchBlob", search_blob)
    sections.add("displayStart", struct.pack(f"<{count + 1}I", *display_start))
    sections.add("displayBlob", display_blob)
    sections.add("places", json.dumps(places, separators=(",", ":")).encode("utf-8"))

    header = {
        "version": 1,
        "count": count,
        "releaseId": contract["releaseId"],
        "states": sorted({record["state"] for record in records}),
        "categories": categories,
        "precisions": precisions,
        "productIds": product_ids,
        "flagBits": FLAG_BITS,
        "displayFields": list(DISPLAY_FIELDS),
        "placeCount": len(places),
        "sections": sections.index,
    }
    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")

    prefix = bytearray(MAGIC + struct.pack("<I", len(header_bytes)) + header_bytes)
    _pad(prefix)
    # Section offsets are relative to the start of the body, which the prefix
    # padding has just aligned, so the views stay aligned in the runtime too.
    container = bytes(prefix) + bytes(sections.body)

    report = {
        "records": count,
        "places": len(places),
        "searchBlobBytes": len(search_blob),
        "displayBlobBytes": len(display_blob),
        "columnBytes": sum(
            entry["length"]
            for name, entry in sections.index.items()
            if name not in {"searchBlob", "displayBlob", "places"}
        ),
        "containerBytes": len(container),
    }
    return container, report


def write_index(records: list[dict], contract: dict, vocabulary: dict, path: Path) -> dict:
    container, report = build_container(records, contract, vocabulary)
    compressed = gzip.compress(container, compresslevel=9, mtime=0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(compressed)
    report["compressedBytes"] = len(compressed)
    return report
