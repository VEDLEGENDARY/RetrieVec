"""Run an explicitly configured local extraction adapter under process resource limits."""

import argparse
from pathlib import Path

from retrievec.app.process_limits import limit_extraction
from retrievec.extraction.adapters import AdapterConfig, extract_document

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    args = parser.parse_args()
    if args.config.stat().st_size > 65536:
        raise ValueError("adapter configuration exceeds limit")
    limit_extraction()
    config = AdapterConfig.model_validate_json(args.config.read_bytes())
    print(extract_document(args.source, args.store, config))
