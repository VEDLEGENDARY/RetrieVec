# CPU embedding model

Use sentence-transformers/all-MiniLM-L6-v2 at immutable revision
1110a243fdf4706b3f48f1d95db1a4f5529b4d41. The model has 384 output dimensions,
22.7 million parameters and an Apache-2.0 license. Its documented sentence
embedding procedure is attention-mask mean pooling followed by L2 normalization.
See the [official model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).

The adapter uses the published ONNX graph with CPUExecutionProvider and pinned
tokenizer.json, two intra-op threads, one inter-op thread and batches of at most
16. Query/document prefixes are empty. Model input is bounded to 256 wordpieces,
including special tokens. Oversized input is rejected, never silently truncated;
rebuild the corpus with a smaller explicit chunk budget if needed.

Configuration includes model/revision, artifact checksums, tokenizer, pooling,
dtype, normalization, prefixes, input policy and dependency versions. Cache keys
include that complete configuration plus text hash and document role. Ordinary
offline tests use a clearly labeled deterministic fixture adapter. Real-model
download and smoke evidence run separately; no reviewed quality claim follows
from fixture embeddings or a small unreviewed dataset.
