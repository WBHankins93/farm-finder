from __future__ import annotations

import sys
import unittest
from copy import deepcopy
import json
from pathlib import Path


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from state_release_urls import classify_public_urls, is_valid_website  # noqa: E402
from state_release_status import state_status  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
