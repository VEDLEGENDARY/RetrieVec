"""Explicit, pinned local adapter protocol with bounded subprocess output.

Adapters are operator-installed programs, not a network or security sandbox.
No cloud transport is implemented; private files never go to a remote adapter here.
"""

import hashlib
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Literal

from pydantic import Field

from retrievec.corpus.snapshot import canonical, digest, parse_json
from retrievec.extraction.pages import inspect_pdf
from retrievec.extraction.schema import Evidence, Hash, Strict
from retrievec.extraction.store import EvidenceStore


class AdapterConfig(Strict):
    schema_version: Literal[1] = 1
    executable: str = Field(min_length=1, max_length=4096)
    executable_sha256: Hash
    arguments: list[str] = Field(default_factory=list, max_length=16)
    name: str = Field(min_length=1, max_length=128)
    revision: str = Field(min_length=1, max_length=256)
    processing: Literal["local"] = "local"
    capabilities: list[Literal["prose", "table", "equation", "figure"]] = Field(
        min_length=1, max_length=4
    )
    timeout_seconds: int = Field(default=60, ge=1, le=120)
    max_pages: int = Field(default=20, ge=1, le=100)
    license_reference: str = Field(min_length=1, max_length=4096)
    parameters: dict = Field(default_factory=dict)

    @property
    def identity(self):
        return digest(canonical(self.model_dump(mode="json")))


class AdapterFailure(ValueError):
    pass


def terminate(process):
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                check=False,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except (OSError, subprocess.TimeoutExpired):
            if process.poll() is None:
                process.kill()
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait(timeout=10)


def extract_document(source_path, root, config, *, cancelled=lambda: False):
    executable = Path(config.executable)
    if not executable.is_absolute() or not executable.is_file() or executable.is_symlink():
        raise AdapterFailure("adapter executable must be an absolute regular file")
    with executable.open("rb") as file:
        if hashlib.file_digest(file, "sha256").hexdigest() != config.executable_sha256:
            raise AdapterFailure("adapter executable revision changed")
    source_path = Path(source_path)
    if source_path.stat().st_size > 64 * 1024 * 1024:
        raise AdapterFailure("source file exceeds limit")
    source = source_path.read_bytes()
    pages = inspect_pdf(source, config.max_pages)
    if cancelled():
        raise AdapterFailure("extraction cancelled")
    with tempfile.TemporaryDirectory(prefix="retrievec-extract-") as temporary:
        directory = Path(temporary)
        # Copy only this document into the adapter workspace; never pass the whole store.
        original = directory / "source.pdf"
        original.write_bytes(source)
        request = {
            "schema_version": 1,
            "source": str(original),
            "source_sha256": digest(source),
            "adapter_identity": config.identity,
            "configuration": config.parameters,
            "capabilities": config.capabilities,
            "pages": [
                {
                    "geometry": row["geometry"].model_dump(mode="json"),
                    "classification": row["classification"],
                }
                for row in pages
            ],
        }
        (directory / "request.json").write_bytes(canonical(request))
        output = directory / "output.json"
        environment = {
            key: os.environ[key]
            for key in ("SystemRoot", "WINDIR", "PATH", "TEMP", "TMP")
            if key in os.environ
        }
        command = [
            str(executable),
            *config.arguments,
            "--request",
            str(directory / "request.json"),
            "--output",
            str(output),
        ]
        options = (
            {"creationflags": subprocess.CREATE_NO_WINDOW}
            if os.name == "nt"
            else {"start_new_session": True}
        )
        process = subprocess.Popen(
            command,
            cwd=directory,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **options,
        )
        started = time.monotonic()
        try:
            while process.poll() is None:
                if cancelled() or time.monotonic() - started > config.timeout_seconds:
                    raise AdapterFailure("extraction interrupted or timed out")
                size, count = 0, 0
                for path in directory.rglob("*"):
                    if path.is_symlink() or path.is_junction():
                        raise AdapterFailure("adapter created a linked output")
                    if path.is_file():
                        size += path.stat().st_size
                        count += 1
                    if size > 256 * 1024 * 1024 or count > 1000:
                        raise AdapterFailure("adapter output exceeds budget")
                time.sleep(0.05)
            if process.returncode:
                raise AdapterFailure("adapter execution failed")
            if output.is_symlink() or output.stat().st_size > 8 * 1024 * 1024:
                raise AdapterFailure("adapter response exceeds limit")
            response = parse_json(output.read_bytes())
            if (
                response.get("schema_version") != 1
                or response.get("source_sha256") != digest(source)
                or response.get("adapter_identity") != config.identity
            ):
                raise AdapterFailure("adapter response provenance differs")
            records = response.get("evidence")
            if not isinstance(records, list) or not 1 <= len(records) <= 10000:
                raise AdapterFailure("invalid adapter object count")
            objects, images = [], {}
            for record in records:
                item = Evidence.model_validate(record)
                if (
                    item.review.status != "pending"
                    or item.review.reviewer is not None
                    or item.extractor != config.name
                    or item.revision != config.revision
                    or item.configuration != config.parameters
                    or item.content.kind not in config.capabilities
                    or item.derivation == "manual"
                ):
                    raise AdapterFailure("adapter cannot claim review or change configuration")
                objects.append(item)
                for key in (item.page_render_sha256, item.region_crop_sha256):
                    if key is not None and key not in images:
                        path = directory / (key + ".png")
                        if path.is_symlink() or path.stat().st_size > 32 * 1024 * 1024:
                            raise AdapterFailure("invalid adapter image")
                        images[key] = path.read_bytes()
                        if sum(len(value) for value in images.values()) > 128 * 1024 * 1024:
                            raise AdapterFailure("image collection exceeds limit")
            if cancelled():
                raise AdapterFailure("extraction cancelled before publication")
            return EvidenceStore(root).publish(source, objects, images)
        finally:
            if process.poll() is None:
                terminate(process)
