# Evaluation labeling

The initial 20-question pool is synthetic and entirely draft. Its 12 development
and eight held-out IDs are frozen in the content-hashed dataset. It tests plumbing,
not real-paper retrieval quality. Do not tune on held-out outputs.

Read each question and the exact pinned passage. Grade 0 irrelevant, 1 related
background, 2 useful evidence, 3 particularly complete evidence. Record a concrete
rationale, your reviewer identity and review_status=reviewed only after inspection.
An unjudged passage has no row; it is distinct from a reviewed grade zero.
Recompute dataset_id over canonical content excluding dataset_id when editing.
Keep prior dataset versions and record split changes; reused held-out questions
become development data and must be replaced for new held-out conclusions.

For real papers, pool BM25, lexical baseline, dense/hybrid candidates and manual
discoveries before labeling. Reports must show reviewed coverage and excluded drafts.
The five-paper source manifest remains the initial real-paper seed; corpus expansion
and human judgments are separate evidence requirements.
