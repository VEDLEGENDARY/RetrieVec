"""Regenerate bindings using the pinned Go plugins and grpcio-tools compiler."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "grpc_tools.protoc", "-I", str(ROOT / "proto"), "--python_out=" + str(ROOT / "python/src"), "--grpc_python_out=" + str(ROOT / "python/src"), "--go_out=" + str(ROOT / "engine"), "--go_opt=module=retrievallab/engine", "--go-grpc_out=" + str(ROOT / "engine"), "--go-grpc_opt=module=retrievallab/engine", str(ROOT / "proto/retrievallab/retrieval/v1/retrieval.proto")], check=True)
