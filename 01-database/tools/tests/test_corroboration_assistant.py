from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import corroboration_assistant as assistant  # noqa: E402


class CorroborationAssistantTests(unittest.TestCase):
    def entity(self, **overrides: str) -> dict[str, str]:
        row = {
            "entity_id": "AR-1",
            "farm_name": "Tiny Farm",
            "normalized_name": "tiny farm",
            "entity_type": "farm",
            "state": "AR",
            "county_equivalent": "Pulaski",
            "city": "Little Rock",
            "postal_code": "72201",
            "products": "Vegetables",
            "business_types": "Farm",
            "phone_internal": "501-555-0100",
            "email_internal": "farmer@example.com",
            "website_url": "https://tinyfarm.example",
            "source_observation_count": "1",
            "source_observation_ids": "arobs_1",
            "source_names": "PickYourOwn",
            "source_urls": "https://directory.example/tiny",
            "evidence_grades": "E",
            "last_retrieved": "2026-07-15",
            "promotion_status": "research_or_qa_queue",
            "promotion_blockers": assistant.QA_BLOCKER,
        }
        row.update(overrides)
        return row

    @staticmethod
    def active_fetch(_: str) -> dict[str, object]:
        return {
            "requestedUrl": "https://tinyfarm.example",
            "finalUrl": "https://tinyfarm.example/season",
            "httpStatus": 200,
            "retrievedAt": "2026-07-16T12:00:00+00:00",
            "responseSha256": "a" * 64,
            "contentType": "text/html",
            "reachable": True,
            "currentYearActiveSignal": "2026",
            "activeEvidenceExcerpt": "Our 2026 season is open; farm stand hours are posted.",
            "explicitClosureSignal": "",
            "error": "",
        }

    def test_website_liveness_requires_three_fetches_and_pairs_decision_patch(self) -> None:
        calls: list[str] = []

        def fake(url: str) -> dict[str, object]:
            calls.append(url)
            return self.active_fetch(url)

        result = assistant.run_assistant(
            "AR",
            [self.entity()],
            {"collection": {"sources": []}},
            fetcher=fake,
        )
        self.assertEqual(calls, ["https://tinyfarm.example"] * 3)
        self.assertEqual(result["hit_rate"]["website_liveness_hits"], 1)
        self.assertEqual(result["hit_rate"]["combined_unique_hit_rate"], 1.0)
        observation = result["proposed_observations"][0]
        decision = result["draft_decisions"][0]
        patch = result["entity_patches"][0]
        self.assertEqual(observation["dated_active_excerpt"], "Our 2026 season is open; farm stand hours are posted.")
        self.assertEqual(observation["response_sha256"], ["a" * 64] * 3)
        self.assertEqual(decision["observation_id"], observation["observation_id"])
        self.assertEqual(patch["proposed_evidence_grades"], ["C", "E"])
        self.assertEqual(patch["proposed_promotion_status"], "research_or_qa_queue")

    def test_directory_and_profile_urls_are_not_fetched(self) -> None:
        row = self.entity(website_url="https://www.yelp.com/biz/tiny-farm")
        calls: list[str] = []
        result = assistant.run_assistant(
            "AR", [row], {"collection": {"sources": []}}, fetcher=lambda url: calls.append(url) or self.active_fetch(url)
        )
        self.assertEqual(calls, [])
        self.assertFalse(result["website_liveness"][0]["eligible_for_fetch"])
        self.assertIsNone(result["website_liveness"][0]["proposal"])

    def test_malformed_encoded_host_is_not_fetched(self) -> None:
        row = self.entity(website_url="http://Welcome%20to%20The%20Produce%20Porch!%20Fresh.example")
        calls: list[str] = []
        result = assistant.run_assistant(
            "AR", [row], {"collection": {"sources": []}}, fetcher=lambda url: calls.append(url) or self.active_fetch(url)
        )
        self.assertEqual(calls, [])
        self.assertFalse(result["website_liveness"][0]["eligible_for_fetch"])
        self.assertEqual(result["website_liveness"][0]["skip_reason"], "invalid or shared website URL")

    def test_entity_patch_accepts_semicolon_delimited_grades(self) -> None:
        observation = {
            "observation_id": "coroobs_test",
            "source_name": "Test source",
            "source_url": "https://tinyfarm.example",
            "evidence_grade": "C",
        }
        patch = assistant.entity_patch(self.entity(evidence_grades="B; E"), observation)
        self.assertEqual(patch["base_evidence_grades"], ["B", "E"])

    def test_cross_directory_hit_needs_contact_and_consistent_geography(self) -> None:
        target = self.entity(website_url="", phone_internal="501-555-0100")
        peer = self.entity(
            entity_id="AR-2",
            farm_name="Tiny Farmstead",
            normalized_name="tiny farmstead",
            city="Little Rock",
            county_equivalent="Pulaski",
            source_observation_count="1",
            source_observation_ids="arobs_2",
            source_names="Arkansas Grown",
            source_urls="https://arkansasgrown.example/tiny",
            evidence_grades="B",
            website_url="",
        )
        result = assistant.run_assistant("AR", [target, peer], {"collection": {"sources": []}})
        self.assertEqual(result["hit_rate"]["cross_directory_hits"], 1)
        self.assertEqual(result["proposed_observations"][0]["method"], "cross_directory_match")
        self.assertEqual(result["draft_decisions"][0]["peer_entity_id"], "AR-2")

    def test_cross_directory_geography_conflict_routes_to_qa_without_decision(self) -> None:
        target = self.entity(website_url="", phone_internal="501-555-0100")
        peer = self.entity(
            entity_id="AR-2",
            farm_name="Tiny Farmstead",
            normalized_name="tiny farmstead",
            city="Bentonville",
            county_equivalent="Benton",
            source_observation_count="1",
            source_observation_ids="arobs_2",
            source_names="Arkansas Grown",
            source_urls="https://arkansasgrown.example/tiny",
            website_url="",
        )
        result = assistant.run_assistant("AR", [target, peer], {"collection": {"sources": []}})
        self.assertEqual(result["hit_rate"]["cross_directory_hits"], 0)
        self.assertEqual(len(result["qa_review_items"]), 1)
        self.assertEqual(result["qa_review_items"][0]["conflict_fields"][0]["field"], "county_equivalent")
        self.assertEqual(result["draft_decisions"], [])

    def test_arkansas_selector_has_sixty_one_rows_after_first_apply_batch(self) -> None:
        path = Path(__file__).resolve().parents[3] / "research/state-expansions/AR/entities.csv"
        rows = assistant.read_csv(path)
        selected = assistant.target_rows(rows, [assistant.QA_BLOCKER])
        self.assertEqual(len(selected), 61)
        self.assertTrue(all(row["promotion_status"] == assistant.QA_STATUS for row in selected))


if __name__ == "__main__":
    unittest.main()
