"""Pipeline unit tests — stdlib unittest, no fixtures on disk, no network.

    python3 -m unittest discover -s 01-database/pipeline/tests -p "test_*.py"
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cleanse import classify_category, dedupe, decide_eligibility, parse_bool, parse_products  # noqa: E402
from geo import apply_geo_fallback  # noqa: E402
from model import CATEGORIES, Contact, Farm, Geo, Provenance, normalized_name, slugify  # noqa: E402
from privacy import clear_public_contact  # noqa: E402
from qa import run_qa, rule_reclear_now_geocoded  # noqa: E402


def farm(**kw) -> Farm:
    base = dict(id="", name="Test Farm", state="LA", county="Acadia", city="Crowley")
    base.update(kw)
    return Farm(**base)


class TestModel(unittest.TestCase):
    def test_app_record_has_exact_app_keys(self):
        expected = {
            "id", "name", "category", "region", "parish", "state", "city", "productsText",
            "products", "marketPresence", "website", "hasWebsite", "onlineStore", "facebook",
            "instagram", "farmersMarket", "csa", "ships", "onFarm", "contact", "notes",
            "source", "latitude", "longitude", "geoPrecision",
        }
        self.assertEqual(set(farm().to_app_record().keys()), expected)

    def test_record_round_trips(self):
        f = farm(id="x", website="https://a.com", products=["Honey"], geo=Geo(1.0, 2.0, "city"))
        self.assertEqual(Farm.from_record(f.to_record()).to_record(), f.to_record())

    def test_slug_matches_shipped_style(self):
        self.assertEqual(slugify("2 Guys Honey"), "2-guys-honey")

    def test_ungeocoded_never_carries_coords_to_map(self):
        self.assertFalse(farm().geo.mappable)


class TestClassification(unittest.TestCase):
    def test_beef_is_meat_not_honey(self):
        # The substring bug: "bee" inside "beef" must not win Honey/Specialty.
        self.assertEqual(classify_category("Beef; Lamb; Pork"), "Meat")

    def test_steak_is_not_specialty(self):
        # "tea" inside "steak" must not win Honey/Specialty.
        self.assertEqual(classify_category("ribeye steak, ground beef"), "Meat")

    def test_honey_still_classifies(self):
        self.assertEqual(classify_category("Raw wildflower honey"), "Honey/Specialty")

    def test_crawfish_is_seafood(self):
        self.assertEqual(classify_category("Live crawfish and shrimp"), "Seafood")

    def test_nursery_is_produce(self):
        self.assertEqual(classify_category("Nursery stock, cut flowers"), "Produce")

    def test_unknown_is_mixed(self):
        self.assertEqual(classify_category("assorted farm goods"), "Mixed")

    def test_all_outputs_are_valid_categories(self):
        for text in ("honey", "beef", "rice", "milk", "shrimp", "urban rooftop", "winery", "apples", "zzz"):
            self.assertIn(classify_category(text), CATEGORIES)


class TestParsing(unittest.TestCase):
    def test_products_split_and_dedupe(self):
        self.assertEqual(parse_products("Honey, Honey; Beeswax and Candles"), ["Honey", "Beeswax", "Candles"])

    def test_bool(self):
        self.assertTrue(parse_bool("True"))
        self.assertTrue(parse_bool("yes"))
        self.assertFalse(parse_bool("False"))
        self.assertFalse(parse_bool(""))


class TestDedupe(unittest.TestCase):
    def test_same_name_same_county_merges_and_ors_channels(self):
        a = farm(name="Bayou Farm", on_farm=True)
        b = farm(name="Bayou  Farm", farmers_market=True, website="https://b.com")
        out, collapsed = dedupe([a, b])
        self.assertEqual(collapsed, 1)
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].on_farm and out[0].farmers_market)
        self.assertEqual(out[0].website, "https://b.com")

    def test_same_name_different_county_kept_distinct(self):
        a = farm(name="Bayou Farm", county="Acadia")
        b = farm(name="Bayou Farm", county="Vermilion")
        out, collapsed = dedupe([a, b])
        self.assertEqual((collapsed, len(out)), (0, 2))

    def test_normalized_name_ignores_suffixes(self):
        self.assertEqual(normalized_name("Smith Farms LLC"), normalized_name("Smith Farm"))


class TestEligibility(unittest.TestCase):
    def test_named_and_placed_is_eligible(self):
        f = farm(provenance=Provenance(source="LDAF"))
        ok, reason = decide_eligibility(f)
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_missing_geography_blocks(self):
        f = farm(county="", city="", provenance=Provenance(source="LDAF"))
        ok, reason = decide_eligibility(f)
        self.assertFalse(ok)
        self.assertIn("geography", reason)

    def test_missing_source_blocks(self):
        ok, reason = decide_eligibility(farm())
        self.assertFalse(ok)
        self.assertIn("source", reason)


class TestGeoFallback(unittest.TestCase):
    def test_centroid_fills_ungeocoded_sibling(self):
        anchor = farm(name="A", geo=Geo(30.0, -92.0, "city"))
        anchor2 = farm(name="B", geo=Geo(30.2, -92.2, "city"))
        orphan = farm(name="C")  # ungeocoded, same county
        stats = apply_geo_fallback([anchor, anchor2, orphan])
        self.assertEqual(orphan.geo.precision, "county-approx")
        self.assertAlmostEqual(orphan.geo.latitude, 30.1, places=3)
        self.assertEqual(stats["filled_county_approx"], 1)

    def test_no_centroid_leaves_ungeocoded(self):
        orphan = farm(name="C")
        apply_geo_fallback([orphan])
        self.assertEqual(orphan.geo.precision, "ungeocoded")
        self.assertFalse(orphan.geo.mappable)

    def test_real_coord_never_overwritten(self):
        real = farm(name="A", geo=Geo(29.9, -91.9, "city"))
        other = farm(name="B", geo=Geo(30.5, -92.5, "city"))
        apply_geo_fallback([real, other])
        self.assertEqual(real.geo.latitude, 29.9)


class TestPrivacy(unittest.TestCase):
    def test_contact_held_internal_by_default(self):
        f = farm(contact=Contact(phone="555-1212"))
        self.assertEqual(f.contact.public_string(), "")

    def test_website_clears_phone_to_public(self):
        f = farm(website="https://a.com", contact=Contact(phone="555-1212"))
        self.assertTrue(clear_public_contact(f))
        self.assertEqual(f.contact.public_string(), "555-1212")

    def test_no_website_stays_internal(self):
        f = farm(contact=Contact(phone="555-1212"))
        self.assertFalse(clear_public_contact(f))
        self.assertEqual(f.contact.public_string(), "")


class TestQA(unittest.TestCase):
    def test_geography_blocked_row_auto_clears_once_mapped(self):
        f = farm(county="", city="", provenance=Provenance(source="LDAF"))
        f.eligible, f.qa_reason = decide_eligibility(f)
        self.assertFalse(f.eligible)
        # Now it has coordinates (e.g. geocode backfill placed it).
        f.geo = Geo(30.0, -92.0, "county-approx")
        f.county = "Acadia"
        cleared = rule_reclear_now_geocoded([f])
        self.assertEqual(cleared, 1)
        self.assertTrue(f.eligible)

    def test_migration_mode_preserves_prior_qa(self):
        # rules=[] must not promote a flagged row even if it now looks eligible.
        f = farm(provenance=Provenance(source="LDAF"))
        f.eligible, f.qa_reason = False, "held by prior human review"
        summary = run_qa([f], rules=[])
        self.assertEqual(summary["residue"], 1)
        self.assertFalse(f.eligible)


if __name__ == "__main__":
    unittest.main(verbosity=2)
