"""Pinned local ONNX cross encoder for frozen BEIR pools; rejects truncation."""

import hashlib
from importlib.metadata import version

import numpy as np


class CrossEncoder:
    def __init__(self, config):
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download
        from tokenizers import Tokenizer

        if config.get("enabled_by_default") is not False or config["truncation"] != "reject":
            raise ValueError("cross encoder must be explicit and reject truncation")
        for field in ("revision", "tokenizer_revision"):
            if len(config[field]) != 40 or any(c not in "0123456789abcdef" for c in config[field]):
                raise ValueError("cross encoder revisions must be commit hashes")
        tokenizer_path = hf_hub_download(
            config["model"], "tokenizer.json", revision=config["tokenizer_revision"]
        )
        model_path = hf_hub_download(
            config["model"], config["artifact"], revision=config["revision"]
        )
        self.tokenizer = Tokenizer.from_file(tokenizer_path)
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        options = ort.SessionOptions()
        options.intra_op_num_threads, options.inter_op_num_threads = 2, 1
        self.session = ort.InferenceSession(
            model_path, sess_options=options, providers=["CPUExecutionProvider"]
        )

        def sha(path):
            with open(path, "rb") as source:
                return hashlib.file_digest(source, "sha256").hexdigest()

        self.config = dict(
            config,
            model_sha256=sha(model_path),
            tokenizer_sha256=sha(tokenizer_path),
            provider="CPUExecutionProvider",
            software={
                name: version(name)
                for name in ("onnxruntime", "tokenizers", "numpy", "huggingface-hub")
            },
        )

    def score(self, query, candidates):
        pairs = [(query, row["title"] + "\n\n" + row["text"]) for row in candidates]
        encoded = self.tokenizer.encode_batch(pairs)
        lengths = [len(row.ids) for row in encoded]
        if any(length > self.config["max_tokens"] for length in lengths):
            raise ValueError("cross encoder input exceeds pinned limit; no candidate truncated")
        output = []
        size = self.config["batch_size"]
        for start in range(0, len(encoded), size):
            batch = encoded[start : start + size]
            width = max(len(row.ids) for row in batch)
            ids = np.zeros((len(batch), width), dtype=np.int64)
            mask, types = np.zeros_like(ids), np.zeros_like(ids)
            for index, row in enumerate(batch):
                (
                    ids[index, : len(row.ids)],
                    mask[index, : len(row.ids)],
                    types[index, : len(row.ids)],
                ) = row.ids, row.attention_mask, row.type_ids
            inputs = {"input_ids": ids, "attention_mask": mask, "token_type_ids": types}
            logits = self.session.run(
                None, {item.name: inputs[item.name] for item in self.session.get_inputs()}
            )[0]
            if logits.shape != (len(batch), 1) or not np.isfinite(logits).all():
                raise ValueError("invalid cross encoder logits")
            output.extend(float(row[0]) for row in logits)
        return output, {
            "maximum_pair_wordpieces": max(lengths, default=0),
            "truncated_candidates": 0,
            "pairs": len(pairs),
        }
