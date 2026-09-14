# Run capture v1

`retrievallab run --queries <JSONL> --output <new-directory> --url <service>` calls
the live service serially. Each record requires unique query_id and query; mode,
top_k and explain default to free_text, 10 and false. Limits: 4 MiB, 1,000 queries.
Invalid query syntax is captured as a per-query service error. CLI exit zero means
the capture was published; inspect error_count to assess request failures.

results.jsonl preserves requests, responses/errors and round-trip timings.
manifest.json records schema/client/service versions, snapshot/configuration,
query/result hashes, Git commit/dirty state, environment and workload. Missing Git
metadata is null. ranking_sha256 excludes request IDs and timings, so repeated
inputs on one snapshot/configuration reproduce it. Server search timing and client
round-trip timing are distinct. Publication stages files then renames the directory;
existing output is rejected. No quality metrics or benchmark claims are produced.
