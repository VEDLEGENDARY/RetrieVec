"""Bounded, resumable pairwise reranker training with atomic checkpoints."""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from retrievec.corpus.snapshot import canonical, digest


@dataclass(frozen=True)
class TrainingConfig:
    dataset_id: str
    mining_id: str
    feature_version: str
    dimension: int
    learning_rate: float = 0.01
    l2: float = 0.0001
    max_steps: int = 1000
    max_epochs: int = 3
    checkpoint_every: int = 100
    seed: int = 1729
    max_seconds: int = 3600

    def validate(self) -> None:
        if not self.dataset_id.startswith("td_") or not self.mining_id.startswith("hn_"):
            raise ValueError("training inputs need content identities")
        if not self.feature_version or not 1 <= self.dimension <= 8192:
            raise ValueError("invalid feature contract")
        if not 0 < self.learning_rate <= 1 or not 0 <= self.l2 <= 1:
            raise ValueError("invalid optimizer configuration")
        if not 1 <= self.max_steps <= 1000 or not 1 <= self.max_epochs <= 3:
            raise ValueError("training exceeds bounded budget")
        if not 1 <= self.checkpoint_every <= self.max_steps or not 1 <= self.max_seconds <= 3600:
            raise ValueError("invalid checkpoint or time budget")

    @property
    def config_id(self) -> str:
        self.validate()
        return "tc_" + digest(canonical(asdict(self)))


def _atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = path.with_name("." + path.name + ".tmp")
    with stage.open("wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    os.replace(stage, path)


def _save_checkpoint(
    directory: Path, config: TrainingConfig, weights: np.ndarray, state: dict
) -> str:
    payload = weights.astype("<f4").tobytes()
    manifest = dict(state, schema_version=1, config=asdict(config), config_id=config.config_id)
    manifest["weights_sha256"] = digest(payload)
    manifest["checkpoint_id"] = "ck_" + digest(canonical(manifest))
    target = directory / manifest["checkpoint_id"]
    _atomic(target / "weights.f32", payload)
    _atomic(target / "manifest.json", canonical(manifest) + b"\n")
    _atomic(
        directory / "latest.json", canonical({"checkpoint_id": manifest["checkpoint_id"]}) + b"\n"
    )
    return manifest["checkpoint_id"]


def load_checkpoint(directory: Path, config: TrainingConfig) -> tuple[np.ndarray, dict] | None:
    pointer = directory / "latest.json"
    if not pointer.exists():
        return None
    checkpoint_id = json.loads(pointer.read_text(encoding="utf-8"))["checkpoint_id"]
    target = directory / checkpoint_id
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    raw = (target / "weights.f32").read_bytes()
    if manifest["config_id"] != config.config_id or manifest["weights_sha256"] != digest(raw):
        raise ValueError("checkpoint identity mismatch")
    weights = np.frombuffer(raw, dtype="<f4").copy()
    if weights.shape != (config.dimension,) or not np.isfinite(weights).all():
        raise ValueError("invalid checkpoint weights")
    return weights, manifest


def train_pairwise(
    pairs: np.ndarray,
    config: TrainingConfig,
    checkpoint_directory: Path,
    *,
    resume: bool = True,
) -> dict:
    """Train on positive-minus-negative feature rows using logistic pairwise loss."""
    config.validate()
    values = np.asarray(pairs, dtype=np.float32)
    if values.ndim != 2 or values.shape[1] != config.dimension or not len(values):
        raise ValueError("training pairs have wrong shape")
    if not np.isfinite(values).all():
        raise ValueError("training features must be finite")
    loaded = load_checkpoint(checkpoint_directory, config) if resume else None
    weights = loaded[0] if loaded else np.zeros(config.dimension, dtype=np.float32)
    step = int(loaded[1]["step"]) if loaded else 0
    epoch = int(loaded[1]["epoch"]) if loaded else 0
    rng = random.Random(config.seed)
    started = time.monotonic()
    checkpoints = []
    while epoch < config.max_epochs and step < config.max_steps:
        order = list(range(len(values)))
        rng.seed(config.seed + epoch)
        rng.shuffle(order)
        for index in order:
            if step >= config.max_steps or time.monotonic() - started >= config.max_seconds:
                break
            row = values[index]
            margin = float(np.dot(weights.astype(np.float64), row.astype(np.float64)))
            probability = 1.0 / (1.0 + np.exp(np.clip(margin, -30, 30)))
            gradient = -probability * row + config.l2 * weights
            weights -= config.learning_rate * gradient.astype(np.float32)
            step += 1
            if step % config.checkpoint_every == 0:
                checkpoints.append(
                    _save_checkpoint(
                        checkpoint_directory, config, weights, {"step": step, "epoch": epoch}
                    )
                )
        epoch += 1
    final = _save_checkpoint(checkpoint_directory, config, weights, {"step": step, "epoch": epoch})
    return {
        "schema_version": 1,
        "config_id": config.config_id,
        "final_checkpoint_id": final,
        "checkpoints": checkpoints,
        "steps": step,
        "epochs": epoch,
        "stopped_by_time": time.monotonic() - started >= config.max_seconds,
    }
