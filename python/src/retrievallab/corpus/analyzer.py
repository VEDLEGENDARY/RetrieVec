"""Use the authoritative Go analyzer for corpus preparation."""

import os
import subprocess
from pathlib import Path

from retrievallab.corpus.snapshot import CorpusError, canonical, parse_json


class GoAnalyzer:
    def __init__(self, executable: str | Path | None = None) -> None:
        self.executable = str(executable or os.environ.get("RETRIEVALLAB_ENGINE", "retrievald"))
        self.version = ""

    def analyze(self, texts: list[str]) -> list[list[dict]]:
        if len(texts) > 256 or any(len(text.encode("utf-8")) > 1024 * 1024 for text in texts):
            raise CorpusError("analyzer input exceeds batch or text limit")
        request = canonical({"texts": texts})
        if len(request) > 8 * 1024 * 1024:
            raise CorpusError("analyzer request exceeds 8 MiB")
        try:
            result = subprocess.run(
                [self.executable, "analyze"],
                input=request,
                capture_output=True,
                timeout=30,
                check=True,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise CorpusError(f"Go analyzer failed: {error}") from error
        response = parse_json(result.stdout)
        if not isinstance(response, dict) or set(response) != {"analyzer_version", "tokens"}:
            raise CorpusError("invalid analyzer response")
        version = response["analyzer_version"]
        if not isinstance(version, str) or not version.startswith("analyzer-v1-unicode-"):
            raise CorpusError("unsupported analyzer version")
        if self.version and version != self.version:
            raise CorpusError("analyzer version changed during preparation")
        batches = response["tokens"]
        if not isinstance(batches, list) or len(batches) != len(texts):
            raise CorpusError("analyzer response count mismatch")
        for text, tokens in zip(texts, batches, strict=True):
            byte_length = len(text.encode("utf-8"))
            if not isinstance(tokens, list):
                raise CorpusError("invalid analyzer token array")
            end = 0
            for position, token in enumerate(tokens):
                if not isinstance(token, dict) or set(token) != {
                    "term",
                    "position",
                    "start",
                    "end",
                }:
                    raise CorpusError("invalid analyzer token")
                if (
                    any(type(token[key]) is not int for key in ("position", "start", "end"))
                    or token["position"] != position
                    or not isinstance(token["term"], str)
                    or not token["term"]
                    or not end <= token["start"] < token["end"] <= byte_length
                ):
                    raise CorpusError("invalid analyzer token position")
                end = token["end"]
        self.version = version
        return batches
