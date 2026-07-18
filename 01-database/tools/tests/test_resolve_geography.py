from __future__ import annotations

import sys
import unittest
import json
from pathlib import Path


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from resolve_geography import (  # noqa: E402
    CENSUS_GEOCODER_URL,
    FCC_AREA_URL,
    address_cache_key,
    place_reference,
    remaining_blockers,
    resolve_state,
)


PLACE_FILE = (
    "STATE|STATEFP|PLACEFP|PLACENAME|TYPE|FUNCSTAT|COUNTYFP|COUNTYNAME\n"
    "NC|37|10120|Black Mountain town|INCORPORATED PLACE|A|021|Buncombe County\n"
    "NC|37|22960|Faison town|INCORPORATED PLACE|A|061|Duplin County\n"
    "NC|37|12345|Splitville town|INCORPORATED PLACE|A|001|Alamance County\n"
    "NC|37|12345|Splitville town|INCORPORATED PLACE|A|003|Alexander County\n"
    "NC|37|01000|Apex town|INCORPORATED PLACE|A|183|Wake County\n"
    "NC|37|02000|Cary town|INCORPORATED PLACE|A|183|Wake County\n"
    "SC|45|99999|Elsewhere town|INCORPORATED PLACE|A|001|Abbeville County\n"
)


def qa_row(**overrides: str) -> dict[str, str]:
    row = {
        "entity_id": "NC-TEST0001",
        "farm_name": "Test Farm",
        "normalized_name": "test farm",
        "entity_type": "farm_or_agricultural_business",
        "identity_decision": "unique_source_name_reviewed",
        "state": "NC",
        "county_equivalent": "",
        "city": "Black Mountain",
        "address_internal": "",
        "postal_code": "",
        "products": "Vegetables",
        "public_location_classification": "public_business_address_reviewed_for_future_reduced_precision",
        "contact_visibility": "internal_until_public_use_review",
        "source_urls": "https://example.test",
        "last_retrieved": "2026-07-16",
        "evidence_grades": "B",
        "promotion_status": "research_or_qa_queue",
        "promotion_blockers": "county requires geography review",
    }
    row.update(overrides)
    return row


class PlaceReferenceTests(unittest.TestCase):
    def test_multi_county_places_are_withheld(self) -> None:
        reference = place_reference("NC", PLACE_FILE)
        self.assertIn("black mountain", reference)
        self.assertEqual(reference["black mountain"][1], "Buncombe")
        self.assertNotIn("splitville", reference)
        self.assertNotIn("elsewhere", reference)


class ResolveStateTests(unittest.TestCase):
    reference = place_reference("NC", PLACE_FILE)

    def test_unambiguous_city_drafts_correct_decision_and_clears_blocker(self) -> None:
        bundle = resolve_state("NC", [qa_row()], self.reference)
        self.assertEqual(bundle["resolved"], 1)
        proposal = bundle["proposals"][0]
        self.assertEqual(proposal["entity_patch"]["proposed_county_equivalent"], "Buncombe")
        self.assertEqual(proposal["entity_patch"]["proposed_promotion_blockers"], "")
        self.assertEqual(proposal["entity_patch"]["proposed_promotion_status"],
                         "promotion_eligible_reviewed")
        self.assertEqual(proposal["decision"]["decision"], "correct")
        self.assertIn("census.gov", proposal["decision"]["source_url"])

    def test_residual_blockers_keep_the_row_in_qa(self) -> None:
        row = qa_row(promotion_blockers="county requires geography review; single grade-E discovery listing needs corroboration")
        bundle = resolve_state("NC", [row], self.reference)
        patch = bundle["proposals"][0]["entity_patch"]
        self.assertEqual(patch["proposed_promotion_blockers"], "single grade-E discovery listing needs corroboration")
        self.assertEqual(patch["proposed_promotion_status"], "research_or_qa_queue")

    def test_grade_e_only_rows_stay_in_qa_even_when_geography_clears(self) -> None:
        bundle = resolve_state("NC", [qa_row(evidence_grades="E")], self.reference)
        self.assertEqual(bundle["proposals"][0]["entity_patch"]["proposed_promotion_status"],
                         "research_or_qa_queue")

    def test_conflicting_county_is_flagged_not_overridden(self) -> None:
        bundle = resolve_state("NC", [qa_row(county_equivalent="Wake")], self.reference)
        self.assertEqual(bundle["resolved"], 0)
        self.assertEqual(bundle["conflicts"], 1)
        self.assertEqual(bundle["conflict_items"][0]["census_county"], "Buncombe")

    def test_missing_city_and_ambiguous_place_are_reported_unresolved(self) -> None:
        rows = [qa_row(city=""), qa_row(entity_id="NC-TEST0002", city="Splitville")]
        bundle = resolve_state("NC", rows, self.reference)
        self.assertEqual(bundle["unresolved"], 2)
        reasons = " ".join(item["reason"] for item in bundle["unresolved_items"])
        self.assertIn("city missing", reasons)
        self.assertIn("unambiguous", reasons)

    def test_same_name_entity_in_resolved_county_is_an_identity_conflict(self) -> None:
        peer = qa_row(
            entity_id="NC-PEER00001",
            county_equivalent="Buncombe",
            promotion_status="promotion_eligible_reviewed",
            promotion_blockers="",
        )
        bundle = resolve_state("NC", [peer, qa_row()], self.reference)
        self.assertEqual(bundle["resolved"], 0)
        self.assertEqual(bundle["conflicts"], 1)
        self.assertEqual(bundle["conflict_items"][0]["colliding_entity_id"], "NC-PEER00001")
        self.assertEqual(bundle["conflict_items"][0]["recommended_action"],
                         "route_to_human_identity_qa")

    def test_remaining_blockers_only_strips_geography_clauses(self) -> None:
        self.assertEqual(
            remaining_blockers("county missing; single grade-E discovery listing needs corroboration"),
            "single grade-E discovery listing needs corroboration",
        )

    def test_internal_street_address_resolves_county_only_and_reuses_hashed_cache(self) -> None:
        row = qa_row(city="", address_internal="1595 Strickland Road, Clayton, NC 27520")
        calls: list[str] = []

        def fetcher(url: str) -> tuple[str, dict[str, object]]:
            calls.append(url)
            self.assertIn(CENSUS_GEOCODER_URL, url)
            return json.dumps({"result": {"addressMatches": [{
                "geographies": {"Counties": [{"STATE": "37", "COUNTY": "101", "NAME": "Johnston County"}]}
            }]}}), {}

        cache: dict[str, object] = {}
        bundle = resolve_state("NC", [row], self.reference, fetcher=fetcher, cache=cache)
        self.assertEqual(bundle["resolved"], 1)
        patch = bundle["proposals"][0]["entity_patch"]
        self.assertEqual(patch["proposed_county_equivalent"], "Johnston")
        self.assertEqual(patch["proposed_geography_precision"], "county_centroid")
        self.assertEqual(patch["proposed_city"], "")
        self.assertEqual(len(calls), 1)
        self.assertIn(address_cache_key("NC", row["address_internal"]), cache)
        cached = resolve_state(
            "NC", [row], self.reference,
            fetcher=lambda url: (_ for _ in ()).throw(AssertionError("unexpected cache miss")),
            cache=cache,
        )
        self.assertEqual(cached["resolved"], 1)

    def test_internal_address_uses_fcc_fallback_without_public_coordinates(self) -> None:
        row = qa_row(city="", address_internal="100 Main Street, Apex, NC 27502")

        def fetcher(url: str) -> tuple[str, dict[str, object]]:
            if CENSUS_GEOCODER_URL in url:
                return json.dumps({"result": {"addressMatches": [{
                    "coordinates": {"x": -78.8, "y": 35.7}, "geographies": {},
                }]}}), {}
            self.assertIn(FCC_AREA_URL, url)
            return json.dumps({"results": [{
                "state_fips": "37", "county_fips": "183", "county_name": "Wake",
            }]}), {}

        bundle = resolve_state("NC", [row], self.reference, fetcher=fetcher, cache={})
        proposal = bundle["proposals"][0]
        self.assertEqual(proposal["decision"]["source_url"], FCC_AREA_URL)
        self.assertNotIn("35.7", json.dumps(proposal))
        self.assertNotIn("-78.8", json.dumps(proposal))

    def test_ambiguous_address_matches_route_to_conflict(self) -> None:
        row = qa_row(city="", address_internal="100 Main Street, NC 27502")
        bundle = resolve_state(
            "NC", [row], self.reference,
            fetcher=lambda url: (json.dumps({"result": {"addressMatches": [{}, {}]}}), {}),
            cache={},
        )
        self.assertEqual(bundle["resolved"], 0)
        self.assertEqual(bundle["conflicts"], 1)
        self.assertEqual(bundle["conflict_items"][0]["recommended_action"], "route_to_human_qa")

    def test_market_circuit_sets_service_area_and_market_precision(self) -> None:
        row = qa_row(
            entity_id="NC-MARKET0001",
            farm_name="Apex Farmers Market",
            normalized_name="apex farmers market",
            city="",
            source_names="Certified Farm Markets roster",
            source_urls="https://markets.example/apex",
            promotion_blockers="county requires geography review; city or safe public service area requires review",
        )
        bundle = resolve_state("NC", [row], self.reference, cache={})
        self.assertEqual(bundle["resolved"], 1)
        patch = bundle["proposals"][0]["entity_patch"]
        self.assertEqual(patch["proposed_county_equivalent"], "Wake")
        self.assertEqual(patch["proposed_city"], "Apex")
        self.assertEqual(patch["proposed_public_location_classification"], "market_circuit_service_area")
        self.assertEqual(patch["proposed_geography_precision"], "market_location_county")
        self.assertEqual(patch["proposed_promotion_blockers"], "")

    def test_ambiguous_market_locations_route_to_conflict(self) -> None:
        row = qa_row(
            entity_id="NC-MARKET0002",
            farm_name="Black Mountain and Faison Farmers Market",
            normalized_name="black mountain and faison farmers market",
            city="",
            source_names="Certified Farm Markets roster",
            source_urls="https://markets.example/ambiguous",
            promotion_blockers="county requires geography review; city or safe public service area requires review",
        )
        bundle = resolve_state("NC", [row], self.reference, cache={})
        self.assertEqual(bundle["resolved"], 0)
        self.assertEqual(bundle["conflicts"], 1)
        self.assertEqual(bundle["conflict_items"][0]["recommended_action"], "route_to_human_qa")


if __name__ == "__main__":
    unittest.main()
