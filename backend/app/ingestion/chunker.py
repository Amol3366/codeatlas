"""Chunking source files into retrievable units (CLAUDE.md §4).

Code is parsed with tree-sitter and split at semantic boundaries (functions,
classes, methods) so a function is never split across chunks. Documents are
split with LangChain's recursive character splitter. All path/line metadata
comes from the parser/splitter — never from an LLM.

LangChain is used only here, behind the :class:`Chunker` interface, so its types
never leak into the rest of the codebase.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.interfaces import Chunker
from app.models import Chunk, SourceFile, make_chunk_id

if TYPE_CHECKING:
    from langchain_text_splitters import TextSplitter
    from tree_sitter import Node, Parser

logger = logging.getLogger(__name__)

# Definition nodes that may contain nested definitions (methods) — captured as a
# short "header" chunk plus one chunk per member.
CONTAINER_TYPES: frozenset[str] = frozenset(
    {
        "class_definition",  # python
        "class_declaration",  # js/ts/java/c_sharp/kotlin
        "abstract_class_declaration",  # ts
        "class_specifier",  # cpp
        "class",  # ruby
        "module",  # ruby module
        "impl_item",  # rust
        "trait_item",  # rust
        "namespace_definition",  # cpp
    }
)

# Definition nodes captured whole (never split).
LEAF_TYPES: frozenset[str] = frozenset(
    {
        "function_definition",  # python, c, cpp, php
        "function_declaration",  # js, ts, go
        "generator_function_declaration",
        "method_definition",  # js/ts
        "method_declaration",  # java, go, c_sharp
        "constructor_declaration",  # java
        "function_item",  # rust
        "method",  # ruby
        "singleton_method",  # ruby
        "interface_declaration",  # ts/java/c_sharp
        "enum_declaration",  # ts/java/c_sharp
        "enum_item",  # rust
        "struct_item",  # rust
        "struct_specifier",  # c/cpp
        "type_declaration",  # go
        "type_alias_declaration",  # ts
    }
)

# Wrappers whose span should be included with the definition they decorate.
_DECORATOR_PARENTS: frozenset[str] = frozenset({"decorated_definition", "export_statement"})

_NAME_NODE_TYPES: frozenset[str] = frozenset(
    {"identifier", "type_identifier", "constant", "field_identifier", "property_identifier", "name"}
)

# Line-window fallback (unsupported languages, parse failures, uncovered gaps).
_WINDOW_LINES = 60
_WINDOW_OVERLAP = 10
_MIN_GAP_LINES = 2

# Document splitter settings.
_DOC_CHUNK_SIZE = 1000
_DOC_CHUNK_OVERLAP = 150


def _nearest_definitions(node: Node) -> list[Node]:
    """Return the nearest definition descendants, skipping wrapper nodes.

    Descends through non-definition nodes (blocks, class bodies, decorators,
    exports) but stops at any definition, so nested helpers inside a function
    body are not hoisted to the top level.
    """
    found: list[Node] = []
    for child in node.named_children:
        if child.type in CONTAINER_TYPES or child.type in LEAF_TYPES:
            found.append(child)
        else:
            found.extend(_nearest_definitions(child))
    return found


def _effective_start_line(node: Node) -> int:
    """1-based start line, extended to include a decorator/export wrapper."""
    parent = node.parent
    if parent is not None and parent.type in _DECORATOR_PARENTS:
        return parent.start_point[0] + 1
    return node.start_point[0] + 1


def _symbol_name(node: Node) -> str | None:
    name_node = node.child_by_field_name("name")
    if name_node is not None and name_node.text is not None:
        return name_node.text.decode("utf-8", errors="replace")
    for child in node.named_children:
        if child.type in _NAME_NODE_TYPES and child.text is not None:
            return child.text.decode("utf-8", errors="replace")
    return None


class CodeChunker:
    """Semantic code chunking via tree-sitter, with a line-window fallback."""

    def chunk(self, file: SourceFile) -> list[Chunk]:
        lines = file.content.splitlines()
        if not lines:
            return []
        parser = self._get_parser(file.language)
        if parser is None:
            return self._line_windows(file, lines, 1, len(lines))
        tree = parser.parse(file.content.encode("utf-8"))
        spans: list[tuple[int, int, str | None]] = []
        self._collect(tree.root_node, spans)
        if not spans:
            return self._line_windows(file, lines, 1, len(lines))
        spans.extend(self._gap_spans(spans, len(lines), lines))
        return self._build_chunks(file, lines, spans)

    @staticmethod
    def _get_parser(language: str | None) -> Parser | None:
        if language is None:
            return None
        try:
            from tree_sitter_language_pack import get_parser

            return get_parser(language)
        except Exception as exc:  # noqa: BLE001 - any parser error degrades to line windows
            logger.debug("No tree-sitter parser for %s (%s); using line windows", language, exc)
            return None

    def _collect(self, node: Node, spans: list[tuple[int, int, str | None]]) -> None:
        for definition in _nearest_definitions(node):
            self._collect_definition(definition, spans)

    def _collect_definition(
        self, definition: Node, spans: list[tuple[int, int, str | None]]
    ) -> None:
        start_line = _effective_start_line(definition)
        symbol = _symbol_name(definition)
        if definition.type in CONTAINER_TYPES:
            members = _nearest_definitions(definition)
            if members:
                first_member_row = min(member.start_point[0] for member in members)
                # Header: class declaration up to (not including) the first member.
                spans.append((start_line, first_member_row, symbol))
                for member in members:
                    self._collect_definition(member, spans)
                return
        spans.append((start_line, definition.end_point[0] + 1, symbol))

    @staticmethod
    def _gap_spans(
        spans: list[tuple[int, int, str | None]],
        total_lines: int,
        lines: list[str],
    ) -> list[tuple[int, int, str | None]]:
        """Cover module-level code between/around definitions with generic spans."""
        covered = sorted((s, e) for s, e, _ in spans)
        merged: list[list[int]] = []
        for start, end in covered:
            if merged and start <= merged[-1][1] + 1:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        gaps: list[tuple[int, int, str | None]] = []
        cursor = 1
        for start, end in merged:
            if start - cursor >= _MIN_GAP_LINES:
                gaps.extend(_split_range(cursor, start - 1, lines))
            cursor = max(cursor, end + 1)
        if total_lines - cursor + 1 >= _MIN_GAP_LINES:
            gaps.extend(_split_range(cursor, total_lines, lines))
        return gaps

    def _line_windows(
        self, file: SourceFile, lines: list[str], start: int, end: int
    ) -> list[Chunk]:
        spans = _split_range(start, end, lines)
        return self._build_chunks(file, lines, spans)

    @staticmethod
    def _build_chunks(
        file: SourceFile,
        lines: list[str],
        spans: list[tuple[int, int, str | None]],
    ) -> list[Chunk]:
        chunks: list[Chunk] = []
        seen: set[tuple[int, int]] = set()
        for start_line, end_line, symbol in sorted(spans):
            if end_line < start_line or (start_line, end_line) in seen:
                continue
            content = "\n".join(lines[start_line - 1 : end_line])
            if not content.strip():
                continue
            seen.add((start_line, end_line))
            chunks.append(
                Chunk(
                    id=make_chunk_id(file.repo, file.path, start_line, end_line),
                    repo=file.repo,
                    path=file.path,
                    language=file.language,
                    kind="code",
                    symbol_name=symbol,
                    start_line=start_line,
                    end_line=end_line,
                    content=content,
                    commit_hash=file.commit_hash,
                )
            )
        return chunks


def _split_range(start: int, end: int, lines: list[str]) -> list[tuple[int, int, str | None]]:
    """Split an inclusive 1-based line range into overlapping windows."""
    if end < start:
        return []
    # Skip ranges that are entirely blank.
    if not any(line.strip() for line in lines[start - 1 : end]):
        return []
    windows: list[tuple[int, int, str | None]] = []
    cursor = start
    while cursor <= end:
        window_end = min(cursor + _WINDOW_LINES - 1, end)
        windows.append((cursor, window_end, None))
        if window_end == end:
            break
        cursor = window_end - _WINDOW_OVERLAP + 1
    return windows


class DocChunker:
    """Document chunking via LangChain's recursive character splitter."""

    def chunk(self, file: SourceFile) -> list[Chunk]:
        splitter = self._get_splitter(file.path)
        documents = splitter.create_documents([file.content])
        chunks: list[Chunk] = []
        for document in documents:
            start_index = int(document.metadata.get("start_index", 0))
            start_line = file.content.count("\n", 0, start_index) + 1
            end_line = start_line + document.page_content.count("\n")
            content = document.page_content
            if not content.strip():
                continue
            chunks.append(
                Chunk(
                    id=make_chunk_id(file.repo, file.path, start_line, end_line),
                    repo=file.repo,
                    path=file.path,
                    language=None,
                    kind="doc",
                    symbol_name=None,
                    start_line=start_line,
                    end_line=end_line,
                    content=content,
                    commit_hash=file.commit_hash,
                )
            )
        return chunks

    @staticmethod
    def _get_splitter(path: str) -> TextSplitter:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        if path.lower().endswith((".md", ".markdown")):
            from langchain_text_splitters import Language

            return RecursiveCharacterTextSplitter.from_language(
                language=Language.MARKDOWN,
                chunk_size=_DOC_CHUNK_SIZE,
                chunk_overlap=_DOC_CHUNK_OVERLAP,
                add_start_index=True,
            )
        return RecursiveCharacterTextSplitter(
            chunk_size=_DOC_CHUNK_SIZE,
            chunk_overlap=_DOC_CHUNK_OVERLAP,
            add_start_index=True,
        )


class CompositeChunker(Chunker):
    """Dispatches to the code or document chunker based on file kind."""

    def __init__(self) -> None:
        self._code = CodeChunker()
        self._doc = DocChunker()

    def chunk(self, file: SourceFile) -> list[Chunk]:
        if file.kind == "code":
            return self._code.chunk(file)
        return self._doc.chunk(file)
