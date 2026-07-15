# FarmFinder state releases

Every state uses the same seven-file repository contract:

1. `state-config.json` — stable geography, lifecycle, and size rules.
2. `sources.json` — the reviewed source catalog and three-pass decisions.
3. `manual-decisions.csv` — human-authored inclusion, correction, merge, and exclusion decisions.
4. `entities.csv` — the only committed staged entity table for the state.
5. `county-coverage.csv` — the official county denominator and coverage result.
6. `completion-report.md` — findings, limitations, and unresolved work.
7. `release-manifest.json` — counts, hashes, and immutable evidence-object references.

Raw observations, source payloads, request logs, QA queues, identity diagnostics,
exclusions, and geography errors are release evidence rather than repository source.
They are stored as private compressed objects under the manifest's versioned
S3-compatible prefix. Local working copies live under the ignored
`data/source-releases/` tree and are never the only durable copy approved for
promotion.

Run the common contract validator from the repository root:

```bash
python3 01-database/tools/validate_state_releases.py
```

Use `--require-local-artifacts` while building or migrating a release. Managed
object storage remains required before a state can move from `coverage_reviewed`
to `record_verified` or `promoted`.

After a collector writes its ignored work files, package and stage a release with:

```bash
03-app/site/.venv/bin/python 01-database/tools/package_state_release.py \
  --state TX --upload
```

The pull-request workflow runs the shared validator automatically for every state.
