"""Repository walking with ignore handling (CLAUDE.md §4).

Walks a target directory, honoring ``.gitignore`` plus a built-in ignore list
(VCS dirs, virtual envs, dependency and build artifacts, lockfiles), and yields
only files that classify as indexable source code or documents.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

import pathspec

from app.ingestion.classify import classify

# Built-in ignore patterns (gitwildmatch syntax), applied on top of .gitignore.
DEFAULT_IGNORE_PATTERNS: tuple[str, ...] = (
    ".git/",
    ".hg/",
    ".svn/",
    ".venv/",
    "venv/",
    "env/",
    "data/",
    "node_modules/",
    "bower_components/",
    "vendor/",
    "Pods/",
    "DerivedData/",
    "__pycache__/",
    "*.pyc",
    ".cache/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".pytest_cache/",
    ".tox/",
    ".coverage",
    "coverage/",
    "htmlcov/",
    "dist/",
    "build/",
    "out/",
    "target/",
    ".next/",
    ".nuxt/",
    ".svelte-kit/",
    ".angular/",
    ".vite/",
    ".turbo/",
    ".parcel-cache/",
    ".pnpm-store/",
    ".gradle/",
    ".idea/",
    ".vscode/",
    "logs/",
    ".DS_Store",
    # Lockfiles (would otherwise be classified via .json etc.)
    "*.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "Cargo.lock",
    # Minified / generated assets.
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.log",
    "*.sqlite",
    "*.sqlite3",
    "*.db",
)


def _build_spec(root: Path, extra_ignores: Sequence[str] | None) -> pathspec.PathSpec[Any]:
    lines: list[str] = list(DEFAULT_IGNORE_PATTERNS)
    gitignore = root / ".gitignore"
    if gitignore.is_file():
        lines.extend(gitignore.read_text(encoding="utf-8", errors="ignore").splitlines())
    if extra_ignores:
        lines.extend(extra_ignores)
    return pathspec.PathSpec.from_lines("gitignore", lines)


def walk_repo(root: Path, extra_ignores: Sequence[str] | None = None) -> Iterator[Path]:
    """Yield absolute paths of indexable files under ``root``.

    Directories matched by an ignore rule are pruned so we never descend into
    ``node_modules``/``.venv`` etc.
    """
    root = root.resolve()
    if root.is_file():
        if classify(root) is not None:
            yield root
        return
    spec = _build_spec(root, extra_ignores)
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        kept_dirs: list[str] = []
        for name in sorted(dirnames):
            rel = f"{(current / name).relative_to(root).as_posix()}/"
            if not spec.match_file(rel):
                kept_dirs.append(name)
        dirnames[:] = kept_dirs
        for name in sorted(filenames):
            file_path = current / name
            rel = file_path.relative_to(root).as_posix()
            if spec.match_file(rel):
                continue
            if classify(file_path) is None:
                continue
            yield file_path


def get_commit_hash(root: Path) -> str | None:
    """Return the current git commit hash for ``root``, or ``None`` if not a repo."""
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None
