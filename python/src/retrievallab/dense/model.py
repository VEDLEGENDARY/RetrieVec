"""Explicit CPU embedding adapters; fixture vectors never establish model quality."""

import hashlib
from importlib.metadata import version

import numpy as np

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"


def normalize(vectors: np.ndarray) -> np.ndarray:
    values = np.asarray(vectors, dtype=np.float32)
    if values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("vectors require finite float32 matrix")
    norms = np.linalg.norm(values.astype(np.float64), axis=1)
    if np.any(norms <= 0) or not np.isfinite(norms).all():
        raise ValueError("zero or invalid vector norm")
    return np.asarray(values / norms[:, None], dtype="<f4")


class FixtureModel:
    config = {"model": "fixture-hashed-words", "revision": "1", "dimension": 32, "dtype": "float32", "normalization": "l2", "pooling": "word-bucket-sum", "query_prefix": "", "document_prefix": "", "max_tokens": 4096, "truncation": "reject-v1", "software": {"numpy": version("numpy")}, "quality_evidence": False}

    def encode(self, texts: list[str]) -> np.ndarray:
        output = np.zeros((len(texts), 32), dtype=np.float32)
        for row, text in enumerate(texts):
            words = text.lower().split()
            if not words or len(words) > 4096:
                raise ValueError("fixture model input length")
            for word in words:
                output[row, int.from_bytes(hashlib.sha256(word.encode()).digest()[:4], "little") % 32] += 1
        return normalize(output)


class MiniLM:
    def __init__(self):
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer
        tokenizer_path = hf_hub_download(MODEL, "tokenizer.json", revision=REVISION)
        model_path = hf_hub_download(MODEL, "onnx/model.onnx", revision=REVISION)
        self.tokenizer = Tokenizer.from_file(tokenizer_path)
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.session = ort.InferenceSession(model_path, sess_options=options, providers=["CPUExecutionProvider"])
        def file_hash(path):
            with open(path, "rb") as file:
                return hashlib.file_digest(file, "sha256").hexdigest()
        self.config = {"model": MODEL, "revision": REVISION, "dimension": 384, "dtype": "float32", "normalization": "l2", "pooling": "attention-mask-mean-v1", "query_prefix": "", "document_prefix": "", "max_tokens": 256, "truncation": "reject-v1", "model_sha256": file_hash(model_path), "tokenizer_sha256": file_hash(tokenizer_path), "provider": "CPUExecutionProvider", "software": {name: version(name) for name in ("onnxruntime", "tokenizers", "numpy", "huggingface-hub")}, "quality_evidence": True}

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts or len(texts) > 16 or any(not text.strip() for text in texts):
            raise ValueError("embedding batch requires 1–16 nonempty texts")
        encoded = self.tokenizer.encode_batch(texts)
        if any(len(item.ids) > 256 for item in encoded):
            raise ValueError("model input exceeds 256 wordpieces; rebuild with a smaller explicit chunk budget")
        width = max(len(item.ids) for item in encoded)
        ids = np.zeros((len(texts), width), dtype=np.int64)
        mask = np.zeros_like(ids)
        types = np.zeros_like(ids)
        for row, item in enumerate(encoded):
            ids[row, :len(item.ids)] = item.ids
            mask[row, :len(item.ids)] = item.attention_mask
            types[row, :len(item.ids)] = item.type_ids
        inputs = {"input_ids": ids, "attention_mask": mask, "token_type_ids": types}
        result = self.session.run(None, {item.name: inputs[item.name] for item in self.session.get_inputs()})[0]
        if result.shape != (len(texts), width, 384):
            raise ValueError("unexpected model output shape")
        pooled = (result * mask[:, :, None]).sum(axis=1) / mask.sum(axis=1)[:, None]
        return normalize(pooled)


def adapter(name: str):
    if name == "fixture":
        return FixtureModel()
    if name == "minilm":
        return MiniLM()
    raise ValueError("unknown embedding adapter")
