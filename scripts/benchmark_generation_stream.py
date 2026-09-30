"""Compare completion transports on synthetic public evidence; no quality acceptance."""

import argparse
import asyncio
import hashlib
import json
import os
import platform
import time
from pathlib import Path

from retrievec.app.answers import answer_schema, validate_answer
from retrievec.app.generation import LlamaProvider, ProviderConfig, pack_evidence


async def benchmark(args):
    if args.key_file:
        os.environ["RETRIEVEC_BENCHMARK_KEY"] = args.key_file.read_text().strip()
    with args.model.open("rb") as source:
        revision = hashlib.file_digest(source, "sha256").hexdigest()
    provider = LlamaProvider(
        ProviderConfig(
            "local",
            args.endpoint,
            args.model.name,
            revision,
            context_tokens=4096,
            output_tokens=512,
            api_key_env="RETRIEVEC_BENCHMARK_KEY",
        )
    )
    packet = await pack_evidence(
        provider,
        "What does sparse retrieval use?",
        [
            {
                "chunk_id": "synthetic-passage",
                "title": "Synthetic retrieval note",
                "text": "Sparse retrieval uses lexical term matching.",
            }
        ],
    )
    schema = answer_schema(packet["evidence"])
    results = []
    for index in range(args.runs):
        streaming = index % 2 == 1
        started = time.perf_counter()
        first = None
        if streaming:
            parts = []
            async for part in provider.generate_stream(packet["prompt"], schema):
                if first is None:
                    first = (time.perf_counter() - started) * 1000
                parts.append(part)
            raw = "".join(parts)
        else:
            raw = await provider.generate(packet["prompt"], schema)
        elapsed = (time.perf_counter() - started) * 1000
        try:
            validate_answer(raw, packet["evidence"])
            structurally_valid = True
        except ValueError:
            structurally_valid = False
        results.append(
            {
                "streaming": streaming,
                "first_content_ms": first,
                "total_ms": elapsed,
                "structurally_valid": structurally_valid,
                "output_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            }
        )
        print(json.dumps(results[-1]), flush=True)
    args.output.write_text(
        json.dumps(
            {
                "kind": "synthetic-evidence-real-local-model",
                "provider": provider.config.public(),
                "platform": platform.platform(),
                "runs": results,
                "human_quality_acceptance": None,
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8098")
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--runs", type=int, choices=range(2, 31), default=4)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(benchmark(parser.parse_args()))
