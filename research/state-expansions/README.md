# FarmFinder state releases

Every state uses the same four-file repository contract:

1. `state.yaml` — configuration, source plan, lifecycle, counts, and immutable evidence pointers.
2. `entities.csv` — retained normalized candidates, including unresolved name-only discoveries.
3. `decisions.csv` — append-only corrections, merges, corroborations, and evidence-backed exclusions.
4. `report.md` — generated coverage, QA, validation, and promotion summary.

Missing data never excludes or deletes a named farm. It keeps the candidate in
`research_or_qa_queue` for later enrichment. Raw observations and generated QA views
live in managed versioned storage or the staging database, not Git.

Run the shared checks from the repository root:

```bash
python3 -m unittest discover -s 01-database/tools/tests -p "test_*.py"
python3 01-database/tools/validate_state_releases.py
python3 01-database/tools/state_release_status.py AL TX
```
