"""Exercise installed entry points from outside the source tree."""

import importlib.metadata
import shutil
import subprocess
import sys
import tempfile
import unittest

from retrievallab import __version__


class EntryPointTests(unittest.TestCase):
    def run_cli(self, *args: str, console: bool = False) -> subprocess.CompletedProcess[str]:
        if console:
            executable = shutil.which("retrievallab")
            self.assertIsNotNone(executable, "Install the package and add the venv to PATH")
            command = [str(executable)]
        else:
            command = [sys.executable, "-m", "retrievallab"]
        with tempfile.TemporaryDirectory() as directory:
            return subprocess.run(
                [*command, *args],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )

    def test_installed_version(self) -> None:
        self.assertEqual(importlib.metadata.version("retrievallab"), __version__)
        for console in (False, True):
            with self.subTest(console=console):
                result = self.run_cli("--version", console=console)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), f"retrievallab {__version__}")

    def test_help(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: retrievallab", result.stdout)

    def test_default_displays_help(self) -> None:
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("usage: retrievallab", result.stdout)

    def test_invalid_argument_fails(self) -> None:
        result = self.run_cli("--unknown")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("unrecognized arguments", result.stderr)


if __name__ == "__main__":
    unittest.main()
