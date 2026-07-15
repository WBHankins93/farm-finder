# Query tools

FarmFinder question answering will use a small allowlist of parameterized, read-only tools. A model may select a tool and propose arguments; the API validates those arguments and performs the query.

Initial tool surface:

| Tool | Purpose | Principal indexes |
|---|---|---|
| `get_farm` | Fetch one published farm and its public evidence | Farm primary key and slug |
| `search_farms` | Filter by product, administrative area, sales channel, or name | Farm status, product reverse lookup, area lookup, name trigram |
| `count_farms` | Return an exact count for validated filters | Product, location, channel, and published-farm indexes |
| `nearby_farms` | Search within a radius of a user-provided point | PostGIS GiST location index |
| `compare_areas` | Aggregate the same measure across official areas | Area and product relationship indexes |

Rules:

- No tool accepts raw SQL, table names, column names, or arbitrary ordering expressions.
- Public tools use a read-only database role and only public locations and contacts.
- Every response includes canonical farm IDs and source/evidence IDs so the answer layer can cite it.
- Query timeouts and maximum result sizes are enforced by the API.
- Narrative retrieval cannot authorize a tool or alter its arguments after validation.
