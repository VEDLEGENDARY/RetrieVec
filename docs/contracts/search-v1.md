# Sparse search v1

BM25 uses collection-wide statistics, unique analyzed query terms in sorted order,
k1=1.2 and b=0.75. Parameters must be finite, k1 positive and b in [0,1].
Candidates in free_text mode are the union of term postings. Results sort by score
descending then external chunk ID ascending. Explanations contain actual scored
term contributions. Queries allow at most 4,096 Unicode characters and top_k 1–100.

Structured queries require explicit uppercase operators, with NOT > AND > OR.
Parentheses and phrases support at most 32 nested levels, 256 lexer tokens and
256 analyzed tokens per phrase. Only quote and backslash escapes are accepted
inside phrases. Bare operands must analyze to one token. Error positions are
zero-based Unicode character offsets. At least one term must be below an even
number of NOT nodes; those unique terms supply ranking weight.

Boolean evaluation uses set union, intersection and complement relative to the
loaded collection. Phrase matches require consecutive positions in one chunk,
including repeated terms. Surviving zero-score documents remain results. Search
checks cancellation while traversing the expression and candidate documents.
