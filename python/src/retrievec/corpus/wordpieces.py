"""Opt-in lossless refinement at authoritative analyzer token boundaries."""

from retrievec.corpus.snapshot import CorpusError, canonical, digest


class WordpieceBudget:
    def __init__(self, model, analyzer):
        analyzer.analyze([])
        self.tokenizer, self.analyzer = model.tokenizer, analyzer
        self.limit = model.config["max_tokens"]
        self.prefix = model.config["document_prefix"]
        self.configuration = {
            "algorithm": "analyzer-boundary-wordpiece-v1",
            "tokenizer_sha256": model.config["tokenizer_sha256"],
            "model_revision": model.config["revision"],
            "max_tokens": self.limit,
            "document_prefix": self.prefix,
            "analyzer_version": analyzer.version,
        }
        self.version = "wordpiece-v1-" + digest(canonical(self.configuration))

    def fits(self, text):
        return len(self.tokenizer.encode(self.prefix + text).ids) <= self.limit

    def split(self, text):
        if self.fits(text):
            return [text]
        raw = text.encode("utf-8")
        tokens = self.analyzer.analyze([text])[0]
        boundaries = [token["start"] for token in tokens[1:]] + [len(raw)]
        chunks, start = [], 0
        while start < len(raw):
            # Verify every candidate, without assuming token counts are monotonic.
            end = next(
                (
                    end
                    for end in reversed(boundaries)
                    if end > start and self.fits(raw[start:end].decode("utf-8"))
                ),
                None,
            )
            if end is None:
                raise CorpusError(
                    "wordpiece budget cannot preserve an indexable span; "
                    "input needs a different explicit extraction policy"
                )
            chunks.append(raw[start:end].decode("utf-8"))
            start = end
        return chunks
