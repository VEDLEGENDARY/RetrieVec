"""Read plain or losslessly compressed measurement reports; never normalize their bytes."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path


def load_report(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rb") as stream:
        return json.load(stream)


def pack_report(path: Path, *, remove_original: bool = False) -> dict:
    if path.suffix != ".json":
        raise ValueError("expected a JSON report")
    raw = path.read_bytes()
    json.loads(raw)
    packed = gzip.compress(raw, compresslevel=9, mtime=0)
    destination = path.with_suffix(".json.gz")
    with destination.open("xb") as stream:
        stream.write(packed)
    if gzip.decompress(destination.read_bytes()) != raw:
        raise ValueError("compressed report differs from its original bytes")
    if remove_original:
        if path.read_bytes() != raw:
            raise ValueError("source changed during compression; both files retained")
        path.unlink()
    return {
        "file": destination.name,
        "uncompressed_sha256": hashlib.sha256(raw).hexdigest(),
        "compressed_sha256": hashlib.sha256(packed).hexdigest(),
        "uncompressed_bytes": len(raw),
        "compressed_bytes": len(packed),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--remove-original", action="store_true")
    args = parser.parse_args()
    print(json.dumps(pack_report(args.report, remove_original=args.remove_original), indent=2))


if __name__ == "__main__":
    main()
