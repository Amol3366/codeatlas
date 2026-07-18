"""Reading file contents into :class:`SourceFile` objects (CLAUDE.md §4).

Text source and document files are read as UTF-8; Jupyter notebooks are
flattened to their markdown + code cells. Binary document formats (pdf/docx)
are recognised but require extra parsers and are skipped with a warning for v1.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.ingestion.classify import classify
from app.models import SourceFile

logger = logging.getLogger(__name__)

# Recognised as documents but not yet parsed (would need pypdf/python-docx).
_UNSUPPORTED_DOC_SUFFIXES = {".pdf", ".docx"}


def _read_notebook(path: Path) -> str | None:
    """Flatten a Jupyter notebook into markdown + code cell text."""
    try:
        notebook = json.loads(path.read_text(encoding="utf-8", errors="strict"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning("Skipping unreadable notebook %s: %s", path, exc)
        return None
    parts: list[str] = []
    for cell in notebook.get("cells", []):
        source = cell.get("source", "")
        text = "".join(source) if isinstance(source, list) else str(source)
        if text.strip():
            parts.append(text)
    return "\n\n".join(parts)


def read_source_file(
    abs_path: Path,
    root: Path,
    repo: str,
    commit_hash: str | None,
) -> SourceFile | None:
    """Read one file into a :class:`SourceFile`, or ``None`` to skip it."""
    classification = classify(abs_path)
    if classification is None:
        return None
    kind, language = classification
    rel_path = abs_path.relative_to(root).as_posix()
    suffix = abs_path.suffix.lower()

    if suffix in _UNSUPPORTED_DOC_SUFFIXES:
        logger.warning("Skipping %s: %s parsing is not supported in v1", rel_path, suffix)
        return None

    if suffix == ".ipynb":
        content = _read_notebook(abs_path)
        if content is None:
            return None
    else:
        try:
            content = abs_path.read_text(encoding="utf-8", errors="strict")
        except (UnicodeDecodeError, OSError) as exc:
            logger.warning("Skipping unreadable file %s: %s", rel_path, exc)
            return None

    if not content.strip():
        return None

    return SourceFile(
        repo=repo,
        path=rel_path,
        abs_path=str(abs_path),
        content=content,
        language=language,
        kind=kind,
        commit_hash=commit_hash,
    )
