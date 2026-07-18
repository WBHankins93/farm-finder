# Source config schema

One file per state: `sources/<region>/<ST>.json`. This is the *entire* input a
state contributes — the collection logic lives once in `engine`/`collect.py`.
Adding a state is adding one of these files. Adding a *kind* of source is adding
one adapter in `collect.py`; the two never entangle.

```jsonc
{
  "state": "LA",                     // USPS code (uppercase)
  "name": "Louisiana",
  "region": "southeast",             // must match a key in regions.json
  "countyEquivalentLabel": "parish", // "county" for every state except LA
  "sources": [
    {
      "id": "ldaf-fmnp-roadside",    // stable slug, unique within the state
      "name": "LDAF 2026 FMNP roadside-stand directory",
      "url": "https://www.ldaf.la.gov/fmnp",
      "adapter": "pdf_list",         // which collector adapter reads this source
      "notes": "Only entries explicitly labeled roadside stands are farms."
    }
  ]
}
```

## Fields

| field | required | notes |
|---|---|---|
| `state` | yes | USPS code; must be listed under its region in `regions.json`. |
| `name` | yes | Full state name. |
| `region` | yes | Region key from `regions.json`. |
| `countyEquivalentLabel` | yes | `parish` for LA, else `county`. |
| `sources[].id` | yes | Stable, unique-within-state slug. |
| `sources[].name` | yes | Human-readable source name (becomes a record's provenance). |
| `sources[].url` | yes | Source URL (becomes provenance source_url). |
| `sources[].adapter` | yes | One of the registered adapter types (below). |
| `sources[].notes` | no | Scope / caveats for reviewers. |

## Adapter types

| adapter | status | owner |
|---|---|---|
| `staged` | working | engine — bridge that re-emits already-migrated rows |
| `csv_download` | to build | Codex — fetch + field-map a CSV directory |
| `html_table` | to build | Codex — parse an HTML listing |
| `pdf_list` | to build | Codex — extract a PDF certificate/permit list |
| `api` | to build | Codex — pull a JSON/REST source |

During the transition every state config may keep a single `{"adapter":"staged"}`
source so the engine runs end-to-end. As live adapters are written for a state,
replace `staged` with the real sources.

## Scaffolding existing states

The 10 already-collected states have their real source lists inside
`research/state-expansions/<ST>/state.yaml` (`collection.sources`). Generate their
configs with:

```bash
python3 01-database/pipeline/scaffold_sources.py
```

This writes `sources/<region>/<ST>.json` for each, pre-mapping known source
types to adapters and defaulting the rest to `staged`. Codex then upgrades the
adapters state-by-state.
