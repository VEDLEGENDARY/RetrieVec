"""Fetch checksum-pinned public PDFs for the optional extraction evaluation."""

import argparse
import hashlib
import os
import re
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from retrievec.corpus.snapshot import parse_json

MAX_SOURCE_BYTES = 64 * 1024 * 1024
ID = re.compile(r"^[0-9]{4}\.[a-z0-9-]+\.[0-9]+$")


def fetch(manifest_path: Path, destination: Path) -> list[str]:
    manifest = parse_json(manifest_path.read_bytes())
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("sources"), list):
        raise ValueError("invalid PDF evaluation manifest")
    destination.mkdir(parents=True, exist_ok=True)
    acquired = []
    for source in manifest["sources"]:
        paper_id = source["paper_id"]
        if (
            not ID.fullmatch(paper_id)
            or source["path"] != paper_id + ".pdf"
            or source["source_url"] != f"https://aclanthology.org/{paper_id}/"
            or not re.fullmatch(r"[0-9a-f]{64}", source["source_sha256"])
        ):
            raise ValueError("PDF source must be a pinned ACL Anthology paper")
        target = destination / source["path"]
        if target.exists():
            if target.stat().st_size > MAX_SOURCE_BYTES:
                raise ValueError(f"existing PDF exceeds size limit: {paper_id}")
            with target.open("rb") as existing:
                checksum = hashlib.file_digest(existing, "sha256").hexdigest()
            if checksum != source["source_sha256"]:
                raise ValueError(f"existing PDF checksum differs: {paper_id}")
            continue
        url = f"https://aclanthology.org/{paper_id}.pdf"
        temporary = None
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                if urlparse(response.url).hostname != "aclanthology.org":
                    raise ValueError("PDF download redirected outside ACL Anthology")
                with tempfile.NamedTemporaryFile(dir=destination, delete=False) as output:
                    temporary = Path(output.name)
                    checksum = hashlib.sha256()
                    size = 0
                    first = True
                    while block := response.read(1024 * 1024):
                        if first and not block.startswith(b"%PDF-"):
                            raise ValueError("download is not a PDF")
                        first = False
                        size += len(block)
                        if size > MAX_SOURCE_BYTES:
                            raise ValueError("PDF source exceeds 64 MiB")
                        checksum.update(block)
                        output.write(block)
            if checksum.hexdigest() != source["source_sha256"]:
                raise ValueError(f"download checksum differs: {paper_id}")
            os.replace(temporary, target)
            acquired.append(paper_id)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return acquired


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("datasets/manifests/pdf-evaluation-v1.json"),
    )
    parser.add_argument("--output", type=Path, default=Path("artifacts/papers"))
    args = parser.parse_args()
    for paper_id in fetch(args.manifest, args.output):
        print(paper_id)


if __name__ == "__main__":
    main()
