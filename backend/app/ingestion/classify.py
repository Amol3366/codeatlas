"""Deterministic file classification (CLAUDE.md §4).

Classifies a file as source code (with a detected language) or a document by
extension. This is ground-truth metadata and never involves an LLM.
"""

from __future__ import annotations

from pathlib import Path

from app.models import Kind

# Extension -> tree-sitter language name (as used by tree-sitter-language-pack).
CODE_LANGUAGES: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".cs": "c_sharp",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sh": "bash",
    ".bash": "bash",
    ".sql": "sql",
    ".css": "css",
    ".html": "html",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
}

# Document extensions. Text-based ones are parsed; binary formats (pdf/docx) are
# classified as documents but require extra parsers (skipped with a warning).
DOC_EXTENSIONS: set[str] = {
    ".md",
    ".markdown",
    ".rst",
    ".txt",
    ".ipynb",
    ".pdf",
    ".docx",
}

TEXT_DOC_EXTENSIONS: set[str] = {".md", ".markdown", ".rst", ".txt"}


def classify(path: Path) -> tuple[Kind, str | None] | None:
    """Return ``(kind, language)`` for an indexable file, or ``None`` to skip.

    ``language`` is the source language for code, and ``None`` for prose docs.
    """
    suffix = path.suffix.lower()
    if suffix in CODE_LANGUAGES:
        return "code", CODE_LANGUAGES[suffix]
    if suffix in DOC_EXTENSIONS:
        return "doc", None
    return None
