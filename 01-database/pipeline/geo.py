"""Geo stage — put ungeocoded records on the map using only in-repo data.

Only ~2,700 of ~15,700 staged rows carry coordinates. Rather than block the
whole dataset on an external geocoding backfill, we synthesize a county centroid
from the rows that *are* geocoded and place their ungeocoded county-siblings
there at `county-approx` precision. It needs no network and no external dataset —
the signal is already in the data we collected.

Rows in a county with zero geocoded siblings stay `ungeocoded`; the map skips
them and they wait for the (Codex-owned) per-region geocode backfill. This stage
is safe to re-run: it only ever fills, never overwrites a real coordinate.
"""
from __future__ import annotations

from collections import defaultdict

from model import Farm


def build_county_centroids(farms: list[Farm]) -> dict[tuple[str, str], tuple[float, float]]:
    """Mean lat/lng per (state, county) over rows that have real coordinates."""
    acc: dict[tuple[str, str], list[tuple[float, float]]] = defaultdict(list)
    for f in farms:
        if f.geo.latitude is not None and f.geo.longitude is not None and f.geo.precision != "county-approx":
            acc[(f.state, f.county.lower())].append((f.geo.latitude, f.geo.longitude))
    centroids: dict[tuple[str, str], tuple[float, float]] = {}
    for key, pts in acc.items():
        if not key[1]:
            continue
        centroids[key] = (
            round(sum(p[0] for p in pts) / len(pts), 5),
            round(sum(p[1] for p in pts) / len(pts), 5),
        )
    return centroids


def apply_geo_fallback(farms: list[Farm]) -> dict[str, int]:
    """Fill ungeocoded rows with their county centroid where one exists.
    Returns coverage counts before/after."""
    centroids = build_county_centroids(farms)
    had = sum(1 for f in farms if f.geo.mappable)
    filled = 0
    for f in farms:
        if f.geo.latitude is not None:
            continue
        c = centroids.get((f.state, f.county.lower()))
        if c:
            f.geo.latitude, f.geo.longitude = c
            f.geo.precision = "county-approx"
            filled += 1
    return {
        "counties_with_centroid": len(centroids),
        "mappable_before": had,
        "filled_county_approx": filled,
        "mappable_after": had + filled,
        "still_ungeocoded": sum(1 for f in farms if not f.geo.mappable),
    }
