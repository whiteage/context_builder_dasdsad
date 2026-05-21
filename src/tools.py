
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from langchain_core.tools import tool

from src.index import ProjectIndex, count_tokens


@dataclass
class ToolContext:
    """Tracks dedup state and token budget across tool calls in an agent session."""

    token_budget: int = 30000
    tokens_used: int = 0
    read_ranges: dict[str, set[tuple[int, int]]] = field(default_factory=dict)
    compacted: set[str] = field(default_factory=set)

    def consume(self, tokens: int) -> None:
        self.tokens_used += tokens

    def remaining(self) -> int:
        return max(0, self.token_budget - self.tokens_used)

    def mark_read(self, path: str, start: int, end: int) -> None:
        if path not in self.read_ranges:
            self.read_ranges[path] = set()
        self.read_ranges[path].add((start, end))

    def is_range_covered(self, path: str, start: int, end: int) -> bool:
        for r_start, r_end in self.read_ranges.get(path, set()):
            if r_start <= start and r_end >= end:
                return True
        return False

    def mark_compacted(self, path: str) -> None:
        self.compacted.add(path)

    def is_compacted(self, path: str) -> bool:
        return path in self.compacted


# Patterns for secrets masking
_SECRET_PATTERNS = [
    # API keys (common formats)
    (re.compile(r'(?:api[_-]?key|apikey|API_KEY|apiKey)\s*[:=]\s*[\'"]([^\'"]+)[\'"]', re.IGNORECASE),
     lambda m: m.group(0).replace(m.group(1), "***")),
    (re.compile(r'(?:api[_-]?key|apikey|API_KEY|apiKey)\s*[:=]\s*(\S+)', re.IGNORECASE),
     lambda m: m.group(0).replace(m.group(1), "***")),
    # DEEPSEEK_API_KEY=sk-..., OPENAI_API_KEY=sk-..., ANTHROPIC_API_KEY=sk-...
    (re.compile(r'(\w*API[_-]?KEY\w*)\s*=\s*(\S+)', re.IGNORECASE),
     lambda m: f'{m.group(1)}=***'),
    # Generic secret/token/password assignment
    (re.compile(r'(?:secret|token|password|passwd|pwd)\s*[:=]\s*[\'"]([^\'"]+)[\'"]', re.IGNORECASE),
     lambda m: m.group(0).replace(m.group(1), "***")),
    (re.compile(r'(?:secret|token|password|passwd|pwd)\s*[:=]\s*(\S+)', re.IGNORECASE),
     lambda m: m.group(0).replace(m.group(1), "***")),
    # JWT tokens (eyJ...)
    (re.compile(r'eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+'),
     lambda m: "***JWT***"),
    # Private key PEM headers (mask the entire block)
    (re.compile(r'-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----'
                r'[\s\S]*?'
                r'-----END (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----'),
     lambda m: "***PRIVATE KEY***"),
    # Connection strings with passwords
    (re.compile(r'(?:password|pwd)=([^;&\s]+)', re.IGNORECASE),
     lambda m: m.group(0).replace(m.group(1), "***")),
]


def mask_secrets(text: str) -> str:
    """Mask API keys, tokens, passwords, and private keys in text."""
    for pattern, replacer in _SECRET_PATTERNS:
        text = pattern.sub(replacer, text)
    return text


def create_tools(index: ProjectIndex, ctx: ToolContext = None) -> list:
    """Create tool instances bound to a ProjectIndex and optional ToolContext."""
    if ctx is None:
        ctx = ToolContext()

    @tool
    def list_files(directory: str = ".") -> str:
        """List files and directories in the project at the given path.

        Args:
            directory: Path relative to project root. Use '.' for root.
        """
        import os
        norm = directory.replace("\\", "/").rstrip("/")
        if norm == ".":
            norm = ""

        lines = []
        for path, entry in sorted(index.repo.files.items()):
            dir_part = os.path.dirname(path).replace("\\", "/")
            if dir_part == norm or (norm == "" and "/" not in dir_part):
                lines.append(f"  {entry.path} [{entry.language}] ({entry.file_type})")

        if not lines:
            return f"No files found in '{directory}'"

        return f"Files in '{directory or 'root'}' ({len(lines)} items):\n" + "\n".join(lines[:100])

    @tool
    def read_file(path: str, start_line: int = 1, end_line: int = 0) -> str:
        """Read the contents of a file. Returns content with line numbers.

        Args:
            path: File path relative to project root.
            start_line: First line to read (1-based). Default 1.
            end_line: Last line to read (0 = read to end). Default 0.
        """
        entry = index.repo.files.get(path)
        if entry is None:
            return f"File not found: {path}"

        full_path = Path(index.repo.project_path) / path
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"Error reading file: {e}"

        lines = content.split("\n")
        total = len(lines)

        if end_line == 0:
            end_line = total

        start = max(1, start_line) - 1
        end = min(end_line, total)

        # Dedup: skip already-read ranges
        if ctx.is_range_covered(path, start + 1, end):
            return f"[SKIP] {path} lines {start + 1}-{end} already read. Remaining budget: {ctx.remaining()} tokens."

        # Auto-dedup: if reading entire large file, suggest compact_file first
        reading_all = (start_line == 1 and end_line == total)
        if reading_all and total > 80:
            preview = mask_secrets("\n".join(
                f"{i + 1}: {line}" for i, line in enumerate(lines[:30])
            ))
            ctx.mark_read(path, 1, 30)
            return (
                f"File: {path} ({total} lines total)\n"
                f"[TIP: This file is {total} lines. Use compact_file('{path}') first to see only signatures.\n"
                f" Then use read_file('{path}', start_line=X, end_line=Y) to read specific sections.\n"
                f" First 30 lines as preview:\n]"
                + preview
            )

        result = mask_secrets("\n".join(
            f"{i + 1}: {line}"
            for i, line in enumerate(lines[start:end], start=start)
        ))
        token_count = count_tokens(result)
        ctx.consume(token_count)
        ctx.mark_read(path, start + 1, end)

        header = f"File: {path} (lines {start + 1}-{end} of {total})"
        if token_count > 2000:
            header += f" [~{token_count} tokens. Budget remaining: {ctx.remaining()}. Use compact_file() first for large files.]"
        return f"{header}\n{result}"

    @tool
    def search_symbol(name: str) -> str:
        """Search for a class, method, or function by name. Case-insensitive partial match.

        Args:
            name: Symbol name to search for.
        """
        results = index.find_symbols(name=name)

        if not results:
            return f"No symbols found matching '{name}'"

        lines = [f"Found {len(results)} matching '{name}':"]
        for r in results[:30]:
            if r["type"] == "method":
                params = ", ".join(f"{p.type} {p.name}" for p in r["parameters"])
                lines.append(f"  [{r['type']}] {r['class_name']}.{r['name']}({params}) in {r['path']}")
            elif r["type"] == "function":
                params = ", ".join(f"{p.type} {p.name}" for p in r["parameters"])
                lines.append(f"  [{r['type']}] {r['name']}({params}) in {r['path']}")
            else:
                lines.append(f"  [{r['type']}] {r['name']} in {r['path']}")
                for m in r.get("methods", [])[:3]:
                    params = ", ".join(f"{p.type} {p.name}" for p in m.parameters)
                    lines.append(f"    {m.return_type or 'void'} {m.name}({params})")

        if len(results) > 30:
            lines.append(f"  ... ({len(results) - 30} more)")
        return "\n".join(lines)

    @tool
    def get_dependencies(path: str) -> str:
        """Get files that the given file imports, and files that import it.

        Args:
            path: File path relative to project root.
        """
        if path not in index.repo.files:
            return f"File not found: {path}"

        deps = index.get_dependencies(path)
        dents = index.get_dependents(path)

        lines = [f"Dependencies for: {path}"]
        lines.append(f"  Imports ({len(deps)}):")
        for d in deps[:20]:
            lines.append(f"    {d}")
        lines.append(f"  Imported by ({len(dents)}):")
        for d in dents[:20]:
            lines.append(f"    {d}")
        return "\n".join(lines)

    @tool
    def find_files(pattern: str = "*", *, language: str = "", file_type: str = "") -> str:
        """Find files by name pattern, language, or type.

        Args:
            pattern: File name pattern (e.g. '*.cs', '*controller*'). Default '*'.
            language: Filter by language (csharp, typescript, php, dart).
            file_type: Filter by type (source, test, config, doc).
        """
        results = index.find_files(
            language=language or None,
            file_type=file_type or None,
            pattern=pattern or None,
        )

        if not results:
            return "No files found"

        lines = [f"Found {len(results)} files:"]
        for e in results[:50]:
            lines.append(f"  {e.path} [{e.language}] ({e.file_type})")
        if len(results) > 50:
            lines.append(f"  ... ({len(results) - 50} more)")
        return "\n".join(lines)

    @tool
    def get_call_graph(method: str = "") -> str:
        """Show method-level call graph: which methods call which.

        Args:
            method: Optional filter — show only calls from/to this method name.
        """
        graph = index.deps.call_graph
        if not graph:
            return "No call graph data available. AST parsing may not have extracted method calls."

        if method:
            filtered = {k: v for k, v in graph.items() if method.lower() in k.lower()}
            if not filtered:
                return f"No call graph entries matching '{method}'"
            graph = filtered

        lines = [f"Call graph ({len(graph)} methods with outgoing calls):"]
        for source, targets in sorted(graph.items())[:30]:
            target_list = sorted(targets)[:10]
            t_str = ", ".join(target_list)
            if len(targets) > 10:
                t_str += f" ... ({len(targets) - 10} more)"
            lines.append(f"  {source}")
            lines.append(f"    ->{t_str}")
        if len(graph) > 30:
            lines.append(f"  ... ({len(graph) - 30} more methods)")
        return "\n".join(lines)

    @tool
    def get_module_graph() -> str:
        """Show module-level dependency graph: which top-level directories import which."""
        graph = index.deps.module_graph
        if not graph:
            return "No module graph data available."

        lines = ["Module graph (top-level directory dependencies):"]
        for source, targets in sorted(graph.items()):
            t_str = ", ".join(sorted(targets))
            lines.append(f"  {source}/ -> {t_str}")
        return "\n".join(lines)

    @tool
    def classify_entities(language: str = "") -> str:
        """Classify source files by entity type: controller, service, repository, DTO, etc.

        Uses AST data (base types, class names) + path heuristics.

        Args:
            language: Filter by language. Leave empty for all.
        """
        result = index.classify_entities(language=language or "")
        if not result:
            return "No entities classified. Run on a project with AST-parsed source files."

        lines = [f"Entity classification ({sum(len(v) for v in result.values())} files):"]
        for etype in ["controller", "service", "repository", "dto", "entity",
                      "handler", "validator", "middleware", "factory",
                      "page", "widget", "composable", "store", "route",
                      "monobehaviour", "scriptableobject", "system", "prefab",
                      "unknown"]:
            files = result.get(etype, [])
            if files:
                lines.append(f"  {etype}: {len(files)} files")
                for f in files[:5]:
                    lines.append(f"    {f}")
                if len(files) > 5:
                    lines.append(f"    ... ({len(files) - 5} more)")
        return "\n".join(lines)

    @tool
    def sample_signatures(n: int = 30) -> str:
        """Get a random sample of class/method signatures for convention analysis.

        Returns class names, method signatures, base types, interfaces, attributes.
        Use this to detect naming conventions, architectural patterns, and code style.

        Args:
            n: Number of classes to sample. Default 30.
        """
        samples = index.ast.get_sample_signatures(n)
        if not samples:
            return "No AST data available. The project may not have been parsed yet."

        lines = [f"Sample of {len(samples)} classes:"]
        for s in samples:
            lines.append(f"  {s['class']} ({s['type']}) in {s['file']}")
            if s.get("namespace"):
                lines.append(f"    namespace: {s['namespace']}")
            if s.get("base_types"):
                lines.append(f"    extends: {', '.join(s['base_types'])}")
            if s.get("interfaces"):
                lines.append(f"    implements: {', '.join(s['interfaces'])}")
            if s.get("attributes"):
                lines.append(f"    attributes: {', '.join(s['attributes'])}")
            for m in s.get("methods", []):
                params = ", ".join(m.get("params", []))
                mods = " ".join(m.get("modifiers", []))
                ret = m.get("return", "void")
                lines.append(f"    {mods} {ret} {m['name']}({params})")
            if s.get("constructor_params"):
                for cp in s["constructor_params"]:
                    lines.append(f"    constructor({', '.join(cp)})")
        return "\n".join(lines)

    @tool
    def rank_files(files: str = "", center: str = "") -> str:
        """Rank files by relevance using dependency graph and priority scoring.

        Args:
            files: Comma-separated list of file paths to rank. Leave empty to rank all.
            center: A file to measure distance from. Files closer to this rank higher.
        """
        if files:
            paths = [f.strip() for f in files.split(",") if f.strip()]
        else:
            paths = list(index.repo.files.keys())

        ranked = index.rank_files(paths, center_path=center)
        if not ranked:
            return "No files to rank."

        lines = [f"Ranked files ({len(ranked)} total):"]
        for path, score in ranked[:30]:
            etype = index._guess_entity_type(path)
            lines.append(f"  {score:.3f} [{etype}] {path}")
        if len(ranked) > 30:
            lines.append(f"  ... ({len(ranked) - 30} more)")
        return "\n".join(lines)

    @tool
    def find_similar(class_name: str) -> str:
        """Find classes similar to the given one by base type, interfaces, attributes, or naming.

        Args:
            class_name: Exact class name to find similar implementations for.
        """
        results = index.find_similar(class_name, n=15)
        if not results:
            return f"No similar classes found for '{class_name}'."

        lines = [f"Classes similar to '{class_name}' ({len(results)} found):"]
        for path, name, reasons in results:
            lines.append(f"  {name} in {path}")
            lines.append(f"    reasons: {', '.join(reasons)}")
        return "\n".join(lines)

    @tool
    def compact_file(path: str) -> str:
        """Get a compact (boilerplate-free) view of a file: signature lines only, no comments.

        Use this to quickly scan many files without burning tokens on implementation details.

        Args:
            path: File path relative to project root.
        """
        if ctx.is_compacted(path):
            return f"[SKIP] {path} already compacted. Use read_file() for specific sections."
        result = index.compact_source(path)
        if result is None:
            return f"Cannot compact: {path}"
        token_count = count_tokens(result)
        ctx.consume(token_count)
        ctx.mark_compacted(path)
        return mask_secrets(result)

    @tool
    def get_summary() -> str:
        """Get a high-level summary of the project: file counts, languages, structure."""
        return index.summarize()

    @tool
    def get_token_budget() -> str:
        """Check remaining token budget. Call before reading large files.

        Returns used tokens, remaining budget, and files already read/compacted.
        """
        return (
            f"Token budget: {ctx.tokens_used} used, {ctx.remaining()} remaining (of {ctx.token_budget}).\n"
            f"Files read: {len(ctx.read_ranges)}. Files compacted: {len(ctx.compacted)}."
        )

    @tool
    def get_docs() -> str:
        """Find and read project documentation files.

        Searches for: README.md, ARCHITECTURE.md, AI_RULES.md, CONTRIBUTING.md,
        CONTRIBUTORS.md, docs/*.md, and ADR (Architecture Decision Records).
        Returns contents of found documents.
        """
        import fnmatch
        doc_names = [
            "readme.md", "architecture.md", "ai_rules.md", "contributing.md",
            "contributors.md", "changelog.md", "code_of_conduct.md",
            "security.md", "license.md",
        ]
        found: list[str] = []

        for path, entry in index.repo.files.items():
            fname = Path(path).name.lower()
            if fname in doc_names:
                found.append(path)
                continue
            if fnmatch.fnmatch(path.lower(), "docs/*.md"):
                found.append(path)
                continue
            if fnmatch.fnmatch(path.lower(), "**/adr/*.md"):
                found.append(path)
                continue

        if not found:
            return "No documentation files found (README.md, ARCHITECTURE.md, AI_RULES.md, etc.)"

        lines = [f"Found {len(found)} documentation files:"]
        for p in sorted(found)[:20]:
            lines.append(f"  {p}")
        if len(found) > 20:
            lines.append(f"  ... ({len(found) - 20} more)")

        # Read first 60 lines of top 5 docs
        lines.append("\n--- Preview (first 30 lines of top docs) ---")
        for p in sorted(found)[:3]:
            full_path = Path(index.repo.project_path) / p
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
                preview_lines = content.split("\n")[:30]
                lines.append(f"\n### {p}")
                lines.append(mask_secrets("\n".join(
                    f"{i + 1}: {line}" for i, line in enumerate(preview_lines)
                )))
            except Exception:
                lines.append(f"\n### {p} — error reading")

        return "\n".join(lines)

    return [list_files, read_file, search_symbol, get_dependencies, find_files,
            get_call_graph, get_module_graph, sample_signatures,
            rank_files, find_similar, compact_file, classify_entities,
            get_summary, get_docs, get_token_budget]