"""Tests for the PDF list adapter; network access is mocked."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import importlib  # noqa: E402

from collect import CollectContext  # noqa: E402


adapter_module = importlib.import_module("adapters.pdf_list")


def pdf_fixture() -> bytes:
    content = b"\n".join(
        [
            b"BT 10 100 Td (PARISH) Tj ET",
            b"BT 100 100 Td (NAME) Tj ET",
            b"BT 200 100 Td (ADDRESS) Tj ET",
            b"BT 300 100 Td (PHONE) Tj ET",
            b"BT 10 80 Td (ACADIA) Tj ET",
            b"BT 100 80 Td (Cedar Grove Farm) Tj ET",
            b"BT 200 80 Td (123 Main St, Crowley, LA 70526) Tj ET",
            b"BT 300 80 Td ((337) 555-1212) Tj ET",
        ]
    )
    return (
        b"%PDF-1.4\n"
        + b"1 0 obj\n<< /Length "
        + str(len(content)).encode()
        + b" >>\nstream\n"
        + content
        + b"\nendstream\nendobj\n%%EOF\n"
    )


class _Response:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.closed = False

    def read(self) -> bytes:
        return self.payload

    def close(self) -> None:
        self.closed = True


class TestPdfListAdapter(unittest.TestCase):
    def test_fetches_pdf_and_maps_table_row_with_provenance(self):
        source = {"name": "Example producer list", "url": "https://example.test/list.pdf"}
        response = _Response(pdf_fixture())
        with patch.object(adapter_module.urllib.request, "urlopen", return_value=response) as fetch:
            farms = list(adapter_module.pdf_list(source, CollectContext("LA", "southeast")))

        fetch.assert_called_once_with(source["url"], timeout=30)
        self.assertTrue(response.closed)
        self.assertEqual(len(farms), 1)
        farm = farms[0]
        self.assertEqual(farm.id, "cedar-grove-farm-la")
        self.assertEqual(farm.name, "Cedar Grove Farm")
        self.assertEqual(farm.state, "LA")
        self.assertEqual(farm.county, "ACADIA")
        self.assertEqual(farm.city, "Crowley")
        self.assertEqual(farm.contact.phone, "(337) 555-1212")
        self.assertEqual(farm.provenance.source, source["name"])
        self.assertEqual(farm.provenance.source_url, source["url"])


if __name__ == "__main__":
    unittest.main()
