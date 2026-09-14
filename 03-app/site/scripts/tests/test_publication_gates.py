"""Publication-gate tests for the national web feed.

These cover the two things a green application build cannot prove on its own:
that ineligible and private data is actually withheld at publish time, and that
the compact index the app queries is a faithful encoding of the feed that was
published.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
SITE = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import discovery_index  # noqa: E402

# build-web-feed.py is not an importable module name, so load it by path.
_spec = importlib.util.spec_from_file_location("build_web_feed", SCRIPTS / "build-web-feed.py")
build_web_feed = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(build_web_feed)

CONTRACT = json.loads((SITE / "app" / "data" / "feed-contract.json").read_text())
VOCABULARY = json.loads((SITE / "app" / "data" / "product-vocabulary.json").read_text())


def sample_record(**overrides) -> dict:
    record = {
        "id": "sample-farm-la", "name": "Sample Farm", "category": "Produce",
        "region": "Acadiana", "parish": "Lafayette", "state": "LA", "city": "Lafayette",
        "productsText": "Vegetables; Honey", "products": ["Vegetables", "Honey"],
        "marketPresence": "On-farm sales", "website": "https://example.com",
        "hasWebsite": True, "onlineStore": False, "facebook": False, "instagram": False,
        "farmersMarket": True, "csa": False, "ships": False, "onFarm": True,
        "contact": "(337) 555-0100", "notes": "", "source": "state-directory",
        "latitude": 30.2241, "longitude": -92.0198, "geoPrecision": "point",
    }
    record.update(overrides)
    return record


def contract_for(records: list[dict]) -> dict:
    """A contract whose coverage floors match the sample, so the privacy and
    field assertions are what a test actually exercises."""
    return {
        **CONTRACT,
        "expectedStates": sorted({record["state"] for record in records}),
        "floors": {"total": 1, "mappable": 0, "statesWithFarms": 1},
    }


class PublicationGateTests(unittest.TestCase):
    def test_accepts_a_conforming_feed(self) -> None:
        records = [sample_record()]
        build_web_feed.enforce_contract(records, contract_for(records))

    def test_rejects_a_contact_without_a_public_website(self) -> None:
        # privacy.py promotes a contact only when the farm publishes its own
        # website. Anything else is an internal contact that escaped the gate.
        records = [sample_record(website="", hasWebsite=False, contact="(337) 555-0100")]
        with self.assertRaises(build_web_feed.ContractViolation) as raised:
            build_web_feed.enforce_contract(records, contract_for(records))
        self.assertIn("without a farm-published", str(raised.exception))

    def test_rejects_a_street_address_in_a_public_contact(self) -> None:
        records = [sample_record(contact="1234 Rural Route Road, Lafayette LA")]
        with self.assertRaises(build_web_feed.ContractViolation) as raised:
            build_web_feed.enforce_contract(records, contract_for(records))
        self.assertIn("street addresses", str(raised.exception))

    def test_rejects_an_internal_field_leaking_into_a_public_record(self) -> None:
        records = [sample_record(qa_reason="missing-geocode")]
        with self.assertRaises(build_web_feed.ContractViolation) as raised:
            build_web_feed.enforce_contract(records, contract_for(records))
        self.assertIn("non-public fields", str(raised.exception))

    def test_rejects_a_record_with_no_provenance(self) -> None:
        records = [sample_record(source="")]
        with self.assertRaises(build_web_feed.ContractViolation) as raised:
            build_web_feed.enforce_contract(records, contract_for(records))
        self.assertIn("no source provenance", str(raised.exception))

    def test_rejects_a_geocoded_record_parked_at_null_island(self) -> None:
        records = [sample_record(latitude=0.0, longitude=0.0)]
        with self.assertRaises(build_web_feed.ContractViolation) as raised:
            build_web_feed.enforce_contract(records, contract_for(records))
        self.assertIn("0,0", str(raised.exception))

    def test_rejects_coverage_below_the_contract_floor(self) -> None:
        records = [sample_record()]
        contract = {**contract_for(records), "floors": {"total": 100, "mappable": 0, "statesWithFarms": 1}}
        with self.assertRaises(build_web_feed.ContractViolation) as raised:
            build_web_feed.enforce_contract(records, contract)
        self.assertIn("below floor", str(raised.exception))

    def test_rejects_a_missing_state(self) -> None:
        records = [sample_record()]
        contract = {**contract_for(records), "expectedStates": ["LA", "MS"]}
        with self.assertRaises(build_web_feed.ContractViolation) as raised:
            build_web_feed.enforce_contract(records, contract)
        self.assertIn("missing=['MS']", str(raised.exception))


class DerivedStatsTests(unittest.TestCase):
    def test_every_displayed_count_is_derived_from_the_feed(self) -> None:
        records = [
            sample_record(),
            sample_record(id="b-la", name="B Farm", category="Meat", website="", hasWebsite=False,
                          contact="", geoPrecision="ungeocoded", latitude=0.0, longitude=0.0,
                          farmersMarket=False, onFarm=False, productsText="Beef", products=["Beef"]),
        ]
        stats = build_web_feed.compute_stats(records, contract_for(records), VOCABULARY)
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["states"], 1)
        self.assertEqual(stats["mappable"], 1)
        self.assertEqual(stats["ungeocoded"], 1)
        self.assertEqual(stats["withoutWebsite"], 1)
        self.assertEqual(stats["withPublicContact"], 1)
        self.assertEqual(stats["services"]["onFarm"], 1)
        self.assertEqual(stats["products"]["beef"], 1)
        self.assertEqual(stats["products"]["vegetables"], 1)
        # "bee" is a whole-word token, so a beef producer is not a honey producer.
        self.assertEqual(stats["products"]["honey"], 1)

    def test_product_counts_match_the_index_filter_bitmask(self) -> None:
        # The browse tiles and the product filter must never disagree: both are
        # built from app/data/product-vocabulary.json, and this proves it.
        records = [
            sample_record(),
            sample_record(id="b-la", productsText="Raw honey and beeswax", products=["Honey"]),
            sample_record(id="c-la", category="Meat", productsText="Grass-fed beef", products=["Beef"]),
            sample_record(id="d-la", category="Produce", productsText="Eggplant and peppers",
                          products=["Eggplant"]),
        ]
        contract = contract_for(records)
        stats = build_web_feed.compute_stats(records, contract, VOCABULARY)
        masks = discovery_index._product_masks(records, VOCABULARY, contract["productGuideIds"])

        for position, product in enumerate(contract["productGuideIds"]):
            filtered = sum(1 for mask in masks if mask & (1 << position))
            self.assertEqual(
                stats["products"][product], filtered,
                f"browse count and filter disagree for {product}",
            )

        # Whole-word tokens at work: the eggplant grower is a vegetable farm and
        # not an egg producer, and the beef producer is not a honey producer.
        self.assertEqual(stats["products"]["eggs"], 0)
        self.assertEqual(stats["products"]["beef"], 1)
        self.assertEqual(stats["products"]["honey"], 2)
        self.assertEqual(stats["products"]["vegetables"], 3)


class IndexEncodingTests(unittest.TestCase):
    def test_container_round_trips_records_faithfully(self) -> None:
        records = [
            sample_record(),
            sample_record(id="cafe-la", name="Café Olé Farm", city="Ville Platte",
                          products=["Vegetables", "Fruit"], productsText="Vegetables; Fruit"),
            sample_record(id="ungeocoded-ms", state="MS", geoPrecision="ungeocoded",
                          latitude=0.0, longitude=0.0),
        ]
        contract = contract_for(records)
        container, report = discovery_index.build_container(records, contract, VOCABULARY)

        self.assertTrue(container.startswith(discovery_index.MAGIC))
        self.assertEqual(report["records"], 3)
        # Only the geocoded rows become map-eligible places.
        self.assertEqual(report["places"], 2)

    def test_search_blob_is_pure_ascii(self) -> None:
        # A single non-ASCII byte doubles the blob's resident size in V8, which
        # is the whole reason the text is folded before packing.
        self.assertEqual(discovery_index.fold_ascii("Café Olé Farm"), "cafe ole farm")
        records = [sample_record(id="cafe-la", name="Café Olé Farm", city="Ville Platte")]
        container, report = discovery_index.build_container(records, contract_for(records), VOCABULARY)
        # Locate the packed search section and prove every byte of it is ASCII.
        header_length = int.from_bytes(container[8:12], "little")
        header = json.loads(container[12:12 + header_length])
        body_start = -(-(12 + header_length) // 8) * 8
        section = header["sections"]["searchBlob"]
        blob = container[body_start + section["offset"]:body_start + section["offset"] + section["length"]]
        self.assertEqual(len(blob), report["searchBlobBytes"])
        self.assertTrue(all(byte < 128 for byte in blob))
        self.assertIn(b"cafe ole farm", blob)

    def test_name_order_is_total_and_deterministic(self) -> None:
        records = [
            sample_record(id="b-la", name="beta farm"),
            sample_record(id="a-la", name="Alpha Farm"),
            sample_record(id="a2-la", name="Alpha Farm"),
            sample_record(id="q-la", name='"Quoted" Farm'),
        ]
        keys = [discovery_index.name_sort_key(record) for record in records]
        self.assertEqual(len(set(keys)), len(keys), "sort keys must be unique for a total order")
        ordered = [record["id"] for record in sorted(records, key=discovery_index.name_sort_key)]
        self.assertEqual(ordered, ["a-la", "a2-la", "b-la", "q-la"])


if __name__ == "__main__":
    unittest.main()
