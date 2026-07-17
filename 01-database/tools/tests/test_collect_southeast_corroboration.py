from __future__ import annotations

import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from collect_alabama import Observation  # noqa: E402
from collect_southeast import (  # noqa: E402
    cross_directory_corroboration,
    empty_observation,
    reconcile,
)
from qa_triage import route  # noqa: E402


class CollectionCorroborationTests(unittest.TestCase):
    def observation(
        self,
        source_name: str,
        farm_name: str = "Tiny Farm",
        *,
        grade: str = "E",
        source_pass: int = 1,
        county: str = "Pulaski",
        city: str = "Little Rock",
        postal_code: str = "72201",
        phone: str = "501-555-0100",
        email: str = "",
    ) -> Observation:
        row = empty_observation(
            "AR",
            source_name,
            f"{source_name}-1",
            farm_name,
            f"https://{source_name.casefold().replace(' ', '-')}.example/{farm_name.casefold().replace(' ', '-')}",
            source_pass,
            grade,
        )
        row.update({
            "entity_type_review": "farm_activity_confirmed_by_directory",
            "county": county,
            "county_source": "https://www2.census.gov/geo/docs/reference/codes2020/national_place_by_county2020.txt",
            "city": city,
            "postal_code": postal_code,
            "phone": phone,
            "email": email,
            "products": "Vegetables",
            "on_farm_sales": True,
        })
        return Observation(**row)

    def test_independent_confirmation_merges_and_becomes_eligible(self) -> None:
        primary = self.observation("Arkansas Grown")
        confirmer = self.observation(
            "LocalHarvest",
            farm_name="Tiny Farmstead",
            grade="C",
            source_pass=2,
        )
        result = cross_directory_corroboration([primary, confirmer])

        self.assertEqual(len(result["merged_pairs"]), 1)
        self.assertEqual(primary.candidate_key, confirmer.candidate_key)
        entities, _, qa = reconcile("AR", [primary, confirmer], result["blockers_by_candidate_key"])

        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0]["evidence_grades"], "C; E")
        self.assertEqual(entities[0]["source_observation_count"], 2)
        self.assertEqual(entities[0]["promotion_status"], "promotion_eligible_reviewed")
        self.assertEqual(qa, [])

    def test_geography_conflict_stays_separate_and_routes_to_geography_qa(self) -> None:
        primary = self.observation("Arkansas Grown")
        conflicting = self.observation(
            "LocalHarvest",
            farm_name="Tiny Farmstead",
            source_pass=2,
            county="Benton",
            city="Bentonville",
            postal_code="72712",
        )
        result = cross_directory_corroboration([primary, conflicting])

        self.assertEqual(result["merged_pairs"], [])
        self.assertEqual(len(result["conflict_items"]), 1)
        self.assertNotEqual(primary.candidate_key, conflicting.candidate_key)
        entities, _, qa = reconcile("AR", [primary, conflicting], result["blockers_by_candidate_key"])

        self.assertEqual(len(entities), 2)
        self.assertEqual(len(qa), 2)
        self.assertTrue(all("cross-directory geography conflict" in row["promotion_blockers"] for row in entities))
        self.assertIn("geography", route(entities[0]["promotion_blockers"])[1])

    def test_contact_conflict_stays_separate_and_routes_to_identity_qa(self) -> None:
        primary = self.observation("Arkansas Grown")
        conflicting = self.observation(
            "LocalHarvest",
            farm_name="Tiny Farmstead",
            source_pass=2,
            phone="501-555-0199",
        )
        result = cross_directory_corroboration([primary, conflicting])

        self.assertEqual(result["merged_pairs"], [])
        self.assertEqual(result["conflict_items"][0]["conflict_types"], ["contact"])
        self.assertNotEqual(primary.candidate_key, conflicting.candidate_key)
        entities, _, qa = reconcile("AR", [primary, conflicting], result["blockers_by_candidate_key"])

        self.assertEqual(len(entities), 2)
        self.assertEqual(len(qa), 2)
        self.assertTrue(all("cross-directory contact conflict" in row["promotion_blockers"] for row in entities))
        self.assertIn("identity", route(entities[0]["promotion_blockers"])[1])

    def test_same_source_duplicate_is_not_independent_confirmation(self) -> None:
        first = self.observation("Arkansas Grown")
        duplicate = self.observation(
            "Arkansas Grown",
            farm_name="Tiny Farmstead",
            source_pass=2,
        )
        result = cross_directory_corroboration([first, duplicate])

        self.assertEqual(result["merged_pairs"], [])
        self.assertEqual(result["conflict_items"], [])
        self.assertNotEqual(first.candidate_key, duplicate.candidate_key)


if __name__ == "__main__":
    unittest.main()
