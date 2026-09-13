"""Observe/query a symbol-free exact-source and structural repository map.

The source repository is read-only. Generated records live under the external
test library. Python receives a real AST map. Other code languages receive an
exact-source file node and an explicit parser status until a verified parser
adapter is added; no regex-derived architecture is promoted as parsed code.
"""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any, Iterable, Iterator


SCHEMA = "truesystems_repository_map@1"
DEFAULT_REPO = Path.cwd()
DEFAULT_OUTPUT = Path.cwd() / "truemachine-repository-maps"

CODE_SUFFIXES = {
    ".py": "python", ".pyw": "python", ".rs": "rust", ".c": "c", ".cc": "cpp",
    ".cpp": "cpp", ".cxx": "cpp", ".h": "c_cpp_header", ".hh": "cpp_header",
    ".hpp": "cpp_header", ".hxx": "cpp_header", ".js": "javascript",
    ".jsx": "javascript_jsx", ".ts": "typescript", ".tsx": "typescript_tsx",
    ".sh": "shell", ".bash": "shell", ".zsh": "shell", ".fish": "fish",
    ".ps1": "powershell", ".html": "html", ".css": "css", ".qml": "qml",
}
TEXT_SUFFIXES = {".md", ".markdown", ".rst", ".txt", ".gitignore", ".service", ".example"}
STRUCTURED_SUFFIXES = {".json", ".jsonl", ".toml", ".yaml", ".yml", ".csv"}
WORD_OR_STRUCTURE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
SENTENCE_END = re.compile(r"(?<=[.!?])(?:[\"')\]]*)\s+|\n+")


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def stable_id(kind: str, *parts: object) -> str:
    payload = {"kind": kind, "parts": list(parts)}
    return hashlib.sha256(canonical(payload)).hexdigest()


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", "-C", str(repo), *args], check=check, capture_output=True)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


class JsonlWriter:
    def __init__(self, path: Path):
        self.path = path
        self.handle = path.open("wb")
        self.count = 0
        self.digest = hashlib.sha256()

    def write(self, value: object) -> None:
        raw = canonical(value)
        self.handle.write(raw)
        self.digest.update(raw)
        self.count += 1

    def close(self) -> dict[str, Any]:
        self.handle.flush()
        os.fsync(self.handle.fileno())
        self.handle.close()
        return {"path": self.path.name, "records": self.count, "sha256": self.digest.hexdigest(), "bytes": self.path.stat().st_size}


@dataclass(frozen=True)
class NodeRef:
    node_id: str
    file_id: str
    path: str
    kind: str
    name: str
    qualname: str
    owner_id: str | None
    line_start: int
    line_end: int
    column_start: int
    column_end: int
    byte_start: int
    byte_end: int
    sibling_ordinal: int


def byte_line_starts(raw: bytes) -> list[int]:
    starts = [0]
    for index, value in enumerate(raw):
        if value == 10:
            starts.append(index + 1)
    return starts


def ast_span(node: ast.AST, starts: list[int], raw_len: int) -> tuple[int, int, int, int, int, int]:
    line_start = int(getattr(node, "lineno", 1) or 1)
    line_end = int(getattr(node, "end_lineno", line_start) or line_start)
    column_start = int(getattr(node, "col_offset", 0) or 0)
    column_end = int(getattr(node, "end_col_offset", column_start) or column_start)
    start_base = starts[min(max(line_start - 1, 0), len(starts) - 1)]
    end_base = starts[min(max(line_end - 1, 0), len(starts) - 1)]
    return line_start, line_end, column_start, column_end, min(start_base + column_start, raw_len), min(end_base + column_end, raw_len)


def dotted(node: ast.AST | None) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Call):
        return dotted(node.func)
    return ""


def direct_statement_children(node: ast.AST) -> list[ast.stmt]:
    rows: list[ast.stmt] = []
    for field in ("body", "orelse", "finalbody"):
        value = getattr(node, field, None)
        if isinstance(value, list):
            rows.extend(item for item in value if isinstance(item, ast.stmt))
    handlers = getattr(node, "handlers", None)
    if isinstance(handlers, list):
        for handler in handlers:
            rows.extend(item for item in getattr(handler, "body", []) if isinstance(item, ast.stmt))
    rows.sort(key=lambda item: (getattr(item, "lineno", 0), getattr(item, "col_offset", 0)))
    return rows


class PythonMapper:
    def __init__(self, *, snapshot_id: str, file_id: str, path: str, raw: bytes, nodes: JsonlWriter,
                 edges: JsonlWriter, calls: JsonlWriter, accesses: JsonlWriter, diagnostics: JsonlWriter):
        self.snapshot_id = snapshot_id
        self.file_id = file_id
        self.path = path
        self.raw = raw
        self.text = raw.decode("utf-8")
        self.starts = byte_line_starts(raw)
        self.nodes_out = nodes
        self.edges_out = edges
        self.calls_out = calls
        self.accesses_out = accesses
        self.diagnostics_out = diagnostics
        self.refs: list[NodeRef] = []
        self.ast_to_ref: dict[int, NodeRef] = {}
        self.scope_for_ast: dict[int, NodeRef] = {}
        self.imports: list[dict[str, Any]] = []
        self.call_sites: list[dict[str, Any]] = []

    def add_node(self, node: ast.AST, *, kind: str, name: str, qualname: str, owner: NodeRef | None,
                 sibling_ordinal: int, resolution: str = "PARSED_STRUCTURE") -> NodeRef:
        span = ast_span(node, self.starts, len(self.raw))
        node_id = stable_id("code_object", self.snapshot_id, self.path, kind, qualname, span[4], span[5])
        ref = NodeRef(node_id, self.file_id, self.path, kind, name, qualname, owner.node_id if owner else None,
                      *span, sibling_ordinal)
        self.refs.append(ref)
        self.ast_to_ref[id(node)] = ref
        exact = self.raw[ref.byte_start:ref.byte_end]
        self.nodes_out.write({
            "schema": "truesystems_code_object@1", "node_id": ref.node_id, "file_id": ref.file_id,
            "path": ref.path, "language": "python", "kind": ref.kind, "name": ref.name,
            "qualified_name": ref.qualname, "owner_node_id": ref.owner_id,
            "line_start": ref.line_start, "line_end": ref.line_end,
            "column_start": ref.column_start, "column_end": ref.column_end,
            "byte_start": ref.byte_start, "byte_end": ref.byte_end,
            "exact_span_sha256": sha256(exact), "sibling_ordinal": ref.sibling_ordinal,
            "parser": "python_stdlib_ast@" + sys.version.split()[0], "resolution": resolution,
        })
        if owner:
            self.edge(owner.node_id, "CONTAINS", ref.node_id, "WITNESSED_STATIC", ref,
                      {"ownership_depth": 1})
            self.edge(ref.node_id, "OWNED_BY", owner.node_id, "WITNESSED_STATIC", ref,
                      {"ownership_depth": -1})
        return ref

    def edge(self, source: str, relation: str, target: str | None, status: str, witness: NodeRef,
             channels: dict[str, Any], *, target_surface: str | None = None, candidates: list[str] | None = None) -> None:
        record = {
            "schema": "truesystems_code_relationship@1", "source_node_id": source,
            "relation": relation, "target_node_id": target, "target_surface": target_surface,
            "resolution": status, "witness": {"path": self.path, "file_id": self.file_id,
                "line_start": witness.line_start, "line_end": witness.line_end,
                "byte_start": witness.byte_start, "byte_end": witness.byte_end,
                "exact_span_sha256": sha256(self.raw[witness.byte_start:witness.byte_end])},
            "channels": channels, "candidate_target_node_ids": candidates or [],
        }
        record["relationship_id"] = stable_id("code_relationship", record)
        self.edges_out.write(record)

    def map(self) -> dict[str, Any]:
        try:
            tree = ast.parse(self.text, filename=self.path, type_comments=True)
        except (SyntaxError, ValueError) as error:
            self.diagnostics_out.write({"schema": "truesystems_code_diagnostic@1", "path": self.path,
                "file_id": self.file_id, "status": "SYNTAX_REJECTED", "parser": "python_stdlib_ast",
                "error_type": type(error).__name__, "line": getattr(error, "lineno", None),
                "column": getattr(error, "offset", None), "message": str(error)})
            return {"status": "SYNTAX_REJECTED", "nodes": 0, "call_sites": 0}

        module_proxy = ast.Module(body=tree.body, type_ignores=[])
        module_proxy.lineno, module_proxy.col_offset = 1, 0
        module_proxy.end_lineno = max(1, self.text.count("\n") + 1)
        module_proxy.end_col_offset = 0 if self.raw.endswith(b"\n") else len(self.raw.rsplit(b"\n", 1)[-1])
        module = self.add_node(module_proxy, kind="module", name=self.path, qualname=self.path,
                               owner=None, sibling_ordinal=0)
        self.scope_for_ast[id(tree)] = module
        self._walk_body(tree.body, module, self.path)
        self._extract_sites(tree, module)
        self._source_order_edges()
        return {"status": "PARSED", "nodes": len(self.refs), "call_sites": len(self.call_sites)}

    def _walk_body(self, body: list[ast.stmt], owner: NodeRef, prefix: str) -> None:
        ordinal = 0
        for item in body:
            if isinstance(item, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                kind = "class" if isinstance(item, ast.ClassDef) else "async_function" if isinstance(item, ast.AsyncFunctionDef) else "function"
                qual = f"{prefix}.{item.name}"
                ref = self.add_node(item, kind=kind, name=item.name, qualname=qual, owner=owner, sibling_ordinal=ordinal)
                self.scope_for_ast[id(item)] = ref
                self._walk_body(item.body, ref, qual)
                ordinal += 1
            elif isinstance(item, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith, ast.Match)):
                name = f"{type(item).__name__}@{getattr(item, 'lineno', 0)}"
                qual = f"{prefix}.{name}"
                ref = self.add_node(item, kind="control", name=name, qualname=qual, owner=owner, sibling_ordinal=ordinal)
                self.scope_for_ast[id(item)] = owner
                children = direct_statement_children(item)
                self._walk_body(children, ref, qual)
                ordinal += 1

    def _nearest_scope(self, parents: dict[int, ast.AST], node: ast.AST, fallback: NodeRef) -> NodeRef:
        current: ast.AST | None = node
        while current is not None:
            found = self.scope_for_ast.get(id(current)) or self.ast_to_ref.get(id(current))
            if found and found.kind in {"module", "class", "function", "async_function", "control"}:
                return found
            current = parents.get(id(current))
        return fallback

    def _extract_sites(self, tree: ast.Module, module: NodeRef) -> None:
        parents: dict[int, ast.AST] = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parents[id(child)] = parent
        for node in ast.walk(tree):
            scope = self._nearest_scope(parents, node, module)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports.append({"scope_node_id": scope.node_id, "kind": "import", "module": alias.name,
                                         "name": None, "alias": alias.asname or alias.name.split(".")[0],
                                         "line": node.lineno})
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    self.imports.append({"scope_node_id": scope.node_id, "kind": "from", "module": node.module or "",
                                         "level": node.level, "name": alias.name, "alias": alias.asname or alias.name,
                                         "line": node.lineno})
            elif isinstance(node, ast.Call):
                span = ast_span(node, self.starts, len(self.raw))
                surface = dotted(node.func)
                self.call_sites.append({"caller_node_id": scope.node_id, "path": self.path,
                    "callee_surface": surface, "line": span[0], "column": span[2],
                    "byte_start": span[4], "byte_end": span[5], "file_id": self.file_id})
            elif isinstance(node, ast.Name):
                span = ast_span(node, self.starts, len(self.raw))
                access = "READS_NAME" if isinstance(node.ctx, ast.Load) else "WRITES_NAME" if isinstance(node.ctx, (ast.Store, ast.Del)) else "UNKNOWN_NAME_ACCESS"
                self.accesses_out.write({"schema": "truesystems_code_name_access@1", "scope_node_id": scope.node_id,
                    "path": self.path, "file_id": self.file_id, "relation": access, "exact_name": node.id,
                    "line_start": span[0], "column_start": span[2], "byte_start": span[4], "byte_end": span[5],
                    "exact_span_sha256": sha256(self.raw[span[4]:span[5]])})
        for row in self.imports:
            self.calls_out.write({"schema": "truesystems_import_site@1", **row, "path": self.path, "file_id": self.file_id})
        for row in self.call_sites:
            self.calls_out.write({"schema": "truesystems_call_site@1", **row})

    def _source_order_edges(self) -> None:
        by_owner: dict[str, list[NodeRef]] = defaultdict(list)
        for ref in self.refs:
            if ref.owner_id:
                by_owner[ref.owner_id].append(ref)
        for owner_id, rows in by_owner.items():
            rows.sort(key=lambda row: (row.sibling_ordinal, row.byte_start, row.node_id))
            for left, right in zip(rows, rows[1:]):
                self.edge(left.node_id, "NEXT_OWNED_SOURCE_NODE", right.node_id, "WITNESSED_STATIC", right,
                          {"sibling_ordinal_delta": 1, "source_byte_delta": right.byte_start - left.byte_start})
                self.edge(right.node_id, "PREVIOUS_OWNED_SOURCE_NODE", left.node_id, "WITNESSED_STATIC", left,
                          {"sibling_ordinal_delta": -1, "source_byte_delta": left.byte_start - right.byte_start})


def source_paths(repo: Path) -> list[str]:
    raw = git(repo, "ls-files", "-co", "--exclude-standard", "-z").stdout
    return sorted({part.decode("utf-8", errors="surrogateescape") for part in raw.split(b"\0") if part})


def classify(path: str, raw: bytes) -> tuple[str, str | None, str]:
    suffix = Path(path).suffix.casefold()
    if suffix in CODE_SUFFIXES:
        return "source_code", CODE_SUFFIXES[suffix], "code"
    if suffix in STRUCTURED_SUFFIXES:
        return "structured_text", None, "text"
    if suffix in TEXT_SUFFIXES or Path(path).name in {"AGENTS.md", "README", "LICENSE", "Makefile"}:
        return "text_document", None, "text"
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return "binary_object", None, "binary"
    if b"\x00" in raw:
        return "binary_object", None, "binary"
    return "unclassified_utf8", None, "text"


def iter_text_blocks(text: str) -> Iterator[tuple[int, int]]:
    """Yield maximal nonblank-line spans in linear time.

    A prior reluctant-DOTALL expression could backtrack catastrophically on
    large structured records. This scanner makes the block boundary explicit.
    """
    active_start: int | None = None
    cursor = 0
    for line in text.splitlines(keepends=True):
        end = cursor + len(line)
        if line.strip():
            if active_start is None:
                active_start = cursor
        elif active_start is not None:
            block_end = cursor
            while block_end > active_start and text[block_end - 1].isspace():
                block_end -= 1
            if block_end > active_start:
                yield active_start, block_end
            active_start = None
        cursor = end
    if cursor < len(text):
        # splitlines() can omit a terminal fragment only for unusual line
        # boundaries; preserve it under the same exact rule.
        if text[cursor:].strip() and active_start is None:
            active_start = cursor
        cursor = len(text)
    if active_start is not None:
        block_end = len(text)
        while block_end > active_start and text[block_end - 1].isspace():
            block_end -= 1
        if block_end > active_start:
            yield active_start, block_end


def exact_text_records(text: str, file_id: str, path: str, blocks: JsonlWriter, sentences: JsonlWriter,
                       occurrences: JsonlWriter) -> tuple[int, int, int]:
    block_count = sentence_count = occurrence_count = 0
    for block_ordinal, (block_start, block_end) in enumerate(iter_text_blocks(text)):
        block_text = text[block_start:block_end]
        block_id = stable_id("text_block", file_id, block_start, block_end, sha256(block_text.encode("utf-8")))
        blocks.write({"schema": "truesystems_text_block@1", "block_id": block_id, "file_id": file_id,
                      "path": path, "block_ordinal": block_ordinal, "character_start": block_start,
                      "character_end": block_end, "exact_text_sha256": sha256(block_text.encode("utf-8"))})
        block_count += 1
        starts = [0]
        for boundary in SENTENCE_END.finditer(block_text):
            starts.append(boundary.end())
        starts = sorted(set(value for value in starts if value < len(block_text)))
        ends = starts[1:] + [len(block_text)]
        for sentence_ordinal, (local_start, local_end) in enumerate(zip(starts, ends)):
            while local_start < local_end and block_text[local_start].isspace(): local_start += 1
            while local_end > local_start and block_text[local_end - 1].isspace(): local_end -= 1
            if local_start >= local_end: continue
            absolute_start, absolute_end = block_start + local_start, block_start + local_end
            sentence_text = text[absolute_start:absolute_end]
            sentence_id = stable_id("text_sentence", file_id, absolute_start, absolute_end, sha256(sentence_text.encode("utf-8")))
            sentences.write({"schema": "truesystems_text_sentence@1", "sentence_id": sentence_id,
                "block_id": block_id, "file_id": file_id, "path": path,
                "sentence_ordinal_block": sentence_ordinal, "character_start": absolute_start,
                "character_end": absolute_end, "exact_text_sha256": sha256(sentence_text.encode("utf-8"))})
            sentence_count += 1
            for item_ordinal, item_match in enumerate(WORD_OR_STRUCTURE.finditer(sentence_text)):
                exact = item_match.group(0)
                start = absolute_start + item_match.start(); end = absolute_start + item_match.end()
                occurrences.write({"schema": "truesystems_exact_occurrence@1",
                    "occurrence_id": stable_id("exact_occurrence", file_id, start, end, exact),
                    "file_id": file_id, "path": path, "block_id": block_id, "sentence_id": sentence_id,
                    "item_ordinal_sentence": item_ordinal, "exact": exact, "character_start": start,
                    "character_end": end, "exact_text_sha256": sha256(exact.encode("utf-8"))})
                occurrence_count += 1
    return block_count, sentence_count, occurrence_count


def resolve_python_edges(out: Path, snapshot_id: str) -> dict[str, int]:
    nodes = [json.loads(line) for line in (out / "code_objects.jsonl").read_text().splitlines() if line]
    node_by_id = {row["node_id"]: row for row in nodes}
    by_path_name: dict[tuple[str, str], list[str]] = defaultdict(list)
    by_qual_tail: dict[str, list[str]] = defaultdict(list)
    module_nodes: dict[str, str] = {}
    for row in nodes:
        if row["kind"] == "module": module_nodes[row["path"]] = row["node_id"]
        else:
            by_path_name[(row["path"], row["name"])].append(row["node_id"])
            by_qual_tail[row["qualified_name"].split(".")[-1]].append(row["node_id"])
    writer = JsonlWriter(out / "resolved_dependency_relationships.jsonl")
    stats = defaultdict(int)
    with (out / "call_and_import_sites.jsonl").open("rb") as sites:
        for raw_line in sites:
            site = json.loads(raw_line)
            if site["schema"] != "truesystems_call_site@1":
                continue
            surface = site.get("callee_surface") or ""
            simple = surface.split(".")[-1] if surface else ""
            candidates = by_path_name.get((site["path"], simple), [])
            if not candidates:
                candidates = by_qual_tail.get(simple, []) if simple else []
            target = candidates[0] if len(candidates) == 1 else None
            resolution = "UNIQUE_RESOLUTION" if target else "AMBIGUOUS" if candidates else "UNRESOLVED"
            record = {"schema": "truesystems_code_relationship@1", "source_node_id": site["caller_node_id"],
                "relation": "CALLS", "target_node_id": target, "target_surface": surface,
                "resolution": resolution, "candidate_target_node_ids": candidates,
                "witness": {k: site[k] for k in ("path", "file_id", "line", "column", "byte_start", "byte_end")},
                "channels": {"call_graph_hops": 1, "ownership_depth": None, "source_line_delta": None}}
            record["relationship_id"] = stable_id("code_relationship", snapshot_id, record)
            writer.write(record); stats[resolution] += 1
    stats["records"] = writer.close()["records"]
    return dict(stats)


def build(args: argparse.Namespace) -> int:
    repo = args.repo.resolve()
    if not (repo / ".git").exists():
        raise SystemExit("source is not a git repository")
    commit = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
    status = git(repo, "status", "--porcelain=v1", "-z").stdout
    paths = source_paths(repo)
    path_facts = []
    for path in paths:
        source = repo / path
        if source.is_symlink():
            raw = os.readlink(source).encode("utf-8", errors="surrogateescape")
        elif source.is_file():
            raw = source.read_bytes()
        else:
            continue
        filesystem_mode = stat.S_IMODE(os.lstat(source).st_mode)
        path_facts.append((path, len(raw), sha256(raw), filesystem_mode))
    snapshot_id = stable_id("repository_snapshot", str(repo), commit, path_facts)
    out = args.output_parent.resolve() / ("repository-map-" + utc_stamp())
    out.mkdir(parents=True, exist_ok=False)
    writers = {name: JsonlWriter(out / f"{name}.jsonl") for name in (
        "files", "text_blocks", "text_sentences", "exact_occurrences", "code_objects",
        "code_relationships", "call_and_import_sites", "name_accesses", "diagnostics")}
    totals = defaultdict(int)
    parser_counts = defaultdict(int)
    for index, (path, size, digest, filesystem_mode) in enumerate(path_facts):
        source = repo / path
        raw = os.readlink(source).encode("utf-8", errors="surrogateescape") if source.is_symlink() else source.read_bytes()
        source_type, language, lane = classify(path, raw)
        file_id = stable_id("repository_file", snapshot_id, path, digest)
        writers["files"].write({"schema": "truesystems_repository_file@1", "snapshot_id": snapshot_id,
            "file_id": file_id, "path": path, "sha256": digest, "bytes": size,
            "filesystem_mode": f"{filesystem_mode:04o}",
            "source_type": source_type, "language": language, "lane": lane,
            "symlink": source.is_symlink(), "symlink_target": os.readlink(source) if source.is_symlink() else None})
        totals["files"] += 1; totals[f"lane_{lane}"] += 1
        if lane == "binary" or source.is_symlink():
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            writers["diagnostics"].write({"schema": "truesystems_code_diagnostic@1", "path": path,
                "file_id": file_id, "status": "NON_UTF8_TEXT_RETAINED_AS_BINARY"})
            continue
        if lane == "text":
            counts = exact_text_records(text, file_id, path, writers["text_blocks"], writers["text_sentences"], writers["exact_occurrences"])
            totals["text_blocks"] += counts[0]; totals["text_sentences"] += counts[1]; totals["exact_occurrences"] += counts[2]
        elif language == "python":
            mapper = PythonMapper(snapshot_id=snapshot_id, file_id=file_id, path=path, raw=raw,
                nodes=writers["code_objects"], edges=writers["code_relationships"],
                calls=writers["call_and_import_sites"], accesses=writers["name_accesses"],
                diagnostics=writers["diagnostics"])
            result = mapper.map(); parser_counts[result["status"]] += 1
        else:
            node_id = stable_id("code_file", snapshot_id, path, digest)
            writers["code_objects"].write({"schema": "truesystems_code_object@1", "node_id": node_id,
                "file_id": file_id, "path": path, "language": language, "kind": "source_file",
                "name": Path(path).name, "qualified_name": path, "owner_node_id": None,
                "line_start": 1, "line_end": text.count("\n") + 1, "column_start": 0,
                "column_end": 0, "byte_start": 0, "byte_end": len(raw), "exact_span_sha256": digest,
                "sibling_ordinal": 0, "parser": None, "resolution": "CODE_STRUCTURE_NOT_IMPLEMENTED"})
            writers["diagnostics"].write({"schema": "truesystems_code_diagnostic@1", "path": path,
                "file_id": file_id, "language": language, "status": "CODE_STRUCTURE_NOT_IMPLEMENTED"})
            parser_counts["CODE_STRUCTURE_NOT_IMPLEMENTED"] += 1
        if args.progress and (index + 1) % args.progress == 0:
            print(json.dumps({"processed": index + 1, "total": len(path_facts), "path": path}), flush=True)
    artifacts = {name: writer.close() for name, writer in writers.items()}
    dependency = resolve_python_edges(out, snapshot_id)
    artifacts["resolved_dependency_relationships"] = {"path": "resolved_dependency_relationships.jsonl",
        "records": dependency.pop("records"), "sha256": sha256((out / "resolved_dependency_relationships.jsonl").read_bytes()),
        "bytes": (out / "resolved_dependency_relationships.jsonl").stat().st_size}
    manifest = {"schema": SCHEMA, "repository": str(repo), "commit": commit,
        "working_tree_clean": not bool(status), "working_tree_status_sha256": sha256(status),
        "snapshot_id": snapshot_id, "persistent_symbols": False, "normalization_performed": False,
        "source_files_modified": False, "paths_from": "git ls-files -co --exclude-standard",
        "n_n_n_contract": {"ownership_radius": args.ownership_n, "source_order_radius": args.flow_n,
            "dependency_radius": args.dependency_n, "channels_collapsed": False,
            "meaning": "ownership-source_order-dependency",
            "control_flow_status": "NOT_IMPLEMENTED",
            "data_flow_status": "EXACT_NAME_ACCESS_EVIDENCE_ONLY"},
        "totals": dict(totals), "parser_statuses": dict(parser_counts),
        "dependency_resolution": dependency, "artifacts": artifacts}
    (out / "manifest.json").write_bytes(canonical(manifest))
    (out / "RUN.txt").write_text(
        f"python -B {Path(__file__).resolve()} build --repo {repo} --output-parent {args.output_parent.resolve()} "
        f"--ownership-n {args.ownership_n} --flow-n {args.flow_n} --dependency-n {args.dependency_n}\n",
        encoding="utf-8")
    print(json.dumps({"output": str(out), "snapshot_id": snapshot_id, "totals": dict(totals),
                      "parser_statuses": dict(parser_counts), "dependency_resolution": dependency}))
    return 0


def query(args: argparse.Namespace) -> int:
    root = args.map_dir.resolve()
    manifest = json.loads((root / "manifest.json").read_text())
    nodes = {row["node_id"]: row for row in map(json.loads, (root / "code_objects.jsonl").read_text().splitlines())}
    matches = [row for row in nodes.values() if args.exact in {row.get("name"), row.get("qualified_name")}]
    if args.path:
        matches = [row for row in matches if row.get("path") == args.path]
    if not matches:
        print(json.dumps({"status": "NOT_FOUND", "exact": args.exact})); return 2
    if len(matches) > 1:
        print(json.dumps({"status": "AMBIGUOUS", "matches": [{k: row[k] for k in ("node_id", "path", "qualified_name")} for row in matches]})); return 3
    center = matches[0]
    edge_files = [root / "code_relationships.jsonl", root / "resolved_dependency_relationships.jsonl"]
    adjacency: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge_file in edge_files:
        for line in edge_file.read_text().splitlines():
            edge = json.loads(line); adjacency[edge["source_node_id"]].append(edge)
    limits = {"CONTAINS": args.ownership_n, "OWNED_BY": args.ownership_n,
              "NEXT_OWNED_SOURCE_NODE": args.flow_n, "PREVIOUS_OWNED_SOURCE_NODE": args.flow_n,
              "CALLS": args.dependency_n}
    visited = {center["node_id"]: {"axis": "center", "depth": 0}}
    frontier = [(center["node_id"], relation, 0) for relation in limits]
    selected_edges = []
    while frontier:
        node_id, allowed_relation, depth = frontier.pop(0)
        if depth >= limits[allowed_relation]: continue
        for edge in adjacency.get(node_id, []):
            if edge["relation"] != allowed_relation or not edge.get("target_node_id"): continue
            selected_edges.append(edge); target = edge["target_node_id"]
            if target not in visited:
                visited[target] = {"axis": allowed_relation, "depth": depth + 1}
                frontier.append((target, allowed_relation, depth + 1))
    packet = {"schema": "truesystems_code_n_n_n_location_packet@1", "snapshot_id": manifest["snapshot_id"],
        "center": center, "radii": {"ownership": args.ownership_n, "source_order": args.flow_n, "dependency": args.dependency_n},
        "nodes": [{**nodes[node_id], "neighborhood": meta} for node_id, meta in visited.items() if node_id in nodes],
        "relationships": selected_edges, "answer": None, "persistent_symbols": False}
    packet["receipt_sha256"] = sha256(canonical(packet))
    print(json.dumps(packet, indent=2))
    return 0


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("rb") as source:
        for line_number, line in enumerate(source, 1):
            try:
                yield json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSONL {path.name}:{line_number}: {error}") from error


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(args: argparse.Namespace) -> int:
    """Verify generated artifacts, source custody, spans, and endpoints."""
    root = args.map_dir.resolve()
    manifest = json.loads((root / "manifest.json").read_bytes())
    repo = Path(manifest["repository"])
    if manifest.get("persistent_symbols") is not False:
        raise ValueError("repository map must not contain persistent symbols")
    if manifest.get("normalization_performed") is not False:
        raise ValueError("repository map must preserve exact source")
    contract = manifest.get("n_n_n_contract", {})
    if contract.get("meaning") != "ownership-source_order-dependency":
        raise ValueError("unknown N-N-N axis contract")
    if contract.get("control_flow_status") != "NOT_IMPLEMENTED":
        raise ValueError("unqualified control-flow authority")

    artifact_results: dict[str, dict[str, Any]] = {}
    for name, record in manifest["artifacts"].items():
        path = root / record["path"]
        actual_hash = hash_file(path)
        if actual_hash != record["sha256"]:
            raise ValueError(f"artifact hash mismatch: {name}")
        with path.open("rb") as source:
            line_count = sum(1 for _ in source)
        if line_count != record["records"]:
            raise ValueError(f"artifact record-count mismatch: {name}")
        artifact_results[name] = {
            "sha256": actual_hash,
            "records": line_count,
            "bytes": path.stat().st_size,
        }

    file_ids: set[str] = set()
    source_cache: dict[str, bytes] = {}
    for record in iter_jsonl(root / "files.jsonl"):
        path = repo / record["path"]
        if path.is_symlink():
            raw = os.readlink(path).encode("utf-8", errors="surrogateescape")
        else:
            raw = path.read_bytes()
        if sha256(raw) != record["sha256"]:
            raise ValueError(f"source changed since observation: {record['path']}")
        current_mode = f"{stat.S_IMODE(os.lstat(path).st_mode):04o}"
        if current_mode != record.get("filesystem_mode"):
            raise ValueError(f"source mode changed since observation: {record['path']}")
        if record["file_id"] in file_ids:
            raise ValueError(f"duplicate file identity: {record['file_id']}")
        file_ids.add(record["file_id"])

    node_ids: set[str] = set()
    span_count = 0
    for record in iter_jsonl(root / "code_objects.jsonl"):
        node_id = record["node_id"]
        if node_id in node_ids:
            raise ValueError(f"duplicate code-object identity: {node_id}")
        node_ids.add(node_id)
        path_text = record["path"]
        raw = source_cache.get(path_text)
        if raw is None:
            raw = (repo / path_text).read_bytes()
            source_cache[path_text] = raw
        start, end = record["byte_start"], record["byte_end"]
        if not 0 <= start <= end <= len(raw):
            raise ValueError(f"invalid source span: {path_text}:{start}:{end}")
        if sha256(raw[start:end]) != record["exact_span_sha256"]:
            raise ValueError(f"source-span hash mismatch: {path_text}:{start}:{end}")
        span_count += 1

    relationship_counts: dict[str, int] = {}
    for filename in ("code_relationships.jsonl", "resolved_dependency_relationships.jsonl"):
        count = 0
        for record in iter_jsonl(root / filename):
            if record["source_node_id"] not in node_ids:
                raise ValueError(f"dangling relationship source: {record['relationship_id']}")
            target = record.get("target_node_id")
            if target is not None and target not in node_ids:
                raise ValueError(f"dangling relationship target: {record['relationship_id']}")
            count += 1
        relationship_counts[filename] = count

    report = {
        "schema": "truemachine.repository_map_verification@1",
        "status": "PASS",
        "snapshot_id": manifest["snapshot_id"],
        "source_files": len(file_ids),
        "code_objects": span_count,
        "relationship_counts": relationship_counts,
        "artifacts": artifact_results,
    }
    report["receipt_sha256"] = sha256(canonical(report))
    print(json.dumps(report, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--repo", type=Path, default=DEFAULT_REPO)
    b.add_argument("--output-parent", type=Path, default=DEFAULT_OUTPUT)
    b.add_argument("--ownership-n", type=int, default=2)
    b.add_argument("--source-order-n", "--flow-n", dest="flow_n", type=int, default=6)
    b.add_argument("--dependency-n", type=int, default=3)
    b.add_argument("--progress", type=int, default=250)
    b.set_defaults(func=build)
    q = sub.add_parser("query")
    q.add_argument("--map-dir", type=Path, required=True)
    q.add_argument("--exact", required=True)
    q.add_argument("--path")
    q.add_argument("--ownership-n", type=int, default=2)
    q.add_argument("--source-order-n", "--flow-n", dest="flow_n", type=int, default=6)
    q.add_argument("--dependency-n", type=int, default=3)
    q.set_defaults(func=query)
    v = sub.add_parser("verify")
    v.add_argument("--map-dir", type=Path, required=True)
    v.set_defaults(func=verify)
    return root


def main() -> int:
    args = parser().parse_args()
    for name in ("ownership_n", "flow_n", "dependency_n"):
        if hasattr(args, name) and not 0 <= getattr(args, name) <= 64:
            raise SystemExit(f"{name} must be 0..64")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
