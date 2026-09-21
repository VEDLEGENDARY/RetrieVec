"""Optional process CPU/RSS sampling without command lines or extra dependencies."""

import ctypes
import os
import sys
import threading
import time
from pathlib import Path


def process_sample(pid):
    if os.name == "nt":
        from ctypes import wintypes

        class Memory(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("faults", wintypes.DWORD),
                ("peak_rss", ctypes.c_size_t),
                ("rss", ctypes.c_size_t),
                ("peak_paged", ctypes.c_size_t),
                ("paged", ctypes.c_size_t),
                ("peak_nonpaged", ctypes.c_size_t),
                ("nonpaged", ctypes.c_size_t),
                ("pagefile", ctypes.c_size_t),
                ("peak_pagefile", ctypes.c_size_t),
            ]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [
            ctypes.POINTER(wintypes.FILETIME)
        ] * 4
        kernel.K32GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(Memory),
            wintypes.DWORD,
        ]
        handle = kernel.OpenProcess(0x1000 | 0x10, False, pid)
        if not handle:
            raise OSError("process unavailable")
        try:
            created, ended, system, user = (wintypes.FILETIME() for _ in range(4))
            memory = Memory()
            memory.cb = ctypes.sizeof(memory)
            if not kernel.GetProcessTimes(
                handle,
                ctypes.byref(created),
                ctypes.byref(ended),
                ctypes.byref(system),
                ctypes.byref(user),
            ):
                raise OSError("CPU sample unavailable")
            if not kernel.K32GetProcessMemoryInfo(handle, ctypes.byref(memory), memory.cb):
                raise OSError("memory sample unavailable")

            def ticks(value):
                return (value.dwHighDateTime << 32) | value.dwLowDateTime

            return {
                "identity": ticks(created),
                "cpu_seconds": (ticks(system) + ticks(user)) / 10_000_000,
                "rss_bytes": memory.rss,
            }
        finally:
            kernel.CloseHandle(handle)
    if sys.platform.startswith("linux"):
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return {
            "identity": int(fields[19]),
            "cpu_seconds": (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK"),
            "rss_bytes": int(fields[21]) * os.sysconf("SC_PAGE_SIZE"),
        }
    raise OSError("process sampling supports Windows and Linux")


class ResourceSampler:
    def __init__(self, pids):
        self.pids = sorted(set(pids))
        if len(self.pids) > 16 or any(
            type(pid) is not int or not 1 <= pid <= 2**32 - 1 for pid in self.pids
        ):
            raise ValueError("supply at most sixteen positive process IDs")
        self.rows = {
            pid: {
                "samples": 0,
                "errors": 0,
                "first": None,
                "last": None,
                "peak_rss_bytes": None,
                "identity_changed": False,
            }
            for pid in self.pids
        }
        self.stop = threading.Event()
        self.thread = None

    def capture(self):
        for pid, row in self.rows.items():
            try:
                sample = process_sample(pid)
                if row["first"] and sample["identity"] != row["first"]["identity"]:
                    row["identity_changed"] = True
                    row["errors"] += 1
                    continue
                row["first"] = row["first"] or sample
                row["last"] = sample
                row["peak_rss_bytes"] = max(row["peak_rss_bytes"] or 0, sample["rss_bytes"])
                row["samples"] += 1
            except (OSError, ValueError, IndexError):
                row["errors"] += 1

    def __enter__(self):
        self.started = time.monotonic()
        self.capture()

        def sample():
            while not self.stop.wait(0.5):
                self.capture()

        self.thread = threading.Thread(target=sample, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.stop.set()
        self.thread.join(timeout=3)
        if self.thread.is_alive():
            raise RuntimeError("resource sampler did not stop")
        self.capture()
        self.elapsed = time.monotonic() - self.started

    def report(self):
        if not self.pids:
            return None
        rows = []
        for pid, row in self.rows.items():
            cpu = (
                max(0, row["last"]["cpu_seconds"] - row["first"]["cpu_seconds"])
                if row["samples"] >= 2 and not row["identity_changed"]
                else None
            )
            rows.append(
                {
                    "pid": pid,
                    "samples": row["samples"],
                    "sample_errors": row["errors"],
                    "identity_changed": row["identity_changed"],
                    "cpu_seconds": cpu,
                    "cpu_percent_one_core": 100 * cpu / self.elapsed if cpu is not None else None,
                    "peak_rss_bytes": row["peak_rss_bytes"],
                }
            )
        return {
            "interval_seconds": 0.5,
            "elapsed_seconds": self.elapsed,
            "processes": rows,
            "scope": "Only explicitly selected PIDs; children excluded unless also selected. "
            "RSS peaks are sampled, CPU percent uses one logical core; warmup included.",
        }
