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
    ".scss": "scss",
    ".less": "css",
    ".html": "html",
    ".htm": "html",
    ".json": "json",
    ".jsonl": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".dockerfile": "dockerfile",
}

# Source-like extensions without a reliable parser in the current dependency
# set. They are still indexed as code through the line-window fallback.
CODE_EXTENSIONS_WITHOUT_LANGUAGE: set[str] = {
    ".bat",
    ".cmd",
    ".conf",
    ".config",
    ".env",
    ".gradle",
    ".graphql",
    ".ini",
    ".lock",
    ".lua",
    ".make",
    ".mk",
    ".pl",
    ".ps1",
    ".r",
    ".sol",
    ".tf",
    ".vue",
    ".svelte",
}

# Document extensions. Text documents are read directly; PDF/DOCX/IPYNB have
# dedicated readers.
DOC_EXTENSIONS: set[str] = {
    ".md",
    ".markdown",
    ".mdx",
    ".rst",
    ".txt",
    ".csv",
    ".tsv",
    ".log",
    ".ipynb",
    ".pdf",
    ".docx",
}

TEXT_DOC_EXTENSIONS: set[str] = {".md", ".markdown", ".rst", ".txt"}

# Obvious non-text formats. Unknown extensions not listed here are attempted as
# UTF-8 text so project-specific files can still be indexed.
BINARY_EXTENSIONS: set[str] = {
    ".7z",
    ".avi",
    ".bin",
    ".bmp",
    ".db",
    ".dll",
    ".dmg",
    ".doc",
    ".eot",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".iso",
    ".jar",
    ".jpeg",
    ".jpg",
    ".mov",
    ".mp3",
    ".mp4",
    ".otf",
    ".png",
    ".pyc",
    ".rar",
    ".sqlite",
    ".sqlite3",
    ".tar",
    ".ttf",
    ".wav",
    ".webm",
    ".webp",
    ".woff",
    ".woff2",
    ".zip",
}


def classify(path: Path) -> tuple[Kind, str | None] | None:
    """Return ``(kind, language)`` for an indexable file, or ``None`` to skip.

    ``language`` is the source language for code, and ``None`` for prose docs.
    """
    suffix = path.suffix.lower()
    if suffix in CODE_LANGUAGES:
        return "code", CODE_LANGUAGES[suffix]
    if suffix in CODE_EXTENSIONS_WITHOUT_LANGUAGE:
        return "code", None
    if suffix in DOC_EXTENSIONS:
        return "doc", None
    if suffix in BINARY_EXTENSIONS:
        return None
    if not suffix and path.name.lower() in {"dockerfile", "makefile", "gemfile", "rakefile"}:
        return "code", None
    # Fallback: attempt unknown extensions as text docs. The reader will reject
    # binary/unreadable files, but this avoids dropping project-specific formats.
    if suffix:
        return "doc", None
    return None
