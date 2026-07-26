"""Stable provenance hash for inputs that can change pipeline-selection results."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Iterable


RESEARCH_INPUT_SCOPES = (
    "ai/app",
    "ai/evaluation/golden_eval_common.py",
    "ai/evaluation/canonical_research_data.py",
    "ai/evaluation/datasets/canonical_research_manifest.v1.json",
    "ai/evaluation/pipeline_selection.py",
    "ai/evaluation/run_pipeline_profile_eval.py",
    "ai/knowledge-base",
    "ai/requirements.txt",
    "backend/data/menu-dataset.json",
)


def _canonical_content(content: bytes) -> bytes:
    return content.replace(b"\r\n", b"\n")


def hash_files(repository_root: Path, relative_paths: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for relative_path in sorted(set(relative_paths)):
        normalized = relative_path.replace("\\", "/")
        digest.update(normalized.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_canonical_content((repository_root / normalized).read_bytes()))
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def _tracked_files(repository_root: Path, revision: str | None) -> list[str]:
    if revision:
        command = [
            "git",
            "ls-tree",
            "-r",
            "--name-only",
            "-z",
            revision,
            "--",
            *RESEARCH_INPUT_SCOPES,
        ]
    else:
        command = ["git", "ls-files", "-z", "--", *RESEARCH_INPUT_SCOPES]
    output = subprocess.run(
        command,
        cwd=repository_root,
        check=True,
        capture_output=True,
    ).stdout
    return sorted(path.decode("utf-8") for path in output.split(b"\0") if path)


def compute_research_input_hash(
    repository_root: Path,
    *,
    revision: str | None = None,
) -> str:
    """Hash tracked runtime, prompt, scorer, KB, dataset and menu inputs."""

    files = _tracked_files(repository_root, revision)
    if not files:
        raise ValueError("no tracked research inputs found")
    if revision is None:
        return hash_files(repository_root, files)

    digest = hashlib.sha256()
    for relative_path in files:
        content = subprocess.run(
            ["git", "show", f"{revision}:{relative_path}"],
            cwd=repository_root,
            check=True,
            capture_output=True,
        ).stdout
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_canonical_content(content))
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"
