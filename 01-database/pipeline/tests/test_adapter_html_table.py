"""Tests for the HTML table adapter; network access is mocked."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import importlib  # noqa: E402

from collect import CollectContext  # noqa: E402


adapter_module = importlib.import_module("adapters.html_table")


class _Response:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.closed = False

    def read(self) -> bytes:
        return self.payload

    def close(self) -> None:
        self.closed = True


class TestHtmlTableAdapter(unittest.TestCase):
    def test_fetches_and_maps_table_row_with_provenance(self):
        html = b"""
            <table>
              <tr><th>Producer Name</th><th>Parish</th><th>City</th>
                  <th>Address</th><th>Phone</th><th>Email</th>
                  <th>Products</th><th>Website</th></tr>
              <tr><td><a href='/farms/cedar'>Cedar Grove Farm</a></td>
                  <td>Acadia</td><td>Crowley</td><td>123 Main St</td>
                  <td>(337) 555-1212</td><td><a href='mailto:farmer@example.com'>Email</a></td>
                  <td>Vegetables; eggs</td><td><a href='https://cedar.example'>Visit</a></td></tr>
            </table>
        """
        source = {"name": "Example producer list", "url": "https://example.test/list"}
        response = _Response(html)
        with patch.object(adapter_module.urllib.request, "urlopen", return_value=response) as fetch:
            farms = list(adapter_module.html_table(source, CollectContext("LA", "southeast")))

        fetch.assert_called_once_with(source["url"], timeout=30)
        self.assertTrue(response.closed)
        self.assertEqual(len(farms), 1)
        farm = farms[0]
        self.assertEqual(farm.id, "cedar-grove-farm-la")
        self.assertEqual(farm.name, "Cedar Grove Farm")
        self.assertEqual(farm.county, "Acadia")
        self.assertEqual(farm.city, "Crowley")
        self.assertEqual(farm.contact.phone, "(337) 555-1212")
        self.assertEqual(farm.contact.email, "farmer@example.com")
        self.assertEqual(farm.contact.address, "123 Main St")
        self.assertEqual(farm.products_text, "Vegetables; eggs")
        self.assertEqual(farm.website, "https://cedar.example")
        self.assertEqual(farm.provenance.source, source["name"])
        self.assertEqual(farm.provenance.source_url, source["url"])

    def test_expands_spans_and_disambiguates_duplicate_names(self):
        html = b"""
            <table>
              <tr><th>Name</th><th>County</th><th>Farmers Market</th></tr>
              <tr><td rowspan='2'>Twin Oaks</td><td>Avoyelles</td><td>Yes</td></tr>
              <tr><td colspan='1'>Iberville</td><td>No</td></tr>
            </table>
        """
        source = {"name": "Directory", "url": "https://example.test/list"}
        response = _Response(html)
        with patch.object(adapter_module.urllib.request, "urlopen", return_value=response):
            farms = list(adapter_module.html_table(source, CollectContext("LA", "southeast")))

        self.assertEqual([farm.id for farm in farms], ["twin-oaks-la", "twin-oaks-la-2"])
        self.assertEqual([farm.county for farm in farms], ["Avoyelles", "Iberville"])
        self.assertTrue(farms[0].farmers_market)
        self.assertFalse(farms[1].farmers_market)


if __name__ == "__main__":
    unittest.main()
