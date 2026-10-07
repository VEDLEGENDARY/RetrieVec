"""Optional local ONNX entailment proxy with pinned artifacts and explicit labels."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class NliConfig:
    model_id: str
    revision: str
    model_path: Path
    tokenizer_path: Path
    model_sha256: str
    tokenizer_sha256: str
    label_order: tuple[str, str, str]
    max_tokens: int

    def validate(self) -> None:
        if not self.model_id or len(self.revision) != 40:
            raise ValueError("NLI model requires identity and full revision")
        if set(self.label_order) != {"contradiction", "neutral", "entailment"}:
            raise ValueError("NLI label order must be explicit")
        if not 64 <= self.max_tokens <= 8192:
            raise ValueError("NLI token budget invalid")
        for path, expected in (
            (self.model_path, self.model_sha256),
            (self.tokenizer_path, self.tokenizer_sha256),
        ):
            if len(expected) != 64:
                raise ValueError("NLI artifact SHA-256 required")
            with path.open("rb") as source:
                if hashlib.file_digest(source, "sha256").hexdigest() != expected:
                    raise ValueError("NLI artifact SHA-256 mismatch")


class NliProxy:
    def __init__(self, config: NliConfig):
        config.validate()
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self.config = config
        self.tokenizer = Tokenizer.from_file(str(config.tokenizer_path))
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        self.session = ort.InferenceSession(
            str(config.model_path), providers=["CPUExecutionProvider"]
        )
        self.input_names = {item.name for item in self.session.get_inputs()}
        if not {"input_ids", "attention_mask"} <= self.input_names or not self.input_names <= {
            "input_ids",
            "attention_mask",
            "token_type_ids",
        }:
            raise ValueError("unsupported NLI model inputs")

    def __call__(self, premise: str, hypothesis: str) -> float:
        if not premise.strip() or not hypothesis.strip():
            raise ValueError("NLI requires nonempty premise and hypothesis")
        row = self.tokenizer.encode(premise, hypothesis)
        if len(row.ids) > self.config.max_tokens:
            raise ValueError("NLI pair exceeds token budget")
        inputs = {
            "input_ids": np.asarray([row.ids], dtype=np.int64),
            "attention_mask": np.asarray([row.attention_mask], dtype=np.int64),
            "token_type_ids": np.asarray([row.type_ids], dtype=np.int64),
        }
        logits = np.asarray(
            self.session.run(None, {name: inputs[name] for name in self.input_names})[0],
            dtype=np.float64,
        )
        if logits.shape != (1, 3) or not np.isfinite(logits).all():
            raise ValueError("unexpected NLI logits")
        normalized = logits[0] - logits[0].max()
        probabilities = np.exp(normalized) / np.exp(normalized).sum()
        score = float(probabilities[self.config.label_order.index("entailment")])
        if not math.isfinite(score):
            raise ValueError("nonfinite NLI probability")
        return score
