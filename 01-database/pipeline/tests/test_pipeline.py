"""Pipeline unit tests — stdlib unittest, no fixtures on disk, no network.

    python3 -m unittest discover -s 01-database/pipeline/tests -p "test_*.py"
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import collect  # noqa: E402
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


class TestAggregateDedupe(unittest.TestCase):
    def test_merges_exact_cross_file_collision(self):
        from cleanse import aggregate_dedupe
        a = farm(name="Bayou Farm", state="LA", county="Acadia", on_farm=True)
        b = farm(name="Bayou Farm", state="LA", county="Acadia", farmers_market=True)
        out, merged = aggregate_dedupe([a, b])
        self.assertEqual((merged, len(out)), (1, 1))
        self.assertTrue(out[0].on_farm and out[0].farmers_market)

    def test_keeps_cross_county_same_name(self):
        from cleanse import aggregate_dedupe
        out, merged = aggregate_dedupe([
            farm(name="Bayou Farm", county="Acadia"),
            farm(name="Bayou Farm", county="Vermilion"),
        ])
        self.assertEqual((merged, len(out)), (0, 2))

    def test_near_dup_reporter_ignores_city_centroids(self):
        from cleanse import near_duplicate_clusters
        # Same city centroid, unrelated names -> not a near-dup.
        a = farm(name="Alpha Ranch", geo=Geo(30.0, -90.0, "city"))
        b = farm(name="Beta Gardens", geo=Geo(30.0, -90.0, "city"))
        self.assertEqual(near_duplicate_clusters([a, b]), 0)

    def test_near_dup_reporter_flags_precise_name_variants(self):
        from cleanse import near_duplicate_clusters
        a = farm(name="Highland Springs Farm", geo=Geo(33.9, -117.0, "point"))
        b = farm(name="Highland Springs Farm at Resort", geo=Geo(33.9, -117.0, "point"))
        self.assertEqual(near_duplicate_clusters([a, b]), 1)


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


class TestAdapterDiscovery(unittest.TestCase):
    def test_load_adapters_registers_dropped_in_module(self):
        """A new file in pipeline/adapters/ must register with zero engine edits."""
        adapters_dir = Path(__file__).resolve().parents[1] / "adapters"
        probe = adapters_dir / "zz_probe.py"
        probe.write_text(
            "from collect import adapter\n"
            "@adapter('zz_probe')\n"
            "def zz_probe(source, ctx):\n"
            "    return []\n"
        )
        try:
            collect._adapters_loaded = False  # force a re-scan
            names = collect.load_adapters()
            self.assertIn("zz_probe", names)
            self.assertIn("staged", names)
        finally:
            probe.unlink()
            for pyc in (adapters_dir / "__pycache__").glob("zz_probe*"):
                pyc.unlink()
            collect.ADAPTERS.pop("zz_probe", None)

    def test_underscore_modules_are_skipped(self):
        adapters_dir = Path(__file__).resolve().parents[1] / "adapters"
        scratch = adapters_dir / "_scratch.py"
        scratch.write_text("raise RuntimeError('must never be imported')\n")
        try:
            collect._adapters_loaded = False
            collect.load_adapters()  # must not raise
        finally:
            scratch.unlink()

    def test_collect_state_triggers_discovery(self):
        collect._adapters_loaded = False
        collect.collect_state(
            {"state": "XX", "region": "test", "sources": []},
            collect.CollectContext(state="XX", region="test"),
        )
        self.assertTrue(collect._adapters_loaded)


class TestQA(unittest.TestCase):
    def test_geography_blocked_row_auto_clears_with_real_geocode(self):
        f = farm(county="", city="", provenance=Provenance(source="LDAF"))
        f.eligible, f.qa_reason = decide_eligibility(f)
        self.assertFalse(f.eligible)
        # A real geocode (city precision) placed it.
        f.geo = Geo(30.0, -92.0, "city")
        f.county = "Acadia"
        cleared = rule_reclear_now_geocoded([f])
        self.assertEqual(cleared, 1)
        self.assertTrue(f.eligible)

    def test_county_approx_centroid_never_clears_geography(self):
        # The centroid derives from the doubted county — circular, must not clear.
        f = farm(qa_reason="county requires geography review",
                 geo=Geo(30.0, -92.0, "county-approx"))
        f.eligible = False
        self.assertEqual(rule_reclear_now_geocoded([f]), 0)
        self.assertFalse(f.eligible)

    def test_migrated_geography_reason_clears_with_real_geocode(self):
        f = farm(qa_reason="county requires geography review",
                 geo=Geo(35.5, -80.0, "city"))
        f.eligible = False
        self.assertEqual(rule_reclear_now_geocoded([f]), 1)
        self.assertTrue(f.eligible)

    def test_no_county_but_real_coord_clears(self):
        # A geocoded point resolves a "county requires review" blocker even when
        # the county field itself is still blank — the point implies the county.
        f = farm(county="", qa_reason="county requires geography review",
                 geo=Geo(35.5, -80.0, "city"))
        f.eligible = False
        self.assertEqual(rule_reclear_now_geocoded([f]), 1)
        self.assertTrue(f.eligible)

    def test_mixed_blockers_stay_residue(self):
        # Geography plus a non-geography blocker must NOT auto-clear.
        f = farm(qa_reason="county requires geography review; needs corroboration",
                 geo=Geo(35.5, -80.0, "city"))
        f.eligible = False
        self.assertEqual(rule_reclear_now_geocoded([f]), 0)
        self.assertFalse(f.eligible)

    def test_migration_mode_preserves_prior_qa(self):
        # rules=[] must not promote a flagged row even if it now looks eligible.
        f = farm(provenance=Provenance(source="LDAF"))
        f.eligible, f.qa_reason = False, "held by prior human review"
        summary = run_qa([f], rules=[])
        self.assertEqual(summary["residue"], 1)
        self.assertFalse(f.eligible)


class TestOrchestrator(unittest.TestCase):
    """End-to-end run.py: a fake adapter + temp config, no network."""

    def setUp(self):
        import collect
        self.pipeline = Path(__file__).resolve().parents[1]
        self.cfg_dir = self.pipeline / "sources" / "_test"
        self.cfg_dir.mkdir(parents=True, exist_ok=True)
        self.cfg = self.cfg_dir / "ZZ.json"
        self.cfg.write_text('{"state":"ZZ","name":"Testland","region":"_test",'
                            '"sources":[{"id":"s1","name":"Fake","url":"","adapter":"faketest"}]}')
        self.data = self.pipeline / "data" / "ZZ.json"

        collect._adapters_loaded = True  # skip disk discovery; register inline

        @collect.adapter("faketest")
        def _fake(source, ctx):
            return [
                Farm(id="", name="Good Farm", state="ZZ", county="Test", city="Town",
                     products_text="honey", provenance=Provenance(source="Fake")),
                Farm(id="", name="No Place Farm", state="ZZ", county="", city="",
                     provenance=Provenance(source="Fake")),  # missing geography -> residue
            ]

    def tearDown(self):
        import collect
        collect.ADAPTERS.pop("faketest", None)
        collect._adapters_loaded = False
        for p in (self.cfg, self.data, self.pipeline / "build" / "qa-residue-ZZ.csv"):
            if p.exists():
                p.unlink()
        if self.cfg_dir.exists():
            self.cfg_dir.rmdir()

    def test_run_state_collects_and_persists(self):
        import run
        stats = run.run_state("ZZ")
        self.assertEqual(stats["count"], 2)
        self.assertEqual(stats["bridged"], 0)  # ZZ has no entities.csv
        self.assertTrue(self.data.exists())
        rows = json.loads(self.data.read_text())
        self.assertEqual(len(rows), 2)

    def test_run_state_decides_fresh_eligibility(self):
        import run
        run.run_state("ZZ")
        rows = {r["name"]: r for r in json.loads(self.data.read_text())}
        # Fresh live rows get decided: placed+sourced is eligible, no-geography is residue.
        self.assertTrue(rows["Good Farm"]["eligible"])
        self.assertFalse(rows["No Place Farm"]["eligible"])
        self.assertIn("geography", rows["No Place Farm"]["qa_reason"])

    def test_publish_prefers_live_data_over_bridge(self):
        import run
        run.run_state("ZZ")
        stats = run.publish_all()
        self.assertIn("ZZ", stats["live_states"])
        self.assertGreater(stats["written"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
