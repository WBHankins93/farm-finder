"""Tests for the JSON/REST API adapter; network access is mocked."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import importlib  # noqa: E402

from collect import CollectContext  # noqa: E402


adapter_module = importlib.import_module("adapters.api")


class _Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()
        self.closed = False

    def read(self) -> bytes:
        return self.payload

    def close(self) -> None:
        self.closed = True


class TestApiAdapter(unittest.TestCase):
    def test_maps_geojson_filters_state_and_sets_provenance(self):
        payload = {
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "id": "cedar-1",
                        "name": "Cedar Grove Farm",
                        "state": "Louisiana",
                        "parish": "Acadia",
                        "city": "Crowley",
                        "products": ["vegetables", "eggs"],
                        "url": "https://cedar.example",
                    },
                    "geometry": {"type": "Point", "coordinates": [-92.37, 30.21]},
                },
                {"properties": {"name": "Out of State Farm", "state": "TX"}},
            ]
        }
        source = {"name": "Example API", "url": "https://example.test/farms"}
        response = _Response(payload)

        with patch.object(adapter_module.urllib.request, "urlopen", return_value=response) as fetch:
            farms = list(adapter_module.api(source, CollectContext("LA", "southeast")))

        fetch.assert_called_once_with(source["url"], timeout=30)
        self.assertTrue(response.closed)
        self.assertEqual(len(farms), 1)
        farm = farms[0]
        self.assertEqual(farm.id, "cedar-1")
        self.assertEqual(farm.state, "LA")
        self.assertEqual(farm.county, "Acadia")
        self.assertEqual(farm.products, ["vegetables", "eggs"])
        self.assertEqual(farm.geo.latitude, 30.21)
        self.assertEqual(farm.geo.longitude, -92.37)
        self.assertEqual(farm.provenance.source, source["name"])
        self.assertEqual(farm.provenance.source_url, source["url"])

    def test_paginates_until_empty_page(self):
        pages = {
            "https://example.test/farms?page=1": {"results": [{"name": "First Farm", "state": "LA", "county": "Acadia"}]},
            "https://example.test/farms?page=2": {"results": [{"name": "Second Farm", "state": "LA", "county": "Jefferson"}]},
            "https://example.test/farms?page=3": {"results": []},
        }
        source = {
            "name": "Paged API",
            "url": "https://example.test/farms",
            "page_param": "page",
        }
        responses = [_Response(pages[url]) for url in pages]

        with patch.object(adapter_module.urllib.request, "urlopen", side_effect=responses) as fetch:
            farms = list(adapter_module.api(source, CollectContext("LA", "southeast")))

        self.assertEqual([farm.name for farm in farms], ["First Farm", "Second Farm"])
        self.assertEqual(
            [call.args[0] for call in fetch.call_args_list],
            list(pages),
        )
        self.assertTrue(all(response.closed for response in responses))


if __name__ == "__main__":
    unittest.main()
