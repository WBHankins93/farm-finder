"""T1 source isolation and dry-run proposal regressions; no live adapters."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PIPELINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PIPELINE))

import collect  # noqa: E402
import run  # noqa: E402
from model import Farm  # noqa: E402


class SourceProposalTests(unittest.TestCase):
    def setUp(self):
        self.previous = collect.ADAPTERS.get("fixture_proposal")
        self.iterator = lambda: iter(())
        collect.ADAPTERS["fixture_proposal"] = lambda source, ctx: self.iterator()

    def tearDown(self):
        if self.previous is None:
            collect.ADAPTERS.pop("fixture_proposal", None)
        else:
            collect.ADAPTERS["fixture_proposal"] = self.previous

    def collect(self, iterator, required=False):
        ctx = collect.CollectContext("LA", "south")
        config = {"state": "LA", "sources": [{
            "id": "fixture", "adapter": "fixture_proposal", "required": required,
        }]}
        self.iterator = lambda: iterator
        rows = collect.collect_state(config, ctx)
        return rows, ctx

    def test_empty_iterator_is_a_completed_empty_observation(self):
        rows, ctx = self.collect(iter(()))
        self.assertEqual(rows, [])
        self.assertEqual(ctx.source_outcomes[0]["status"], "empty")
        self.assertEqual(ctx.source_outcomes[0]["completion_basis"], "iterator_exhausted")

    def test_iterator_failure_discards_partial_rows(self):
        def broken():
            yield Farm(id="", name="Partial", state="LA")
            raise OSError("fixture detail")

        rows, ctx = self.collect(broken())
        self.assertEqual(rows, [])
        outcome = ctx.source_outcomes[0]
        self.assertEqual(outcome["status"], "partial")
        self.assertEqual(outcome["failure_type"], "OSError")
        self.assertNotIn("fixture detail", json.dumps(outcome))

    def test_malformed_item_discards_source_rows(self):
        rows, ctx = self.collect(iter([Farm(id="", name="Good", state="LA"), {"name": "bad"}]))
        self.assertEqual(rows, [])
        self.assertEqual(ctx.source_outcomes[0]["status"], "partial")
        self.assertEqual(ctx.source_outcomes[0]["failure_type"], "TypeError")

    def test_dry_run_writes_private_proposal_without_changing_canonical_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sources = root / "LA.json"
            sources.write_text(json.dumps({
                "state": "LA", "region": "south", "sources": [{
                    "id": "fixture", "adapter": "fixture_proposal", "required": True,
                }],
            }))
            canonical_dir = root / "data"
            canonical_dir.mkdir()
            canonical = canonical_dir / "LA.json"
            canonical.write_bytes(b'[{"id":"existing"}]\n')
            before = canonical.read_bytes()

            self.iterator = lambda: iter([Farm(id="", name="Observed", state="LA")])
            build = root / "build"
            with patch.object(run, "find_config", return_value=sources), \
                 patch.object(run, "DATA", canonical_dir), patch.object(run, "BUILD", build):
                result = run.propose_state("la")

            self.assertEqual(canonical.read_bytes(), before)
            proposal_path = result["proposal_path"]
            proposal = json.loads(proposal_path.read_text())
            self.assertEqual(proposal["base_canonical_sha256"], run._sha256_file(canonical))
            self.assertEqual(proposal["observations"][0]["records"][0]["name"], "Observed")
            self.assertEqual(proposal["source_outcomes"][0]["status"], "complete")
            self.assertEqual(result["required_failures"], [])
            self.assertEqual(os.stat(proposal_path).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(proposal_path.parent).st_mode & 0o777, 0o700)

    def test_required_partial_source_is_machine_detectable(self):
        def broken():
            yield Farm(id="", name="Partial", state="LA")
            raise RuntimeError("safe detail not persisted")

        _, ctx = self.collect(broken(), required=True)
        required_failures = [
            outcome["source_id"] for outcome in ctx.source_outcomes
            if outcome["required"] and outcome["status"] in ("failed", "partial", "disabled")
        ]
        self.assertEqual(required_failures, ["fixture"])


if __name__ == "__main__":
    unittest.main()
