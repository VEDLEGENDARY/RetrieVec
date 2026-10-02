"""Run the same workspace checks on Windows, Linux, and in CI."""

import argparse
import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*command: str, cwd: Path = ROOT) -> None:
    print(f"> {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--race", action="store_true", help="enable Go race checks (requires C compiler)"
    )
    args = parser.parse_args()
    run(sys.executable, "scripts/check_design_tokens.py")

    # Make the installed console entry point available without shell activation.
    os.environ["PATH"] = sysconfig.get_path("scripts") + os.pathsep + os.environ.get("PATH", "")
    for tool in ("go", "gofmt"):
        if shutil.which(tool) is None:
            print(f"Missing {tool}; install Go and add its bin directory to PATH.", file=sys.stderr)
            return 1

    engine = ROOT / "engine"
    go_files = sorted(str(path.relative_to(engine)) for path in engine.rglob("*.go"))
    formatting = subprocess.run(
        ["gofmt", "-l", *go_files], cwd=engine, capture_output=True, text=True, check=True
    )
    if formatting.stdout.strip():
        print("Run gofmt -w on these files:\n" + formatting.stdout, file=sys.stderr)
        return 1

    run("go", "vet", "./...", cwd=engine)
    run("go", "test", *(["-race"] if args.race else []), "-count=1", "./...", cwd=engine)
    output = ROOT / "artifacts" / "bin"
    output.mkdir(parents=True, exist_ok=True)
    binary = output / ("retrievald.exe" if os.name == "nt" else "retrievald")
    run("go", "build", "-o", str(binary), "./cmd/retrievald", cwd=engine)
    run(str(binary), "--version")
    os.environ["RETRIEVEC_ENGINE"] = str(binary)
    run(sys.executable, "-m", "pip", "check")
    run(
        sys.executable,
        "-m",
        "ruff",
        "check",
        "--config",
        "python/pyproject.toml",
        "python",
        "scripts",
    )
    run(
        sys.executable,
        "-m",
        "ruff",
        "format",
        "--check",
        "--config",
        "python/pyproject.toml",
        "python",
        "scripts",
    )
    run(sys.executable, "-m", "unittest", "discover", "-s", "python/tests", "-v")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        print(f"Check failed (exit {error.returncode}): {error.cmd}", file=sys.stderr)
        raise SystemExit(1) from error
