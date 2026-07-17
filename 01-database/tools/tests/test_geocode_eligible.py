from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import geocode_eligible  # noqa: E402


def feature(**attributes: object) -> dict[str, object]:
    return {"attributes": attributes}


class GeocodeEligibleTests(unittest.TestCase):
    def test_request_json_retries_three_times_with_declared_timeout(self) -> None:
        calls: list[tuple[str, int, str | None]] = []

        def fetcher(request: object, timeout: int) -> bytes:
            calls.append((
                getattr(request, "full_url"),
                timeout,
                getattr(request, "get_header")("User-agent"),
            ))
            if len(calls) < 3:
                raise URLError("temporary failure")
            return b'{"ok": true}'

        with patch.object(geocode_eligible.time, "sleep") as sleep:
            body, log = geocode_eligible.request_json(
                "https://example.test/geocode", fetcher=fetcher
            )

        self.assertEqual(body, {"ok": True})
        self.assertEqual(log["attempts_used"], 3)
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(timeout == 45 for _, timeout, _ in calls))
        self.assertTrue(all(user_agent == geocode_eligible.USER_AGENT for _, _, user_agent in calls))
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(calls[0][0], "https://example.test/geocode")

    def test_precision_ladder_preserves_source_fields_and_protects_internal_rows(self) -> None:
        def fetcher(request: object, timeout: int) -> bytes:
            url = getattr(request, "full_url")
            if "State_County" in url:
                return json.dumps({
                    "features": [feature(
                        BASENAME="Pulaski", NAME="Pulaski County", STATE="05",
                        INTPTLAT="34.75", INTPTLON="-92.3",
                    )]
                }).encode()
            if "MapServer/4/query" in url:
                return json.dumps({
                    "features": [feature(
                        BASENAME="Little Rock", NAME="Little Rock city", STATE="05",
                        INTPTLAT="34.7465", INTPTLON="-92.2896",
                    )]
                }).encode()
            return b'{"features": []}'

        rows = [
            {
                "entity_id": "AR-1", "latitude": "35", "longitude": "-92",
                "public_location_classification": "public_business_address_reviewed_for_future_reduced_precision",
                "address_internal": "123 Main Street", "city": "", "county_equivalent": "Pulaski",
                "promotion_status": "promotion_eligible_reviewed", "evidence_grades": "B",
            },
            {
                "entity_id": "AR-2", "latitude": "", "longitude": "",
                "public_location_classification": "public_business_address_reviewed_for_future_reduced_precision",
                "address_internal": "", "city": "Little Rock", "county_equivalent": "Pulaski",
                "promotion_status": "promotion_eligible_reviewed", "evidence_grades": "B",
            },
            {
                "entity_id": "AR-3", "latitude": "35.1", "longitude": "-92.1",
                "public_location_classification": "internal_only",
                "address_internal": "123 Private Road", "city": "", "county_equivalent": "Pulaski",
                "promotion_status": "promotion_eligible_reviewed", "evidence_grades": "C",
            },
        ]
        cache: dict[str, object] = {}
        output, summary = geocode_eligible.geocode_rows("AR", rows, cache, fetcher=fetcher)

        self.assertEqual(output[0]["geocoded_latitude"], "35.0000000")
        self.assertEqual(output[0]["geocode_precision"], "public_business_address")
        self.assertEqual(output[1]["geocoded_latitude"], "34.7465000")
        self.assertEqual(output[1]["geocode_precision"], "city_centroid")
        self.assertEqual(output[2]["geocoded_latitude"], "34.7500000")
        self.assertEqual(output[2]["geocode_precision"], "county_centroid")
        self.assertEqual(output[2]["geocode_source"], "U.S. Census Bureau — TIGERweb county internal point")
        for index, source in enumerate(rows):
            self.assertEqual(output[index]["promotion_status"], source["promotion_status"])
            self.assertEqual(output[index]["evidence_grades"], source["evidence_grades"])
        self.assertEqual(summary["input_rows"], 3)
        self.assertTrue(summary["target_met"])

    def test_cached_response_is_reused_for_empty_and_nonempty_results(self) -> None:
        cache: dict[str, object] = {}
        calls = 0

        def fetcher(request: object, timeout: int) -> bytes:
            nonlocal calls
            calls += 1
            return b'{"features": []}'

        url = "https://example.test/geocode?city=Nowhere"
        first = geocode_eligible.cached_json(url, cache, fetcher=fetcher)
        second = geocode_eligible.cached_json(url, cache, fetcher=fetcher)

        self.assertEqual(calls, 1)
        self.assertFalse(first[2])
        self.assertTrue(second[2])
        self.assertEqual(first[0], second[0])


if __name__ == "__main__":
    unittest.main()
