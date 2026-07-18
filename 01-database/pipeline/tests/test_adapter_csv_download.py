"""Tests for the CSV download adapter; network access is mocked."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import importlib  # noqa: E402

from collect import CollectContext  # noqa: E402


adapter_module = importlib.import_module("adapters.csv_download")


class _Response:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.closed = False

    def read(self) -> bytes:
        return self.payload

    def close(self) -> None:
        self.closed = True


class TestCsvDownloadAdapter(unittest.TestCase):
    def test_fetches_csv_maps_aliases_and_sets_provenance(self):
        csv_data = (
            "Business Name,Parish,City,Product List,Phone Number,Website,CSA,Latitude,Longitude\n"
            "Cedar Grove Farm,Acadia,Crowley,Vegetables; eggs,(337) 555-1212,https://cedar.example,Yes,30.21,-92.37\n"
        ).encode()
        source = {"name": "Example CSV directory", "url": "https://example.test/farms.csv"}
        response = _Response(csv_data)

        with patch.object(adapter_module.urllib.request, "urlopen", return_value=response) as fetch:
            farms = list(adapter_module.csv_download(source, CollectContext("LA", "southeast")))

        fetch.assert_called_once_with(source["url"], timeout=30)
        self.assertTrue(response.closed)
        self.assertEqual(len(farms), 1)
        farm = farms[0]
        self.assertEqual(farm.id, "cedar-grove-farm-la")
        self.assertEqual(farm.county, "Acadia")
        self.assertEqual(farm.products, ["Vegetables", "eggs"])
        self.assertEqual(farm.contact.phone, "(337) 555-1212")
        self.assertTrue(farm.csa)
        self.assertEqual(farm.geo.precision, "point")
        self.assertEqual(farm.provenance.source, source["name"])
        self.assertEqual(farm.provenance.source_url, source["url"])

    def test_field_map_supports_model_to_column_and_duplicate_ids(self):
        csv_data = (
            "record_key,producer_label,parish_source,market_flag\n"
            "shared,Cypress Roots,East Baton Rouge,No\n"
            "shared,Second Cypress,Jefferson,Yes\n"
        ).encode()
        source = {
            "name": "Mapped directory",
            "url": "https://example.test/download",
            "field_map": {
                "id": "record_key",
                "name": "producer_label",
                "parish_source": "county",
                "farmers_market": "market_flag",
            },
        }
        response = _Response(csv_data)

        with patch.object(adapter_module.urllib.request, "urlopen", return_value=response):
            farms = list(adapter_module.csv_download(source, CollectContext("LA", "southeast")))

        self.assertEqual([farm.id for farm in farms], ["shared", "shared-2"])
        self.assertEqual([farm.county for farm in farms], ["East Baton Rouge", "Jefferson"])
        self.assertFalse(farms[0].farmers_market)
        self.assertTrue(farms[1].farmers_market)


if __name__ == "__main__":
    unittest.main()
