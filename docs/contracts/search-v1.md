# Sparse search v1

BM25 uses collection-wide statistics, unique analyzed query terms in sorted order,
k1=1.2 and b=0.75. Parameters must be finite, k1 positive and b in [0,1].
Candidates in free_text mode are the union of term postings. Results sort by score
descending then external chunk ID ascending. Explanations contain actual scored
term contributions. Queries allow at most 4,096 Unicode characters and top_k 1–100.
