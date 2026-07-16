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
    effective_decisions,
)
from state_release_status import state_status  # noqa: E402
from collect_alabama import Observation  # noqa: E402
from collect_southeast import (  # noqa: E402
    STATE_CONFIG,
    apply_place_reference,
    empty_observation,
    localharvest_profile,
)
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

    def test_later_retain_decision_supersedes_exclusion(self) -> None:
        rows = [
            {"review_id": "one", "decision": "exclude", "supersedes_review_id": ""},
            {"review_id": "two", "decision": "retain", "supersedes_review_id": "one"},
        ]
        self.assertEqual([row["decision"] for row in effective_decisions(rows)], ["retain"])

    def test_supersession_requires_known_prior_decision(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown decision"):
            effective_decisions([
                {"review_id": "two", "decision": "retain", "supersedes_review_id": "missing"}
            ])


class SoutheastGeographyTests(unittest.TestCase):
    @staticmethod
    def observation(address: str) -> Observation:
        values = empty_observation(
            "AR", "test", address, "Test Farm", "https://example.test", 1, "A"
        )
        values["address"] = address
        return Observation(**values)

    def test_state_confirmed_address_uses_unambiguous_census_place(self) -> None:
        item = self.observation("5985 S.W. Anglin Road Bentonville Arkansas 72713")
        apply_place_reference(
            "AR", {"name": "Arkansas"}, [item],
            {"bentonville": ("Bentonville", "Benton", "05007")},
        )
        self.assertEqual((item.city, item.county, item.county_fips, item.postal_code),
                         ("Bentonville", "Benton", "05007", "72713"))

    def test_out_of_state_address_is_not_inferred(self) -> None:
        item = self.observation("Dallas, TX 75201")
        apply_place_reference(
            "AR", {"name": "Arkansas"}, [item],
            {"dallas": ("Dallas", "Polk", "05113")},
        )
        self.assertEqual((item.city, item.county, item.postal_code), ("", "", ""))

    def test_out_of_state_radius_result_is_preserved_as_exclusion_evidence(self) -> None:
        body = (
            '<strong>Location:</strong><br />1045 S. Genois St.<br /> '
            'New Orleans, LA 70125 <div id="descDiv">Vegetable farm</div>'
        )
        card = {
            "url": "https://www.localharvest.org/example-M1", "name": "Example Farm",
            "city": "", "summary": "", "searched_county": "Pulaski",
            "search_url": "https://example.test",
        }
        item = localharvest_profile("AR", STATE_CONFIG["AR"], card, body)
        self.assertEqual(item.promotion_status, "excluded_outside_jurisdiction")
        self.assertIn("outside AR", item.notes)


class CurrentStateContractTests(unittest.TestCase):
    def test_alabama_contract(self) -> None:
        self.assertEqual(validate_state("AL", False)["status"], "passed")

    def test_texas_contract(self) -> None:
        self.assertEqual(validate_state("TX", False)["status"], "passed")

    def test_arkansas_contract(self) -> None:
        self.assertEqual(validate_state("AR", False)["status"], "passed")

    def test_coverage_review_is_not_promotion_approval(self) -> None:
        for state in ("AL", "AR", "TX"):
            result = state_status(state)
            self.assertEqual(result["lifecycleStatus"], "coverage_reviewed")
            self.assertFalse(result["promotionReady"])
            self.assertFalse(result["promotable"])

    def test_release_fingerprint_changes_with_evidence_identity(self) -> None:
        state_dir = STATE_ROOT / "AL"
        path = state_dir / "state.yaml" if (state_dir / "state.yaml").is_file() else state_dir / "release-manifest.json"
        document = json.loads(path.read_text())
        changed = deepcopy(document)
        artifacts = changed["release"]["artifacts"] if "release" in changed else changed["artifacts"]
        artifacts[0]["versionId"] = "different-version"
        self.assertNotEqual(release_fingerprint(document), release_fingerprint(changed))

    def test_v1_state_migrates_to_exactly_four_valid_files(self) -> None:
        legacy_states = sorted(
            path for path in STATE_ROOT.iterdir()
            if path.is_dir() and not (path / "state.yaml").is_file()
        )
        if not legacy_states:
            self.skipTest("all committed states already use contract v2")
        source_state = legacy_states[0]
        with tempfile.TemporaryDirectory() as temporary:
            state_root = Path(temporary) / "state-expansions"
            shutil.copytree(source_state, state_root / source_state.name)
            original_migration_root = migration.STATE_ROOT
            original_validation_root = validation.STATE_ROOT
            try:
                migration.STATE_ROOT = state_root
                validation.STATE_ROOT = state_root
                migration.migrate(source_state.name)
                result = validation.validate_state(source_state.name, False)
            finally:
                migration.STATE_ROOT = original_migration_root
                validation.STATE_ROOT = original_validation_root
            self.assertEqual(result["status"], "passed", result["errors"])
            self.assertEqual(
                {path.name for path in (state_root / source_state.name).iterdir()},
                {"state.yaml", "entities.csv", "decisions.csv", "report.md"},
            )


if __name__ == "__main__":
    unittest.main()
