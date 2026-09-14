# Local HTTP API v1

Start retrievald with --corpus <snapshot> --listen 127.0.0.1:8091. Corpus validation
and index construction finish before listening. Only numeric loopback addresses
are accepted. SIGINT/SIGTERM drain requests with a ten-second shutdown deadline.

GET /healthz, /readyz and /v1/stats expose health, pinned snapshot and statistics.
POST /v1/search accepts query, mode (free_text or structured), top_k (1–100), and
optional explain (false). Unknown, duplicate, null and mistyped fields fail.
Bodies are limited to 32 KiB, concurrency to 32 requests, query execution to five
seconds. Header/read/write/idle timeouts are configured.

Responses identify request, snapshot, collection, analyzer, scoring version and
BM25 configuration, total matches, timings and ranked hits. Hits include exact
text, paper identities, title, nullable pages and optional term contributions.
Errors contain code/message and optional character position. Status codes are
400 invalid input, 413 oversized body, 405 method, 503 unavailable/canceled/busy,
404 unknown endpoint and 500 unexpected failure. This local API has no authentication.
