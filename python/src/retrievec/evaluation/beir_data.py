"""BEIR inputs through the production importer; no test judgments used for preparation."""

import csv
import hashlib
import json
import time
import urllib.request
import zipfile

from retrievec.corpus.analyzer import GoAnalyzer
from retrievec.corpus.importer import import_manifest
from retrievec.corpus.snapshot import canonical, digest, load_snapshot
from retrievec.dense.artifacts import build_embeddings
from retrievec.registry.artifacts import Store

BASE = "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/"


def download(name, root, expected_md5):
    root.mkdir(parents=True, exist_ok=True)
    archive = root / f"{name}.zip"
    if not archive.exists():
        temporary = archive.with_suffix(".download")
        with (
            urllib.request.urlopen(BASE + name + ".zip", timeout=60) as response,
            temporary.open("wb") as output,
        ):
            total = 0
            while block := response.read(1 << 20):
                total += len(block)
                if total > 512 << 20:
                    raise ValueError("dataset archive exceeds bound")
                output.write(block)
        temporary.replace(archive)
    with archive.open("rb") as source:
        if hashlib.file_digest(source, "md5").hexdigest() != expected_md5:
            raise ValueError("BEIR published archive checksum mismatch")
    with zipfile.ZipFile(archive) as bundle:
        for name_in_zip in bundle.namelist():
            target = (root / name_in_zip).resolve()
            if not target.is_relative_to(root.resolve()):
                raise ValueError("archive traversal")
        if sum(item.file_size for item in bundle.infolist()) > 1 << 30:
            raise ValueError("expanded dataset exceeds bound")
        bundle.extractall(root)
    return root / name


def rows(path):
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def qrels(path):
    result = {}
    with path.open(encoding="utf-8") as source:
        for row in csv.DictReader(source, delimiter="\t"):
            qid, did, score = row["query-id"], row["corpus-id"], int(row["score"])
            if score not in (0, 1):
                raise ValueError("expected binary SciFact/SCIDOCS judgments")
            if did in result.setdefault(qid, {}):
                raise ValueError("duplicate judgment")
            result[qid][did] = score
    return result


def order(ids, seed):
    return sorted(ids, key=lambda key: (digest(f"{seed}:{key}".encode()), key))


class BatchedAnalyzer(GoAnalyzer):
    """Amortize subprocess startup; returned tokens are unmodified Go responses."""

    def __init__(self, engine, texts):
        super().__init__(engine)
        self.texts, self.offset, self.cache = texts, 0, {}

    def analyze(self, texts):
        if not texts:
            return super().analyze(texts)
        for text in texts:
            while text not in self.cache and self.offset < len(self.texts):
                batch = self.texts[self.offset : self.offset + 64]
                self.cache = dict(zip(batch, super().analyze(batch), strict=True))
                self.offset += len(batch)
            if text not in self.cache:
                return super().analyze(texts)
        return [self.cache[text] for text in texts]


def prepare(name, data, work, engine, model, protocol, document_limit=0):
    started = time.perf_counter()
    documents = rows(data / "corpus.jsonl")
    if len({row["_id"] for row in documents}) != len(documents):
        raise ValueError("duplicate corpus ID")
    if document_limit:
        chosen = set(order([row["_id"] for row in documents], protocol["seed"])[:document_limit])
        documents = [row for row in documents if row["_id"] in chosen]
    work.mkdir(parents=True, exist_ok=True)
    sources = work / "sources"
    sources.mkdir(exist_ok=True)
    records, texts = [], []
    for row in sorted(documents, key=lambda item: item["_id"]):
        text = str(row.get("title", "")) + "\n\n" + str(row.get("text", ""))
        texts.append(text)
        raw = text.encode()
        filename = digest(row["_id"].encode()) + ".txt"
        (sources / filename).write_bytes(raw)
        records.append(
            {
                "paper_id": row["_id"],
                "title": row.get("title") or row["_id"],
                "authors": [],
                "path": filename,
                "source_url": None,
                "source_sha256": digest(raw),
                "license_note": (
                    f"BEIR {name}; original dataset terms apply; benchmark input, not redistributed"
                ),
            }
        )
    manifest = work / "sources.json"
    manifest.write_bytes(canonical({"schema_version": 1, "sources": records}))
    corpus = import_manifest(
        manifest,
        sources,
        work / "store/corpora",
        name,
        protocol["chunk_token_budget"],
        BatchedAnalyzer(engine, texts),
    )
    import_ms = (time.perf_counter() - started) * 1000
    print(f"{name}: imported {len(records)} papers", flush=True)
    started = time.perf_counter()
    store = Store(work / "store")
    embedding = build_embeddings(store, corpus, model)
    embedding_ms = (time.perf_counter() - started) * 1000
    started = time.perf_counter()
    retrieval = store.build(engine, corpus, embedding)
    index_ms = (time.perf_counter() - started) * 1000
    _, _, chunks = load_snapshot(corpus)
    result = {
        "corpus": str(corpus.resolve()),
        "embedding_id": embedding,
        "snapshot_id": retrieval,
        "papers": len(records),
        "chunks": len(chunks),
        "import_ms": import_ms,
        "embedding_ms": embedding_ms,
        "sparse_build_ms": index_ms,
        "protocol_sha256": digest(canonical(protocol)),
        "model": model.config,
        "inputs": {
            file: digest((data / file).read_bytes()) for file in ("corpus.jsonl", "queries.jsonl")
        },
        "subset": bool(document_limit),
        "document_limit": document_limit,
    }
    (work / "prepared.json").write_bytes(canonical(result) + b"\n")
    return result
