"""Repository scanner — walks project tree and indexes files."""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path

from src.config import Config


@dataclass
class FileEntry:
    path: str
    size: int
    mtime: float
    extension: str
    language: str
    file_type: str  # source / test / config / doc / generated / unknown
    is_test: bool
    is_doc: bool

    @property
    def ast_eligible(self) -> bool:
        return self.file_type in ("source", "test")


@dataclass
class FolderNode:
    name: str
    path: str
    children: list[FolderNode] = field(default_factory=list)
    files: list[FileEntry] = field(default_factory=list)


@dataclass
class RepoIndex:
    project_path: str
    files: dict[str, FileEntry]  # relative_path → FileEntry
    file_tree: FolderNode
    file_count: int
    files_by_language: dict[str, list[str]]  # language → [paths]
    files_by_type: dict[str, list[str]]  # type → [paths]
    dir_mtimes: dict[str, float] = field(default_factory=dict)  # rel_dir → mtime


TEST_PATTERNS = [
    "*Test*",
    "*Spec*",
    "*Tests*",
    "*.test.*",
    "*.spec.*",
]

TEST_FOLDERS = [
    "__tests__",
    "tests",
    "test",
    "spec",
    "specs",
    "Testing",
    "Test",
]

DOC_EXTENSIONS = {".md", ".rst", ".txt", ".adoc"}
DOC_FOLDERS = {"docs", "doc", "documentation"}

LANGUAGE_MAP = {
    ".cs": "csharp",
    ".csproj": "xml",
    ".sln": "text",
    ".php": "php",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".vue": "vue",
    ".dart": "dart",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".xml": "xml",
    ".config": "xml",
    ".css": "css",
    ".scss": "scss",
    ".html": "html",
    ".razor": "razor",
    ".cshtml": "razor",
    ".shader": "shader",
    ".hlsl": "hlsl",
    ".glsl": "glsl",
    ".compute": "hlsl",
    ".unity": "yaml",
    ".prefab": "yaml",
    ".asset": "yaml",
    ".meta": "yaml",
    ".env": "text",
    ".gitignore": "text",
    ".editorconfig": "text",
    # C++ / Unreal Engine
    ".cpp": "cpp",
    ".cxx": "cpp",
    ".cc": "cpp",
    ".c": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
    ".inl": "cpp",
}

GENERATED_EXTENSIONS = {
    ".g.cs", ".g.i.cs", ".designer.cs", ".generated.cs",
    ".gen.dart", ".g.dart", ".freezed.dart",
    ".min.js", ".min.css",
}


class RepoScanner:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._exclude_patterns = config.index_exclude

    def scan(self) -> RepoIndex:
        project_path = self.config.project_path
        files: dict[str, FileEntry] = {}
        root = FolderNode(name=project_path.name, path="")
        dir_mtimes: dict[str, float] = {}

        for dirpath, dirnames, filenames in os.walk(project_path):
            rel_dir = os.path.relpath(dirpath, project_path)
            if rel_dir == ".":
                rel_dir = ""

            # Record directory mtime for incremental scans
            try:
                dir_mtimes[rel_dir] = os.stat(dirpath).st_mtime
            except OSError:
                pass

            # Filter excluded directories
            dirnames[:] = [
                d for d in dirnames
                if not self._is_excluded(os.path.join(rel_dir, d).replace("\\", "/") + "/")
            ]

            for filename in filenames:
                rel_path = os.path.join(rel_dir, filename).replace("\\", "/")
                if self._is_excluded(rel_path):
                    continue

                full_path = os.path.join(dirpath, filename)
                try:
                    stat = os.stat(full_path)
                except OSError:
                    continue

                entry = self._classify_file(rel_path, filename, stat)
                files[rel_path] = entry

        # Build file tree
        for rel_path, entry in files.items():
            self._add_to_tree(root, rel_path, entry)

        # Group by language and type
        by_language: dict[str, list[str]] = {}
        by_type: dict[str, list[str]] = {}
        for rel_path, entry in files.items():
            by_language.setdefault(entry.language, []).append(rel_path)
            by_type.setdefault(entry.file_type, []).append(rel_path)

        return RepoIndex(
            project_path=str(project_path),
            files=files,
            file_tree=root,
            file_count=len(files),
            files_by_language=by_language,
            files_by_type=by_type,
            dir_mtimes=dir_mtimes,
        )

    def incremental_scan(self, existing: RepoIndex) -> tuple[list[str], list[str], RepoIndex]:
        """Scan and return (new_files, modified_files, updated_index).

        Uses directory mtimes to skip unchanged subtrees. Falls back to full
        scan when dir_mtimes cache is empty (first run after upgrade).
        """
        if not existing.dir_mtimes:
            new_index = self.scan()
        else:
            new_index = self._quick_scan(existing)

        new_files: list[str] = []
        modified: list[str] = []

        for path, entry in new_index.files.items():
            if path not in existing.files:
                new_files.append(path)
            elif entry.mtime != existing.files[path].mtime:
                modified.append(path)

        return new_files, modified, new_index

    def _quick_scan(self, existing: RepoIndex) -> RepoIndex:
        """Fast scan: walk directory tree but skip subtrees whose mtime hasn't changed."""
        project_path = self.config.project_path
        files: dict[str, FileEntry] = {}
        root = FolderNode(name=project_path.name, path="")
        dir_mtimes: dict[str, float] = {}
        cached_mtimes = existing.dir_mtimes

        # Build recursive subtree index: rel_dir -> [(path, entry), ...]
        # One pass over existing.files, then O(1) lookup per unchanged directory
        subtree_files: dict[str, list[tuple[str, FileEntry]]] = {}
        for path, entry in existing.files.items():
            parts = path.split("/")
            for i in range(len(parts)):
                prefix = "/".join(parts[:i])
                subtree_files.setdefault(prefix, []).append((path, entry))

        for dirpath, dirnames, filenames in os.walk(project_path):
            rel_dir = os.path.relpath(dirpath, project_path)
            if rel_dir == ".":
                rel_dir = ""

            try:
                current_mtime = os.stat(dirpath).st_mtime
                dir_mtimes[rel_dir] = current_mtime
            except OSError:
                current_mtime = None

            dirnames[:] = [
                d for d in dirnames
                if not self._is_excluded(os.path.join(rel_dir, d).replace("\\", "/") + "/")
            ]

            cached_mtime = cached_mtimes.get(rel_dir)
            if cached_mtime is not None and current_mtime is not None and current_mtime == cached_mtime:
                for path, entry in subtree_files.get(rel_dir, []):
                    files[path] = entry
                dirnames.clear()
                continue

            # Changed or new — scan files
            for filename in filenames:
                rel_path = os.path.join(rel_dir, filename).replace("\\", "/")
                if self._is_excluded(rel_path):
                    continue
                full_path = os.path.join(dirpath, filename)
                try:
                    stat = os.stat(full_path)
                except OSError:
                    continue
                entry = self._classify_file(rel_path, filename, stat)
                files[rel_path] = entry

        # Build file tree
        for rel_path, entry in files.items():
            self._add_to_tree(root, rel_path, entry)

        # Group by language and type
        by_language: dict[str, list[str]] = {}
        by_type: dict[str, list[str]] = {}
        for rel_path, entry in files.items():
            by_language.setdefault(entry.language, []).append(rel_path)
            by_type.setdefault(entry.file_type, []).append(rel_path)

        return RepoIndex(
            project_path=str(project_path),
            files=files,
            file_tree=root,
            file_count=len(files),
            files_by_language=by_language,
            files_by_type=by_type,
            dir_mtimes=dir_mtimes,
        )

    def _is_excluded(self, rel_path: str) -> bool:
        for pattern in self._exclude_patterns:
            norm_pattern = pattern.replace("\\", "/")
            norm_path = rel_path.replace("\\", "/")
            if fnmatch.fnmatch(norm_path, norm_pattern):
                return True
            if norm_path.startswith(norm_pattern.rstrip("/") + "/"):
                return True
            if norm_pattern.endswith("/**") and norm_path.startswith(norm_pattern[:-3] + "/"):
                return True
        return False

    def _classify_file(self, rel_path: str, filename: str, stat: os.stat_result) -> FileEntry:
        ext = Path(filename).suffix.lower()
        rel_lower = rel_path.lower()
        parts = rel_path.replace("\\", "/").split("/")

        is_test = False
        for part in parts[:-1]:
            if part in TEST_FOLDERS:
                is_test = True
                break
        if not is_test:
            for pattern in TEST_PATTERNS:
                if fnmatch.fnmatch(filename, pattern):
                    is_test = True
                    break

        is_doc = ext in DOC_EXTENSIONS or any(p in DOC_FOLDERS for p in parts)

        # Classify file type
        if ext in GENERATED_EXTENSIONS or ".generated" in rel_lower:
            file_type = "generated"
        elif is_test:
            file_type = "test"
        elif is_doc:
            file_type = "doc"
        elif ext in (".json", ".yaml", ".yml", ".xml", ".config", ".env", ".csproj",
                      ".sln", ".gitignore", ".editorconfig"):
            file_type = "config"
        elif ext in LANGUAGE_MAP and LANGUAGE_MAP[ext] not in ("text", "json", "yaml",
                                                                "xml", "css", "scss", "html"):
            file_type = "source"
        else:
            file_type = "unknown"

        return FileEntry(
            path=rel_path,
            size=stat.st_size,
            mtime=stat.st_mtime,
            extension=ext,
            language=LANGUAGE_MAP.get(ext, "unknown"),
            file_type=file_type,
            is_test=is_test,
            is_doc=is_doc,
        )

    def _add_to_tree(self, node: FolderNode, rel_path: str, entry: FileEntry) -> None:
        parts = rel_path.split("/")
        current = node
        for i, part in enumerate(parts[:-1]):
            child = None
            for c in current.children:
                if c.name == part:
                    child = c
                    break
            if child is None:
                child_path = "/".join(parts[:i + 1])
                child = FolderNode(name=part, path=child_path)
                current.children.append(child)
            current = child
        current.files.append(entry)

    @staticmethod
    def print_tree(node: FolderNode, indent: int = 0, max_depth: int = 4) -> str:
        """Return a string representation of the folder tree (for LLM prompts)."""
        lines = []
        if indent <= max_depth:
            prefix = "  " * indent
            if node.path:
                lines.append(f"{prefix}{node.name}/")
            for child in sorted(node.children, key=lambda c: c.name):
                lines.append(RepoScanner.print_tree(child, indent + 1, max_depth))
            for f in sorted(node.files, key=lambda f: f.path)[:5]:  # limit files per folder
                lines.append(f"{prefix}  {Path(f.path).name}")
            if len(node.files) > 10:
                lines.append(f"{prefix}  ... ({len(node.files) - 10} more files)")
        return "\n".join(lines)
