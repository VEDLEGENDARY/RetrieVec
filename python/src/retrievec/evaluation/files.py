"""Publish evaluation artifacts without truncating an existing result on failure."""

import json
import os
import tempfile
from pathlib import Path


def validate_outputs(outputs: list[Path], inputs: list[Path]) -> None:
    destinations = [path.resolve() for path in outputs]
    if len(set(destinations)) != len(destinations) or set(destinations) & {
        path.resolve() for path in inputs
    }:
        raise ValueError("outputs must be distinct from each other and inputs")


def write_json(path: Path, value: object) -> None:
    # Serialize before touching the destination; reject NaN/Infinity in evidence reports.
    content = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
