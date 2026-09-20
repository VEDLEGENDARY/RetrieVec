"""Build an openly inspectable synthetic draft pool; never assign human review."""

from pathlib import Path

from retrievallab.corpus.snapshot import canonical, digest, load_snapshot

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / (
    "datasets/fixtures/snapshots/ss_4415a7c573a87a239ee65b0581664ea667b3988e4"
    "be43cb7f3bd069380ee0811"
)
QUESTIONS = [
    ("How does BM25 use document length?", "fixture-01"),
    ("How can semantic retrieval bridge vocabulary mismatch?", "fixture-02"),
    ("How are incompatible retrieval score scales combined?", "fixture-03"),
    ("Can a reranker recover passages absent from candidates?", "fixture-04"),
    ("How are oversized paragraphs split?", "fixture-05"),
    ("What does judgment coverage measure?", "fixture-06"),
    ('"red red"', "fixture-07"),
    ("Are stopwords discarded?", "fixture-08"),
    ("Unicode café", "fixture-09"),
    ("What defines the scope of negation?", "fixture-10"),
    ("What identifies source versions reproducibly?", "fixture-11"),
    ("Where do stars form?", "fixture-12"),
    ("lexical retrieval term frequency", "fixture-01"),
    ("embeds queries passages", "fixture-02"),
    ("reciprocal rank fusion", "fixture-03"),
    ("cross encoder candidate evidence", "fixture-04"),
    ("chunk boundaries overlap", "fixture-05"),
    ("recall known relevant results", "fixture-06"),
    ("hashes AND NOT astronomy", "fixture-11"),
    ("quantum superconducting qubits", None),
]


def main() -> None:
    manifest, _, chunks = load_snapshot(CORPUS)
    data = {
        "schema_version": 1,
        "kind": "synthetic-draft",
        "corpus_snapshot_id": manifest["snapshot_id"],
        "queries": [],
        "judgments": [],
    }
    for i, (question, relevant) in enumerate(QUESTIONS):
        query_id = f"q{i + 1:02}"
        data["queries"].append(
            {
                "query_id": query_id,
                "query": question,
                "mode": "structured" if i in (6, 18) else "free_text",
                "split": "development" if i < 12 else "held_out",
            }
        )
        for chunk in chunks:
            data["judgments"].append(
                {
                    "query_id": query_id,
                    "chunk_id": chunk["chunk_id"],
                    "grade": 3 if chunk["paper_id"] == relevant else 0,
                    "review_status": "draft",
                    "reviewer": None,
                    "rationale": (
                        "Synthetic expected-topic proposal; inspect passage before approving."
                    ),
                }
            )
    data["dataset_id"] = "ev_" + digest(canonical(data))
    (ROOT / "datasets/evaluation/synthetic-draft-v1.json").write_bytes(canonical(data) + b"\n")


if __name__ == "__main__":
    main()
