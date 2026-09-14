# Analyzer v1

The Go analysis package is authoritative for both indexing and corpus preparation.
It accepts valid UTF-8, separates maximal runs of Unicode letters (L) or decimal
digits (Nd), and applies Go's simple per-codepoint lowercase. It retains stopwords
and performs no stemming, case folding, or normalization. Combining marks separate
tokens; compatibility numerals outside Nd are separators. The version includes
Go's Unicode table version, so a table upgrade changes the analyzer identity.

Tokens have term, zero-based position, and [start,end) UTF-8 byte offsets into the
original text. Offsets are not character indices. Empty input produces [].
Turkish dotted I and Greek final sigma illustrate why Python str.lower() is not
an equivalent preparation analyzer. Shared fixtures cover these cases explicitly.

Run retrievald analyze with one JSON object on stdin: {"texts":["RAG-based"]}.
The response has analyzer_version and one token array per input text. Limits:
256 texts, 1 MiB of UTF-8 per text, 8 MiB total serialized request. Python's
GoAnalyzer invokes this command with a deadline and validates the response.
Set RETRIEVALLAB_ENGINE to the built executable, or place retrievald on PATH.
scripts/check.py builds it and sets the environment for integration tests.
