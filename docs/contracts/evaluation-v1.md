# Evaluation v1

Evaluation IDs hash canonical questions, split membership, corpus identity and
judgments. Review state is part of that identity. Default reports use only reviewed
judgments; --include-drafts explicitly opts into exploratory draft output.
Binary relevance is grade >=2; nDCG gain is 2^grade-1, logarithmic rank discount.
Unknown gains are zero for arithmetic only. Queries without known positives have
null MRR/recall; zero ideal gain gives null nDCG. Empty results have null coverage.
Undefined values are excluded from means with their counts reported. Request
failures and absent queries are separate from valid empty responses.
Saved result hashes and query text/mode/corpus identities are verified before
metrics.json/report.md are written. Replaying the same inputs reproduces metrics.
