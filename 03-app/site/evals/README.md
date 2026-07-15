# FarmFinder evaluations

Evals are executable product expectations. They are not the runtime guardrails themselves.

Runtime guardrails live in the API: authentication, authorization, input validation, a read-only tool allowlist, query timeouts, PII redaction, and separation of retrieved data from system instructions. Evals prove those controls continue to work.

## Evaluation layers

1. **Routing:** Does the question choose structured SQL, narrative retrieval, both, or no AI?
2. **Tool arguments:** Are product, geography, distance, and sales-channel arguments valid and normalized?
3. **Data correctness:** Do counts and returned farm IDs match a pinned dataset release?
4. **Citation grounding:** Does each material claim point to a farm record or document chunk?
5. **Safety:** Are prompt injection, unauthorized writes, private contact requests, and exact-location disclosure rejected?
6. **Quality and operations:** Are latency, token use, and estimated cost within the release budget?

Deterministic database and policy evals will run on every pull request. A small live-model suite will run on a controlled schedule because model calls are nondeterministic and incur cost. Every eval result records the dataset release, schema migration, model, prompt version, and query-tool version.

`cases/foundation.jsonl` contains the initial expectations. It is deliberately small until the query tools exist.
