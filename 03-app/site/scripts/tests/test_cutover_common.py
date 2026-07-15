from __future__ import annotations

import unittest

from cutover_common import (
    candidate_entity_count,
    duplicate_groups,
    record_hash,
    source_records,
)


class CutoverCommonTests(unittest.TestCase):
    def test_source_keys_are_stable_across_row_reordering(self) -> None:
        rows = [
            {"Farm Name": "Alpha Farm", "Source Tab": "LA Directory", "Value": 1},
            {"Farm Name": "Beta Farm", "Source Tab": "MS Directory", "Value": 2},
        ]
        forward = {
            row["raw_data"]["Farm Name"]: row["source_record_key"]
            for row in source_records(rows)
        }
        reverse = {
            row["raw_data"]["Farm Name"]: row["source_record_key"]
            for row in source_records(reversed(rows))
        }
        self.assertEqual(forward, reverse)

    def test_duplicate_names_remain_separate_evidence_rows(self) -> None:
        rows = [
            {"Farm Name": "Same Farm", "Source Tab": "Source A"},
            {"Farm Name": "Same Farm", "Source Tab": "Source B"},
        ]
        records = source_records(rows)
        self.assertEqual(len(records), 2)
        self.assertEqual(candidate_entity_count(records), 1)
        self.assertEqual(duplicate_groups(records), ["same farm"])
        self.assertNotEqual(
            records[0]["source_record_key"], records[1]["source_record_key"]
        )

    def test_record_hash_is_order_independent(self) -> None:
        self.assertEqual(record_hash({"a": 1, "b": 2}), record_hash({"b": 2, "a": 1}))


if __name__ == "__main__":
    unittest.main()
