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
    source_tier_issues,
    sufficient_promotion_evidence,
)
from state_release_status import state_status  # noqa: E402
from export_state_pipeline import export_state  # noqa: E402
from collect_alabama import Observation  # noqa: E402
from collect_southeast import (  # noqa: E402
    STATE_CONFIG,
    apply_place_reference,
    apply_source_tier_policy,
    choose_county,
    empty_observation,
    farm_operation_signal,
    farm_entity_confirmation,
    florida_farm_to_you_profile,
    florida_producer_cards,
    georgia_grown_cards,
    georgia_grown_profile,
    localharvest_profile,
    next_page_data,
    normalized_county,
    nursery_column_records,
    reconcile,
    sanitized_email,
    sanitized_phone,
)
from assess_pr_scope import (  # noqa: E402
    QA_INTAKE_CAP,
    committed_qa_total,
    new_state_directories,
    stale_state_directories,
)
from qa_triage import route as qa_route  # noqa: E402
from qa_triage import triage_state  # noqa: E402
from audit_operation_evidence import dated_active_excerpt  # noqa: E402
import migrate_state_contract_v2 as migration  # noqa: E402
import validate_state_releases as validation  # noqa: E402
from validate_state_releases import STATE_ROOT, release_fingerprint, validate_state  # noqa: E402
from referrals import (  # noqa: E402
    REFERRAL_FIELDS,
    infer_home_state,
    read_referrals,
    referral_from_decision,
    referral_from_observation,
    referrals_from_committed_decisions,
    stage_referrals,
    validate_referral_inputs,
)


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

    def test_social_homepage_is_not_a_farm_profile(self) -> None:
        _, facebook, instagram, _ = classify_public_urls(
            "", "https://www.facebook.com/", "https://www.instagram.com/", ""
        )
        self.assertEqual((facebook, instagram), ("", ""))


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

    def test_supersession_cycles_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "supersession cycle"):
            effective_decisions([
                {"review_id": "one", "decision": "retain", "supersedes_review_id": "two"},
                {"review_id": "two", "decision": "retain", "supersedes_review_id": "one"},
            ])

    def test_grade_e_only_observations_are_insufficient_for_eligibility(self) -> None:
        self.assertFalse(sufficient_promotion_evidence("E"))
        self.assertFalse(sufficient_promotion_evidence("E", ["E"]))
        self.assertTrue(sufficient_promotion_evidence("B"))
        self.assertTrue(sufficient_promotion_evidence("B; E"))

    def test_corroborating_decision_evidence_can_resolve_grade_e_only(self) -> None:
        self.assertTrue(sufficient_promotion_evidence("E", ["C"]))
        self.assertFalse(sufficient_promotion_evidence("E", ["F"]))

    def test_grade_f_observations_block_eligibility_even_when_corroborated(self) -> None:
        self.assertFalse(sufficient_promotion_evidence("B; F"))
        self.assertFalse(sufficient_promotion_evidence("F", ["A"]))


class ReferralInputTests(unittest.TestCase):
    def test_home_state_inference_discards_collecting_state(self) -> None:
        self.assertEqual(
            infer_home_state(
                "The operation is in a New Mexico community and serves Texas buyers.",
                collecting_state="TX",
            ),
            "NM",
        )

    def test_decision_becomes_home_state_referral_with_market_presence(self) -> None:
        row = referral_from_decision({
            "review_id": "tx-1",
            "farm_name": "Example Farm",
            "exclusion_reason": "outside_jurisdiction",
            "decision_basis": "The farm-owned site places the operation in Louisiana, outside Texas.",
            "notes": "The Texas directory was the collecting source.",
            "source_url": "https://example.test/evidence",
            "retrieved_date": "2026-07-15",
            "business_types": "Farmers market; direct sales",
            "products": "Vegetables",
            "evidence_grade": "C",
            "verified_entity_type": "farm",
        }, "TX")
        self.assertEqual(row["home_state"], "LA")
        self.assertEqual(row["observed_market_state"], "TX")
        self.assertIn("Farmers market", row["observed_market_channel"])
        self.assertEqual(row["source_decision_id"], "tx-1")

    def test_retroactive_generation_covers_all_current_outside_decisions(self) -> None:
        referrals = referrals_from_committed_decisions()
        self.assertEqual(len(referrals), 20)
        self.assertIn("Ganus Farms", {row["farm_name"] for row in referrals})
        self.assertEqual(
            {row["home_state"] for row in referrals if row["farm_name"] == "Ganus Farms"},
            {"MS"},
        )

    def test_staging_is_idempotent_and_is_not_a_state_contract_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            row = referral_from_decision({
                "review_id": "al-1",
                "farm_name": "Ganus Farms",
                "exclusion_reason": "outside_jurisdiction",
                "decision_basis": "The farm is in Mississippi, outside Alabama.",
                "source_url": "https://example.test/ganus",
                "retrieved_date": "2026-07-15",
            }, "AL")
            stage_referrals([row], root=root)
            stage_referrals([row], root=root)
            path = root / "research" / "collection-inputs" / "MS" / "referrals.csv"
            self.assertEqual(path.read_text(encoding="utf-8").count("Ganus Farms"), 1)
            self.assertEqual(read_referrals("MS", root=root)[0]["collecting_state"], "AL")
            self.assertEqual(validate_referral_inputs(root=root)["status"], "passed")
            self.assertNotIn("referrals.csv", {item.name for item in (root / "research" / "state-expansions" / "MS").glob("*")} if (root / "research" / "state-expansions" / "MS").exists() else set())

    def test_referral_input_header_is_explicit(self) -> None:
        self.assertEqual(REFERRAL_FIELDS[0], "referral_id")
        self.assertIn("observed_market_channel", REFERRAL_FIELDS)

    def test_collector_observation_becomes_referral(self) -> None:
        row = referral_from_observation({
            "observation_id": "arobs-1",
            "farm_name": "Example Farm",
            "source_name": "LocalHarvest — Arkansas",
            "source_url": "https://example.test/profile",
            "retrieved_date": "2026-07-16",
            "business_types": "Farmers market vendor",
            "products": "Vegetables",
            "evidence_grade": "E",
            "notes": "Source location is Louisiana, outside AR; retained as exclusion evidence.",
        }, "AR")
        self.assertEqual((row["home_state"], row["collecting_state"]), ("LA", "AR"))
        self.assertEqual(row["source_record_id"], "arobs-1")
        self.assertIn("Farmers market", row["observed_market_channel"])

    def test_malformed_csv_shape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "malformed.csv"
            path.write_text("entity_id,state\nNC-1,NC,extra\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "more values than the header"):
                validation.read_csv(path)


class SourceTierPolicyTests(unittest.TestCase):
    def test_valid_tiers_pass_and_invalid_tiers_error(self) -> None:
        invalid, untiered = source_tier_issues([
            {"sourceId": "a", "tier": "candidate"},
            {"sourceId": "b", "tier": "identity_hint"},
            {"sourceId": "c", "tier": "primary"},
        ])
        self.assertEqual(invalid, ["c"])
        self.assertEqual(untiered, [])

    def test_legacy_untiered_sources_warn_not_error(self) -> None:
        invalid, untiered = source_tier_issues([{"sourceId": "a"}])
        self.assertEqual((invalid, untiered), ([], ["a"]))

    @staticmethod
    def observation(source_name: str, farm_name: str = "Hint Farm", source_pass: int = 2) -> Observation:
        row = empty_observation(
            "TN", source_name, farm_name, farm_name, "https://example.test", source_pass, "B"
        )
        return Observation(**row)

    def test_identity_hint_attaches_to_candidate_without_becoming_a_new_entity(self) -> None:
        candidate = self.observation("Candidate directory")
        hint = self.observation("Historic registry")
        reconciled, unrepresented = apply_source_tier_policy(
            [candidate, hint],
            {"Candidate directory": "candidate", "Historic registry": "identity_hint"},
        )
        entities, _, qa = reconcile("TN", reconciled)
        self.assertEqual(len(unrepresented), 0)
        self.assertEqual(len(entities), 1)
        self.assertEqual(entities[0]["source_observation_count"], 2)
        self.assertEqual(len(qa), 1)

    def test_unmatched_identity_hint_is_preserved_but_creates_no_entity_or_qa(self) -> None:
        hint = self.observation("Historic registry", "Historic-only farm")
        reconciled, unrepresented = apply_source_tier_policy(
            [hint], {"Historic registry": "identity_hint"}
        )
        entities, _, qa = reconcile("TN", reconciled)
        self.assertEqual(len(reconciled) + len(unrepresented), 1)
        self.assertEqual(unrepresented[0].observation_id, hint.observation_id)
        self.assertEqual((entities, qa), ([], []))

    def test_same_name_in_a_different_county_does_not_attach_identity_hint(self) -> None:
        candidate = self.observation("Candidate directory", "Same Farm")
        candidate.county = "Candidate County"
        hint = self.observation("Historic registry", "Same Farm")
        hint.county = "Different County"
        reconciled, unrepresented = apply_source_tier_policy(
            [candidate, hint],
            {"Candidate directory": "candidate", "Historic registry": "identity_hint"},
        )
        self.assertEqual([item.source_name for item in reconciled], ["Candidate directory"])
        self.assertEqual([item.source_name for item in unrepresented], ["Historic registry"])


class QaTriageTests(unittest.TestCase):
    def test_primary_strategy_follows_priority_order(self) -> None:
        primary, matched = qa_route(
            "county requires geography review; identity continuity review required"
        )
        self.assertEqual(primary, "geography")
        self.assertEqual(matched, ["geography", "identity"])

    def test_unrecognized_blocker_text_is_unrouted(self) -> None:
        self.assertEqual(qa_route("mystery condition"), ("unrouted", ["unrouted"]))

    def test_every_committed_qa_row_is_routable(self) -> None:
        for state_dir in sorted(STATE_ROOT.iterdir()):
            if not (state_dir / "entities.csv").is_file():
                continue
            with self.subTest(state=state_dir.name):
                result = triage_state(state_dir.name)
                self.assertEqual(result["unrouted"], 0,
                                 f"{state_dir.name} has unrouted QA blocker text")


class QaBackpressureTests(unittest.TestCase):
    def test_new_state_detection_uses_merge_base_tree(self) -> None:
        def runner(*args: str) -> str:
            return "" if args[-1].endswith("/NE") else "research/state-expansions/AL\n"
        self.assertEqual(new_state_directories("mb", {"NE", "AL"}, runner), ["NE"])

    def test_committed_qa_total_excludes_the_new_state(self) -> None:
        total = committed_qa_total()
        without_nc = committed_qa_total(exclude={"NC"})
        self.assertGreater(total, without_nc)
        self.assertGreater(QA_INTAKE_CAP, 0)


class PrScopeFreshnessTests(unittest.TestCase):
    def test_state_changed_on_base_after_merge_base_is_stale(self) -> None:
        def runner(*args: str) -> str:
            return "abc123\n" if args[-1].endswith("/TX") else "\n"
        self.assertEqual(
            stale_state_directories("mb", "origin/main", {"TX", "AL"}, runner), ["TX"]
        )

    def test_fresh_branch_reports_no_stale_states(self) -> None:
        self.assertEqual(
            stale_state_directories("mb", "origin/main", {"AL", "TX"}, lambda *a: ""), []
        )


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

    def test_unambiguous_census_place_corrects_broad_pick_your_own_region(self) -> None:
        item = self.observation("")
        item.city = "Lake Alfred"
        item.county = "Columbia"
        item.county_fips = "12023"
        item.county_source = "https://www.pickyourown.org/FLnorth-BakerColumbiaUnion.htm"
        apply_place_reference(
            "FL", {"name": "Florida"}, [item],
            {"lake alfred": ("Lake Alfred", "Polk", "12105")},
        )
        self.assertEqual((item.county, item.county_fips), ("Polk", "12105"))
        self.assertIn("corrected broad PickYourOwn region county", item.notes)

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

    def test_same_grade_county_conflict_prefers_census_geography(self) -> None:
        directory = self.observation("")
        directory.county = "Columbia"
        directory.county_source = "https://example.test/directory"
        directory.evidence_grade = "E"
        census = self.observation("")
        census.county = "Polk"
        census.county_source = "https://geo.fcc.gov/api/census/area"
        census.evidence_grade = "E"
        self.assertEqual(choose_county([directory, census]), "Polk")

    def test_same_grade_county_conflict_recognizes_census_place_reference(self) -> None:
        directory = self.observation("")
        directory.county = "Columbia"
        directory.county_source = "https://www.pickyourown.org/FLnorth-BakerColumbiaUnion.htm"
        directory.evidence_grade = "E"
        census = self.observation("")
        census.county = "Polk"
        census.county_source = "https://www2.census.gov/geo/docs/reference/codes2020/national_place_by_county2020.txt"
        census.evidence_grade = "E"
        self.assertEqual(choose_county([directory, census]), "Polk")

    def test_authoritative_geography_outweighs_record_evidence_grade_for_county(self) -> None:
        directory = self.observation("")
        directory.county = "Alachua"
        directory.county_source = "https://example.test/official-directory"
        directory.evidence_grade = "B"
        census = self.observation("")
        census.county = "Lake"
        census.county_source = "https://geo.fcc.gov/api/census/area"
        census.evidence_grade = "E"
        self.assertEqual(choose_county([directory, census]), "Lake")

    def test_coordinate_geography_outweighs_census_mailing_place(self) -> None:
        mailing_place = self.observation("")
        mailing_place.county = "Duval"
        mailing_place.county_source = "https://www2.census.gov/geo/docs/reference/codes2020/national_place_by_county2020.txt"
        mailing_place.evidence_grade = "E"
        coordinate = self.observation("")
        coordinate.county = "Clay"
        coordinate.county_source = "https://geo.fcc.gov/api/census/area"
        coordinate.evidence_grade = "E"
        self.assertEqual(choose_county([mailing_place, coordinate]), "Clay")


class SoutheastSourceClassificationTests(unittest.TestCase):
    def test_current_year_requires_nearby_activity_language(self) -> None:
        self.assertEqual(dated_active_excerpt("Copyright 2026 Example Farm"), ("", ""))
        year, _ = dated_active_excerpt("Our 2026 blueberry season opens May 20; orders are available now.")
        self.assertEqual(year, "2026")

    def test_nursery_parser_retains_explicit_grower_classification(self) -> None:
        rows = nursery_column_records([
            "TINY FARM",
            "Owner Name                              County: Example",
            "Physical Address:                       Greenhouses: 1",
            "1 Farm Road                             Total Sq Ft:",
            "Town , MS 39000                         Classification: Commercial",
            "Mailing Address:                        Sales Structure: Retail",
            "1 Farm Road                             SOD Acres: 0.00",
            "Town , MS 39000                         Total Acres: 2.00",
            "                                         Stock Sold:",
            "Phone #: (601) 555-0100                 VEGETABLE, FRUITING",
            "Website:",
        ])
        self.assertEqual((rows[0]["name"], rows[0]["classification"], rows[0]["county"]),
                         ("Tiny Farm", "Commercial", "Example"))

    def test_farm_named_profile_is_confirmed(self) -> None:
        self.assertTrue(farm_operation_signal("Windy Springs Farm", "", "Vegetables"))

    def test_food_manufacturer_is_not_silently_promoted_as_farm(self) -> None:
        self.assertFalse(farm_operation_signal(
            "Example Cookie Company", "We manufacture packaged cookies in Tennessee.", "Cookies"
        ))

    def test_adjacent_agriculture_entities_require_scope_review(self) -> None:
        for name in (
            "Example Farm Supply", "Example Processing", "Example Farmers Association",
            "Agriculture Museum", "Example Market and Grill", "Producer Coalition",
        ):
            with self.subTest(name=name):
                self.assertFalse(farm_entity_confirmation(name, "Vegetables and cattle", "Produce"))

    def test_product_evidence_can_confirm_a_named_producer(self) -> None:
        self.assertTrue(farm_entity_confirmation("The Garden Patch", "", "Fruit and vegetables"))

    def test_farmers_market_only_agricultural_vendor_is_in_scope(self) -> None:
        self.assertTrue(farm_entity_confirmation(
            "Viking Honey", "MDAC agricultural farmers-market vendor", ""
        ))

    def test_georgia_directory_card_is_retained_with_contact_fields(self) -> None:
        body = '''
        <h3 class="titleSmall">Tiny Georgia Farm</h3>
        <p class="paragraph">We grow vegetables.</p>
        <p class="phone-number"><strong>Phone Number:</strong> (404) 555-0100</p>
        <p class="email-address"><strong>Email Address:</strong> farm@example.com</p>
        <p><strong>Business Categories:</strong> Fruits &amp; Vegetables</p>
        <a href="https://georgiagrown.com/member/tiny-georgia-farm/">View Profile</a>
        '''
        cards = georgia_grown_cards(body)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["name"], "Tiny Georgia Farm")
        self.assertEqual(cards[0]["email"], "farm@example.com")

    def test_georgia_profile_extracts_location_and_products(self) -> None:
        card = {
            "name": "Tiny Georgia Farm",
            "url": "https://georgiagrown.com/member/tiny-georgia-farm/",
            "description": "",
            "phone": "",
            "email": "",
            "categories": "Fruits & Vegetables",
        }
        body = '''
        <section class="bg-white primary">
          <div class="gg_member_profile_single--description--company--info">
            <h1 class="title">Tiny Georgia Farm</h1>
            <p class="paragraph">Our family grows vegetables.</p>
            <a href="https://tiny.example" class="btn">Visit Website</a>
          </div>
          <h3 class="cardTitle">Products or Services Offered</h3>
          <p class="cardTitle">Fruits &amp; Vegetables</p><li>Tomatoes</li>
          <!-- RELATED -->
          <h3 class="largeLabel">Contact</h3><p>(404) 555-0100</p>
          <p><a href="mailto:farm@example.com">farm@example.com</a></p>
          <h3 class="largeLabel">Primary Location</h3>
          <p class="paragraphSmall"><strong>Tiny Georgia Farm</strong></br>1 Farm Rd</br>Athens, GA 30601</p>
        </section>
        '''
        item, _ = georgia_grown_profile("GA", STATE_CONFIG["GA"], card, body)
        self.assertEqual((item.city, item.postal_code, item.address), ("Athens", "30601", "1 Farm Rd"))
        self.assertIn("Tomatoes", item.products)
        self.assertEqual(item.entity_type_review, "farm_activity_confirmed_by_current_official_profile")

    def test_florida_archive_card_and_profile_are_parsed(self) -> None:
        archive = '''
        <article class="card:producer"><h3 class="card:producer::heading">
        <a href="https://flfarmtoyou.com/producer/tiny-farm/">Tiny Farm</a></h3></article>
        '''
        card = florida_producer_cards(archive)[0]
        profile = '''
        <main class="view:producer@single"><h2 class="block:producer::heading">Tiny Farm</h2>
        <div class="block:producer::content"><p>Our family grows vegetables.</p></div>
        <section class="block:services"><strong>Tomatoes</strong></section>
        <address class="card:producer@location::address">1 Farm Rd<br/>Gainesville, FL 32601</address>
        <a href="tel:3525550100">Call</a><a href="mail:farm@example.com">Email</a>
        </main>
        '''
        item, _ = florida_farm_to_you_profile("FL", STATE_CONFIG["FL"], card, profile)
        self.assertEqual((item.farm_name, item.city, item.postal_code), ("Tiny Farm", "Gainesville", "32601"))
        self.assertEqual(item.email, "farm@example.com")
        self.assertIn("Tomatoes", item.products)

    def test_next_page_data_returns_fdacs_page_props(self) -> None:
        body = '<script id="__NEXT_DATA__" type="application/json">{"props":{"pageProps":{"childrenInfos":[1,2]}}}</script>'
        self.assertEqual(next_page_data(body)["childrenInfos"], [1, 2])

    def test_county_casing_and_placeholder_phone_are_normalized(self) -> None:
        self.assertEqual(normalized_county("DeKalb County"), "DeKalb")
        self.assertEqual(normalized_county("McDuffie County"), "McDuffie")
        self.assertEqual(normalized_county("DeSoto County"), "DeSoto")
        self.assertEqual(sanitized_phone("(000) 000-0000"), "")
        self.assertEqual(sanitized_phone("."), "")
        self.assertEqual(sanitized_email("httpswww.facebook.comprofile.php"), "")


class CurrentStateContractTests(unittest.TestCase):
    def test_alabama_contract(self) -> None:
        self.assertEqual(validate_state("AL", False)["status"], "passed")

    def test_texas_contract(self) -> None:
        self.assertEqual(validate_state("TX", False)["status"], "passed")

    def test_arkansas_contract(self) -> None:
        self.assertEqual(validate_state("AR", False)["status"], "passed")

    def test_canonical_state_rebuild_contracts(self) -> None:
        for state in ("LA", "MS"):
            with self.subTest(state=state):
                result = validate_state(state, False)
                self.assertEqual(result["status"], "passed", result["errors"])

    def test_coverage_review_is_not_promotion_approval(self) -> None:
        for state in ("AL", "AR", "FL", "GA", "TN", "TX"):
            result = state_status(state)
            self.assertEqual(result["lifecycleStatus"], "coverage_reviewed")
            self.assertFalse(result["promotionReady"])
            self.assertFalse(result["promotable"])
            self.assertTrue(result["eligibleStagingReady"])
            self.assertTrue(result["counts"]["qa"] > 0)

    def test_eligible_handoff_keeps_qa_state_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            handoff = export_state("AL", Path(temporary))
            self.assertEqual(handoff["status"], "eligible_staged")
            self.assertEqual(handoff["eligibleCount"], 800)
            self.assertEqual(handoff["qaCount"], 7)
            self.assertEqual(handoff["qaPolicy"], "deferred_state_scoped_review")
            self.assertTrue((Path(temporary) / "AL" / "eligible-entities.csv").is_file())
            self.assertTrue((Path(temporary) / "AL" / "qa-queue.csv").is_file())

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
