"""Container role dispatcher and fail-fast supervision of the local workspace."""

import argparse
import os
import signal
import subprocess
import sys
import time


def commands():
    return {
        "api": [sys.executable, "-m", "retrievec.app.main"],
        "ingestion": [sys.executable, "-m", "retrievec.app.worker"],
        "research": [sys.executable, "-m", "retrievec.app.research_worker"],
        "migrate": [sys.executable, "-m", "retrievec.registry.cli", "migrate"],
        "rpc": [
            os.getenv("RETRIEVEC_ENGINE", "retrievald"),
            "rpc",
            "--store",
            os.getenv("RETRIEVEC_STORE", "artifacts/store"),
            "--listen",
            os.getenv("RETRIEVEC_RPC_LISTEN", "127.0.0.1:8092"),
        ],
    }


def supervise(roles, *, grace_seconds=35):
    """Stop the whole unit when any child exits, including an unexpected zero exit."""
    stopping = False
    children = []

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        for command in roles:
            if stopping:
                return 0
            children.append(subprocess.Popen(command))
        while not stopping:
            if any(child.poll() is not None for child in children):
                print("workspace child exited; stopping remaining roles", file=sys.stderr)
                return 1
            time.sleep(0.2)
        return 0
    finally:
        for child in reversed(children):
            if child.poll() is None:
                child.terminate()
        deadline = time.monotonic() + grace_seconds
        for child in children:
            try:
                child.wait(timeout=max(0, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "role", choices=("workspace", "api", "rpc", "ingestion", "research", "migrate")
    )
    args = parser.parse_args()
    roles = commands()
    if args.role != "workspace":
        os.execvp(roles[args.role][0], roles[args.role])
    subprocess.run(roles["migrate"], check=True)
    return supervise([roles[name] for name in ("rpc", "ingestion", "research", "api")])


if __name__ == "__main__":
    raise SystemExit(main())
