from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from evaluation.research_inputs import hash_files


class ResearchInputHashTests(unittest.TestCase):
    def test_hash_is_stable_across_input_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.txt").write_text("alpha", encoding="utf-8")
            (root / "b.txt").write_text("beta", encoding="utf-8")

            first = hash_files(root, ["a.txt", "b.txt"])
            second = hash_files(root, ["b.txt", "a.txt"])

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("sha256:"))

    def test_hash_changes_when_research_input_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "prompt.py"
            target.write_text("version = 1", encoding="utf-8")
            before = hash_files(root, ["prompt.py"])
            target.write_text("version = 2", encoding="utf-8")
            after = hash_files(root, ["prompt.py"])

        self.assertNotEqual(before, after)

    def test_hash_normalizes_platform_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "prompt.py"
            target.write_bytes(b"first\r\nsecond\r\n")
            windows_hash = hash_files(root, ["prompt.py"])
            target.write_bytes(b"first\nsecond\n")
            unix_hash = hash_files(root, ["prompt.py"])

        self.assertEqual(windows_hash, unix_hash)
