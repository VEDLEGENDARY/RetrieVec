# Hybrid retrieval v1

Python resolves one ready retrieval snapshot and pins it across Go RPC, vectors
and original passage lookup. Registry ownership is checked for every request.
Query model configuration must exactly match the embedding manifest.
Sparse/dense/hybrid are explicit modes. Structured grammar is sparse-only;
dense/hybrid structured requests fail. Missing or failed branches fail the query.
There is no silent fallback or fusion of different snapshots.

RRF deduplicates each input before assigning one-based ranks, adds 1/(60+rank)
across every list, then sorts globally by total descending and chunk ID ascending.
Default candidate limits are 100 per branch and 10 final hits. BM25, cosine and
RRF values are returned separately. Hybrid total_matches is the unique candidate
pool size, not an exhaustive relevance estimate. Cosine may be negative.
Float32 cosine comparisons use 1e-6 numeric fixture tolerance; exact ties use IDs.
