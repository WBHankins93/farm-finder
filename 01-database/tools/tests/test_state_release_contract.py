from __future__ import annotations

import sys
import unittest
from copy import deepcopy
import json
from pathlib import Path
import shutil
import tempfile


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from state_release_urls import classify_public_urls, is_valid_website  # noqa: E402
from state_policy import (  # noqa: E402
    ELIGIBLE_STATUS,
    EXCLUDED_STATUS,
    RESEARCH_STATUS,
    classify_candidate,
)
from state_release_status import state_status  # noqa: E402
import migrate_state_contract_v2 as migration  # noqa: E402
import validate_state_releases as validation  # noqa: E402
from validate_state_releases import STATE_ROOT, release_fingerprint, validate_state  # noqa: E402


class StateReleaseUrlTests(unittest.TestCase):
    def test_social_value_moves_out_of_website_field(self) -> None:
        website, facebook, instagram, tiktok = classify_public_urls(
            "https://facebook.com/example", "", "", ""
        )
        self.assertEqual(website, "")
        self.assertEqual(facebook, "https://facebook.com/example")
        self.assertEqual((instagram, tiktok), ("", ""))

    def test_map_and_malformed_values_are_not_websites(self) -> None:
        self.assertFalse(is_valid_website("https://www.google.com/maps/place/example"))
        self.assertFalse(is_valid_website("https://name@gmail.com"))

    def test_google_sites_is_a_valid_owned_site(self) -> None:
        self.assertTrue(is_valid_website("https://sites.google.com/view/example/home"))


class CandidateRetentionPolicyTests(unittest.TestCase):
    def test_name_only_candidate_is_retained_for_research(self) -> None:
        result = classify_candidate(
            "Tiny Farm",
            ["county missing", "products or farm activity missing", "contact missing"],
        )
        self.assertEqual(result.status, RESEARCH_STATUS)
        self.assertEqual(result.exclusion_reason, "")

    def test_missing_data_cannot_be_an_exclusion_reason(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing data must remain"):
            classify_candidate("Tiny Farm", exclusion_reason="missing_contact")

    def test_affirmative_nonfarm_evidence_can_exclude(self) -> None:
        result = classify_candidate("Example Farmers Market", exclusion_reason="confirmed_nonfarm")
        self.assertEqual(result.status, EXCLUDED_STATUS)

    def test_complete_candidate_can_be_eligible(self) -> None:
        self.assertEqual(classify_candidate("Documented Farm").status, ELIGIBLE_STATUS)


class CurrentStateContractTests(unittest.TestCase):
    def test_alabama_contract(self) -> None:
        self.assertEqual(validate_state("AL", False)["status"], "passed")

    def test_texas_contract(self) -> None:
        self.assertEqual(validate_state("TX", False)["status"], "passed")

    def test_coverage_review_is_not_promotion_approval(self) -> None:
        for state in ("AL", "TX"):
            result = state_status(state)
            self.assertEqual(result["lifecycleStatus"], "coverage_reviewed")
            self.assertFalse(result["promotionReady"])
            self.assertFalse(result["promotable"])

    def test_release_fingerprint_changes_with_evidence_identity(self) -> None:
        manifest = json.loads((STATE_ROOT / "AL" / "release-manifest.json").read_text())
        changed = deepcopy(manifest)
        changed["artifacts"][0]["versionId"] = "different-version"
        self.assertNotEqual(release_fingerprint(manifest), release_fingerprint(changed))

    def test_v1_state_migrates_to_exactly_four_valid_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_root = Path(temporary) / "state-expansions"
            shutil.copytree(STATE_ROOT / "AL", state_root / "AL")
            original_migration_root = migration.STATE_ROOT
            original_validation_root = validation.STATE_ROOT
            try:
                migration.STATE_ROOT = state_root
                validation.STATE_ROOT = state_root
                migration.migrate("AL")
                result = validation.validate_state("AL", False)
            finally:
                migration.STATE_ROOT = original_migration_root
                validation.STATE_ROOT = original_validation_root
            self.assertEqual(result["status"], "passed", result["errors"])
            self.assertEqual(
                {path.name for path in (state_root / "AL").iterdir()},
                {"state.yaml", "entities.csv", "decisions.csv", "report.md"},
            )


if __name__ == "__main__":
    unittest.main()
