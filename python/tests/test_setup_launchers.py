"""Exercise setup commands with a fake Docker CLI, without touching user containers."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


@unittest.skipUnless(POWERSHELL, "requires PowerShell")
class PowerShellSetupTests(unittest.TestCase):
    def run_setup(self, action, scenario="ready"):
        with tempfile.TemporaryDirectory(prefix="setup space ") as directory:
            root = Path(directory)
            log = root / "commands.jsonl"
            wrapper = root / "docker-mock.ps1"
            wrapper.write_text(
                """function global:docker {
  $encoded = ConvertTo-Json -Compress -InputObject @($args)
  Add-Content -LiteralPath $env:RETRIEVEC_SETUP_TEST_LOG -Value $encoded
  $global:LASTEXITCODE = 0
  if ($args[0] -eq 'info') {
    if ($env:RETRIEVEC_SETUP_TEST_SCENARIO -eq 'stopped') { $global:LASTEXITCODE = 1; return }
    if ($env:RETRIEVEC_SETUP_TEST_SCENARIO -eq 'windows') { 'windows'; return }
    'linux'
  }
  if ($args -contains 'up' -and $env:RETRIEVEC_SETUP_TEST_SCENARIO -eq 'failed') {
    $global:LASTEXITCODE = 1
  }
}
& $env:RETRIEVEC_SETUP_TEST_SCRIPT -Action $env:RETRIEVEC_SETUP_TEST_ACTION
exit $LASTEXITCODE
""",
                encoding="utf-8",
            )
            result = subprocess.run(
                [POWERSHELL, "-NoProfile", "-File", str(wrapper)],
                cwd=root,
                env=os.environ
                | {
                    "RETRIEVEC_SETUP_TEST_SCRIPT": str(ROOT / "start.ps1"),
                    "RETRIEVEC_SETUP_TEST_LOG": str(log),
                    "RETRIEVEC_SETUP_TEST_ACTION": action,
                    "RETRIEVEC_SETUP_TEST_SCENARIO": scenario,
                },
                capture_output=True,
                text=True,
                timeout=20,
            )
            calls = [json.loads(line) for line in log.read_text(encoding="utf-8-sig").splitlines()]
            return result, calls

    def test_start_waits_for_readiness_and_uses_root_compose(self):
        result, calls = self.run_setup("start")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("http://127.0.0.1:8000", result.stdout)
        self.assertEqual(calls[-1][:2], ["compose", "-f"])
        self.assertEqual(Path(calls[-1][2]).resolve(), ROOT / "compose.yaml")
        self.assertEqual(calls[-1][3:], ["up", "--build", "--wait", "--wait-timeout", "900"])

    def test_failure_never_announces_a_ready_workspace(self):
        for scenario, message in (
            ("stopped", "Docker is not running"),
            ("windows", "Linux containers"),
            ("failed", "Docker Compose failed"),
        ):
            with self.subTest(scenario=scenario):
                result, calls = self.run_setup("start", scenario)
                self.assertEqual(result.returncode, 1)
                self.assertIn(message, result.stdout)
                self.assertNotIn("Open http://", result.stdout)

    def test_doctor_never_starts_and_stop_never_deletes_volumes(self):
        for action in ("doctor", "stop", "status", "logs"):
            with self.subTest(action=action):
                result, calls = self.run_setup(action)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                self.assertFalse(any("up" in call for call in calls))
                self.assertFalse(any("--volumes" in call for call in calls))
                if action == "stop":
                    self.assertEqual(calls[-1][-1], "down")
                    self.assertIn("preserved", result.stdout)


@unittest.skipIf(os.name == "nt", "POSIX launcher runs on Linux/macOS")
class ShellSetupTests(unittest.TestCase):
    def run_setup(self, action, scenario="ready"):
        with tempfile.TemporaryDirectory(prefix="setup space ") as directory:
            root = Path(directory)
            log = root / "commands"
            docker = root / "docker"
            docker.write_text(
                """#!/bin/sh
printf '%s\\n' "$*" >> "$RETRIEVEC_SETUP_TEST_LOG"
if [ "$1" = info ]; then
  case "$RETRIEVEC_SETUP_TEST_SCENARIO" in
    stopped) exit 1 ;; windows) echo windows ;; *) echo linux ;;
  esac
fi
if [ "$RETRIEVEC_SETUP_TEST_SCENARIO" = failed ] && [ "${4:-}" = up ]; then exit 1; fi
"""
            )
            docker.chmod(0o755)
            result = subprocess.run(
                ["sh", str(ROOT / "start.sh"), action],
                cwd=root,
                env=os.environ
                | {
                    "PATH": str(root) + os.pathsep + os.environ["PATH"],
                    "RETRIEVEC_SETUP_TEST_LOG": str(log),
                    "RETRIEVEC_SETUP_TEST_SCENARIO": scenario,
                },
                capture_output=True,
                text=True,
                timeout=20,
            )
            return result, log.read_text().splitlines()

    def test_start_waits_and_reports_service_failures(self):
        result, calls = self.run_setup("start")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(calls[-1], "compose -f compose.yaml up --build --wait --wait-timeout 900")
        for scenario in ("stopped", "windows", "failed"):
            result, calls = self.run_setup("start", scenario)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn("Open http://", result.stdout)

    def test_doctor_and_stop_preserve_data(self):
        for action in ("doctor", "stop", "status", "logs"):
            result, calls = self.run_setup(action)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(any(" up " in call or "--volumes" in call for call in calls))
