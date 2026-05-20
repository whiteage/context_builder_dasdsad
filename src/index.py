from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

from src.config import Config
from src.scanner import FileEntry, RepoIndex, RepoScanner, FolderNode
from src.parsers.base import ASTIndex, ClassDecl, FileAST, BaseParser
from src.parsers.registry import get_parser


@dataclass
class DependencyGraph:
    """File-level import graph: who imports whom."""
    dependencies: dict[str, set[str]]
    dependents: dict[str, set[str]]
    call_graph: dict[str, set[str]] = field(default_factory=dict)
    module_graph: dict[str, set[str]] = field(default_factory=dict)

    @classmethod
    def from_ast(cls, ast: ASTIndex, repo: RepoIndex) -> DependencyGraph:
        deps: dict[str, set[str]] = {p: set() for p in ast.files}
        dents: dict[str, set[str]] = {p: set() for p in ast.files}

        # Build namespace → files map for C# resolution
        namespace_map: dict[str, set[str]] = {}
        for path, fast in ast.files.items():
            if fast.namespace:
                namespace_map.setdefault(fast.namespace, set()).add(path)

        for path, fast in ast.files.items():
            for imp in fast.imports:
                resolved = cls._resolve_import(imp, path, repo, namespace_map)
                if resolved and resolved != path:
                    deps[path].add(resolved)
                    dents.setdefault(resolved, set()).add(path)

        call_graph = cls._build_call_graph(ast)
        module_graph = cls._build_module_graph(deps)

        return cls(
            dependencies=deps, dependents=dents,
            call_graph=call_graph, module_graph=module_graph,
        )

    @staticmethod
    def _build_call_graph(ast: ASTIndex) -> dict[str, set[str]]:
        """Build method-level call graph: 'file:Class.method' → {'ClassB.target', ...}."""
        graph: dict[str, set[str]] = {}
        for path, fast in ast.files.items():
            for cls in fast.classes:
                for m in cls.methods:
                    if not m.calls:
                        continue
                    key = f"{path}:{cls.name}.{m.name}"
                    graph[key] = set(m.calls)
        return graph

    @staticmethod
    def _build_module_graph(file_deps: dict[str, set[str]]) -> dict[str, set[str]]:
        """Group file-level dependencies by top-level directory/namespace."""
        def module_of(p: str) -> str:
            return p.split("/")[0] if "/" in p else "root"

        modules: dict[str, set[str]] = {}
        for source, targets in file_deps.items():
            src_mod = module_of(source)
            for t in targets:
                tgt_mod = module_of(t)
                if src_mod != tgt_mod:
                    modules.setdefault(src_mod, set()).add(tgt_mod)
        return modules

    @staticmethod
    def _resolve_import(import_str: str, source_file: str, repo: RepoIndex,
                        namespace_map: dict[str, set[str]] | None = None) -> str | None:
        source_dir = os.path.dirname(source_file)

        if import_str.startswith("."):
            # Relative import: resolve against source directory
            resolved = os.path.normpath(
                os.path.join(source_dir, import_str)
            ).replace("\\", "/")
            result = DependencyGraph._match_file(resolved, repo)
            if result:
                return result
            # Also try as directory/index
            for ext in (".ts", ".tsx", ".js", ".jsx", ".php", ".dart", ".py"):
                candidate = os.path.join(resolved, "index" + ext).replace("\\", "/")
                if candidate in repo.files:
                    return candidate
        else:
            # Package import: try to resolve in monorepo
            result = DependencyGraph._resolve_package_import(import_str, repo)
            if result:
                return result

            # C++: #include paths (e.g. "STypes.h", "CoreMinimal.h")
            # Must be checked BEFORE C# because file extensions contain dots.
            if import_str.endswith((".h", ".hpp", ".cpp", ".cxx", ".c", ".hxx")):
                result = DependencyGraph._resolve_cpp_import(import_str, source_file, repo)
                if result:
                    return result

            # PHP: namespace import (e.g. "App\Models\Contact")
            if "\\" in import_str:
                result = DependencyGraph._resolve_php_import(import_str, repo)
                if result:
                    return result

            # C#: namespace import (e.g. "Nop.Core.Domain.Customers")
            # Guard: dots present, not a file extension, not @/guid: prefixed
            if ("." in import_str and not import_str.startswith(("@", "guid:"))
                    and not any(import_str.endswith(ext) for ext in (".h", ".hpp", ".cpp", ".cs", ".php", ".ts", ".js", ".vue", ".dart", ".py"))):
                result = DependencyGraph._resolve_csharp_import(import_str, repo, namespace_map)
                if result:
                    return result

        return None

    @staticmethod
    def _match_file(resolved: str, repo: RepoIndex) -> str | None:
        """Try to match *resolved* to an actual file in the repo.
        Strips the existing extension and tries known source extensions,
        so that ``./foo.js`` → ``./foo.ts`` in TypeScript projects.
        """
        if resolved in repo.files:
            return resolved
        base, existing_ext = os.path.splitext(resolved)
        for ext in (".ts", ".tsx", ".js", ".jsx", ".cs", ".php", ".dart", ".py", ".vue", ".cpp", ".h", ".hpp"):
            if base + ext in repo.files:
                return base + ext
        return None

    @staticmethod
    def _match_file_case_insensitive(candidate: str, repo: RepoIndex) -> str | None:
        """Case-insensitive file match for PHP/C# projects where namespace case
        might differ from filesystem case."""
        candidate_lower = candidate.lower()
        for file_path in repo.files:
            if file_path.lower() == candidate_lower:
                return file_path
        return None

    @staticmethod
    def _resolve_package_import(import_str: str, repo: RepoIndex) -> str | None:
        """Resolve a package import (e.g. ``@directus/env``) in a monorepo
        by checking tsconfig paths, package.json workspaces, and directory layout.
        """
        project_path = Path(repo.project_path)

        # 1. Try tsconfig.json compilerOptions.paths
        for tsconfig_name in ("tsconfig.json", "tsconfig.base.json", "tsconfig.build.json"):
            tsconfig = project_path / tsconfig_name
            if tsconfig.exists():
                try:
                    tsdata = json.loads(tsconfig.read_text(encoding="utf-8"))
                    paths = tsdata.get("compilerOptions", {}).get("paths", {})
                    for pattern, targets in paths.items():
                        # pattern like "@directus/*" or "@scope/pkg"
                        prefix = pattern.rstrip("*")
                        if import_str == pattern or (
                            "*" in pattern and import_str.startswith(prefix)
                        ):
                            suffix = import_str[len(prefix):]
                            for t in targets:
                                t = t.replace("/*", "").rstrip("/")
                                resolved = (t + suffix).replace("\\", "/")
                                result = DependencyGraph._match_file(resolved, repo)
                                if result:
                                    return result
                                # Try /index
                                for ext in (".ts", ".tsx", ".js", ".jsx"):
                                    idx = os.path.join(resolved, "index" + ext).replace("\\", "/")
                                    if idx in repo.files:
                                        return idx
                except Exception:
                    pass
                break  # only check first found tsconfig

        # 2. Try package.json workspaces
        pkg_json = project_path / "package.json"
        if pkg_json.exists():
            try:
                pkg = json.loads(pkg_json.read_text(encoding="utf-8"))
                workspaces = pkg.get("workspaces", [])
                if isinstance(workspaces, dict):
                    workspaces = workspaces.get("packages", [])
                for ws_pattern in workspaces:
                    prefix = ws_pattern.rstrip("*")
                    if "/" in import_str:
                        pkg_name = import_str.split("/", 1)[1]
                    else:
                        pkg_name = import_str
                    for subdir in ("src", "lib", ""):
                        candidate_dir = os.path.normpath(
                            os.path.join(prefix, pkg_name, subdir)
                        ).replace("\\", "/") if subdir else os.path.normpath(
                            os.path.join(prefix, pkg_name)
                        ).replace("\\", "/")
                        for ext in (".ts", ".tsx", ".js", ".jsx"):
                            idx = os.path.join(candidate_dir, "index" + ext).replace("\\", "/")
                            if idx in repo.files:
                                return idx
            except Exception:
                pass

        # 3. Derive path from package name: @scope/name → packages/name/src/index.ts
        if "/" in import_str:
            pkg_name = import_str.split("/", 1)[1]
            common_roots = ("packages", "packages/core", "packages/plugins",
                           "packages/providers", "packages/utils", "libs", "src")
            for root in common_roots:
                for subdir in ("src", "lib", ""):
                    base = os.path.join(root, pkg_name) if not subdir else os.path.join(root, pkg_name, subdir)
                    candidate_dir = os.path.normpath(base).replace("\\", "/")
                    for ext in (".ts", ".tsx", ".js", ".jsx"):
                        idx = os.path.join(candidate_dir, "index" + ext).replace("\\", "/")
                        if idx in repo.files:
                            return idx
            # Also try: packages/<name>/package.json → read "name" to match
            for root in common_roots:
                pkg_json_path = project_path / root / pkg_name / "package.json"
                if pkg_json_path.exists():
                    try:
                        pkg_data = json.loads(pkg_json_path.read_text(encoding="utf-8"))
                        if pkg_data.get("name") == import_str:
                            main = pkg_data.get("main", "dist/index.js")
                            source = main.replace("dist/", "src/").replace(".js", ".ts")
                            candidate = os.path.normpath(
                                os.path.join(root, pkg_name, source)
                            ).replace("\\", "/")
                            if candidate in repo.files:
                                return candidate
                    except Exception:
                        pass

        return None

    @staticmethod
    def _resolve_php_import(import_str: str, repo: RepoIndex) -> str | None:
        """Resolve a PHP namespace import (e.g. ``App\\Models\\Contact``) to a file path.

        Uses PSR-4 mappings from composer.json if available, falls back to
        Laravel convention: lowercase first segment, backslash → slash, + .php.
        """
        project_path = Path(repo.project_path)
        composer_json = project_path / "composer.json"
        psr4_map: dict[str, str] = {}
        if composer_json.exists():
            try:
                composer = json.loads(composer_json.read_text(encoding="utf-8"))
                for src_key in ("autoload", "autoload-dev"):
                    autoload = composer.get(src_key, {})
                    for prefix, paths in autoload.get("psr-4", {}).items():
                        if isinstance(paths, list):
                            paths = paths[0] if paths else ""
                        elif not isinstance(paths, str):
                            continue
                        psr4_map[prefix.rstrip("\\")] = paths.rstrip("/") if paths else ""
            except Exception:
                pass

        # Try PSR-4 mapping
        for prefix, base_dir in sorted(psr4_map.items(), key=lambda x: -len(x[0])):
            if import_str.startswith(prefix + "\\") or import_str == prefix:
                suffix = import_str[len(prefix):].lstrip("\\")
                rel_path = suffix.replace("\\", "/") + ".php"
                candidate = os.path.normpath(
                    os.path.join(base_dir, rel_path)
                ).replace("\\", "/")
                if candidate in repo.files:
                    return candidate

        # Fallback: Laravel convention
        parts = import_str.replace("\\", "/").split("/")
        candidate = "/".join(parts) + ".php"
        match = DependencyGraph._match_file_case_insensitive(candidate, repo)
        if match:
            return match

        # Try with lowercase first segment
        if parts:
            parts[0] = parts[0].lower()
        candidate_lower = "/".join(parts) + ".php"
        if candidate_lower != candidate:
            match = DependencyGraph._match_file_case_insensitive(candidate_lower, repo)
            if match:
                return match

        # Try with common base dirs
        for base in ("app", "src", "lib", ""):
            c = os.path.join(base, candidate).replace("\\", "/") if base else candidate
            match = DependencyGraph._match_file_case_insensitive(c, repo)
            if match:
                return match

        return None

    @staticmethod
    def _resolve_csharp_import(import_str: str, repo: RepoIndex,
                               namespace_map: dict[str, set[str]] | None = None) -> str | None:
        """Resolve a C# namespace import (e.g. ``Nop.Core.Domain.Customers``) to files.

        Uses AST namespace declarations first (most accurate), then falls back
        to directory-to-namespace heuristic for projects where directory names
        embed namespace prefixes (e.g. ``Nop.Core/`` dir → ``Nop.Core`` namespace).
        """
        # 1. Exact namespace match from AST data
        if namespace_map and import_str in namespace_map:
            files = namespace_map[import_str]
            return next(iter(files))

        # 2. Prefix match: namespace starts with the import string
        #    e.g. import "CollisionLib" matches namespace "CollisionLib.Editor"
        if namespace_map:
            for ns, files in namespace_map.items():
                if ns.startswith(import_str + ".") or ns == import_str:
                    return next(iter(files))
            # Also try suffix match: namespace is a parent of a known namespace
            # e.g. import "Nop.Core.Domain" matches namespace "Nop.Core.Domain.Customers"
            for ns, files in namespace_map.items():
                if ns.startswith(import_str + "."):
                    return next(iter(files))

        # 3. Directory-based fallback for projects like nopCommerce
        #    where directory names contain dots mapping to namespaces
        dirs: dict[str, str] = {}  # normalized_dir → first .cs file in it
        for file_path in repo.files:
            if file_path.endswith(".cs"):
                d = os.path.dirname(file_path).replace("\\", "/")
                if d not in dirs:
                    dirs[d] = file_path

        for dir_path, cs_file in dirs.items():
            dot_path = dir_path.replace("/", ".")
            if dot_path.endswith("." + import_str) or dot_path == import_str:
                return cs_file
        return None

    @staticmethod
    def _resolve_cpp_import(import_str: str, source_file: str, repo: RepoIndex) -> str | None:
        """Resolve a C++ #include path (e.g. ``STypes.h``) to a file.

        For ``"..."`` includes (project headers): resolve relative to source file,
        then search the entire project for matching filename.
        """
        source_dir = os.path.dirname(source_file)

        # Try relative to source file
        resolved = os.path.normpath(
            os.path.join(source_dir, import_str)
        ).replace("\\", "/")
        if resolved in repo.files:
            return resolved

        # Search project for matching filename
        filename = os.path.basename(import_str)
        for file_path in repo.files:
            if os.path.basename(file_path) == filename:
                return file_path

        return None


@dataclass
class FileInfo:
    entry: FileEntry
    ast: FileAST | None


@dataclass
class ProjectIndex:
    repo: RepoIndex
    ast: ASTIndex
    deps: DependencyGraph

    @classmethod
    def build(cls, config: Config, force: bool = False) -> ProjectIndex:
        scanner = RepoScanner(config)
        repo = scanner.scan()

        ast = ASTIndex()
        for parser_id in config.parsers_needed:
            parser = get_parser(parser_id)
            if parser is None:
                continue
            eligible = [
                p for p, e in repo.files.items()
                if e.ast_eligible and e.language == parser.language
            ]
            if not eligible:
                continue
            result = parser.parse(str(config.project_path), eligible)
            if result.files:
                ast.files.update(result.files)
            elif eligible:
                logger.warning(
                    "Parser %s produced no results for %d eligible files",
                    parser_id, len(eligible),
                )
            ast.errors.extend(result.errors)

        ast.total_classes = sum(len(f.classes) for f in ast.files.values())
        ast.total_methods = sum(
            len(c.methods) for f in ast.files.values() for c in f.classes
        )
        deps = DependencyGraph.from_ast(ast, repo)
        return cls(repo=repo, ast=ast, deps=deps)

    def get_file(self, path: str) -> FileInfo | None:
        entry = self.repo.files.get(path)
        if entry is None:
            return None
        return FileInfo(entry=entry, ast=self.ast.files.get(path))

    def find_files(self, *, language=None, file_type=None, pattern=None) -> list[FileEntry]:
        import fnmatch
        results = list(self.repo.files.values())
        if language:
            results = [e for e in results if e.language == language]
        if file_type:
            results = [e for e in results if e.file_type == file_type]
        if pattern:
            results = [e for e in results if fnmatch.fnmatch(e.path, pattern)]
        return results

    def find_classes(self, *, name=None, base_type=None, attribute=None, language=None):
        results = []
        for path, fast in self.ast.files.items():
            if language and fast.language != language:
                continue
            for cls in fast.classes:
                if name and name.lower() not in cls.name.lower():
                    continue
                if base_type and base_type not in cls.base_types + cls.interfaces:
                    continue
                if attribute and attribute not in cls.attributes:
                    continue
                results.append((path, cls))
        return results

    def find_symbols(self, name: str) -> list[dict]:
        """Search for classes, methods, and functions by name.

        Returns list of dicts with keys: type ('class'|'method'|'function'),
        name, path, and contextual info (class_name for methods, params for functions/methods).
        """
        results: list[dict] = []
        name_lower = name.lower()

        for path, fast in self.ast.files.items():
            for cls in fast.classes:
                if name_lower in cls.name.lower():
                    results.append({
                        "type": cls.class_type or "class",
                        "name": cls.name,
                        "path": path,
                        "methods": cls.methods[:5],
                    })
                for m in cls.methods:
                    if name_lower in m.name.lower():
                        results.append({
                            "type": "method",
                            "name": m.name,
                            "path": path,
                            "class_name": cls.name,
                            "return_type": m.return_type or "void",
                            "parameters": m.parameters,
                            "modifiers": m.modifiers,
                        })
            for fn in fast.functions:
                if name_lower in fn.name.lower():
                    results.append({
                        "type": "function",
                        "name": fn.name,
                        "path": path,
                        "return_type": fn.return_type or "void",
                        "parameters": fn.parameters,
                        "modifiers": fn.modifiers,
                    })

        # Deduplicate: prefer exact matches, then prefix matches
        results.sort(key=lambda r: (
            0 if r["name"].lower() == name_lower else 1,
            0 if r["name"].lower().startswith(name_lower) else 1,
            r["name"].lower(),
        ))
        return results

    def get_dependencies(self, path: str) -> list[str]:
        return sorted(self.deps.dependencies.get(path, set()))

    def get_dependents(self, path: str) -> list[str]:
        return sorted(self.deps.dependents.get(path, set()))

    def _page_rank(self, paths: list[str], steps: int = 3) -> dict[str, float]:
        """Simple PageRank-like scoring: score flows from a file to its neighbors."""
        scores: dict[str, float] = {}
        for p in paths:
            scores[p] = 1.0

        for _ in range(steps):
            new_scores: dict[str, float] = {}
            for node, score in scores.items():
                neighbors = self.deps.dependencies.get(node, set()) | self.deps.dependents.get(node, set())
                if not neighbors:
                    new_scores[node] = new_scores.get(node, 0) + score
                    continue
                share = score * 0.85 / len(neighbors)
                for nb in neighbors:
                    new_scores[nb] = new_scores.get(nb, 0) + share
                new_scores[node] = new_scores.get(node, 0) + score * 0.15
            scores = new_scores

        return scores

    ENTITY_PRIORITY = {
        "controller": 10, "handler": 9, "service": 8, "repository": 7,
        "entity": 6, "dto": 5, "validator": 5, "middleware": 4,
        "page": 6, "widget": 5, "composable": 5, "store": 4,
        "system": 8, "prefab": 4,
    }

    def _guess_entity_type(self, path: str) -> str:
        """Guess entity type from file path and class names."""
        import fnmatch
        lower = path.lower()
        name = Path(path).stem.lower()

        for etype in self.ENTITY_PRIORITY:
            if etype in name or etype in lower:
                return etype
        if fnmatch.fnmatch(name, "*controller*"): return "controller"
        if fnmatch.fnmatch(name, "*service*"): return "service"
        if fnmatch.fnmatch(name, "*repository*"): return "repository"
        if fnmatch.fnmatch(name, "*handler*"): return "handler"
        return "unknown"

    def rank_files(self, paths: list[str], center_path: str = "") -> list[tuple[str, float]]:
        """Rank files by relevance: dependency distance, centrality, entity type priority.

        Higher score = more relevant. Use for context ranking to prioritize what to include.
        """
        if not paths:
            return []

        # Only rank files that actually exist in the repo
        known = [p for p in paths if p in self.repo.files]
        if not known:
            return []

        center = center_path if center_path and center_path in self.repo.files else ""
        start = [center] if center else known[:10]
        scores = self._page_rank(start)

        # Boost by entity type priority
        for p in list(scores.keys()):
            etype = self._guess_entity_type(p)
            boost = self.ENTITY_PRIORITY.get(etype, 1) / 5.0
            scores[p] *= (1.0 + boost)

        # Sort and return — only include known paths
        ranked = [(p, round(scores.get(p, 0), 3)) for p in known if p in scores]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked

    def find_similar(self, class_name: str, n: int = 10) -> list[tuple[str, str, list[str]]]:
        """Find classes similar to the given one: same base type, interfaces, or naming.

        Returns list of (file_path, class_name, [reason, ...]).
        """
        import fnmatch

        # Find the target class first
        target: tuple[str, ClassDecl] | None = None
        for path, cls in self.find_classes(name=class_name):
            if cls.name.lower() == class_name.lower():
                target = (path, cls)
                break
        if not target:
            return []

        t_path, t_cls = target
        scored: list[tuple[str, str, list[str], int]] = []

        for path, cls in self.find_classes():
            if cls.name.lower() == class_name.lower():
                continue
            reasons: list[str] = []
            score = 0

            # Same base type
            common_base = set(t_cls.base_types) & set(cls.base_types)
            if common_base:
                reasons.append(f"extends {', '.join(common_base)}")
                score += len(common_base) * 3

            # Same interface
            common_iface = set(t_cls.interfaces) & set(cls.interfaces)
            if common_iface:
                reasons.append(f"implements {', '.join(common_iface)}")
                score += len(common_iface) * 2

            # Same attributes/decorators
            common_attr = set(t_cls.attributes) & set(cls.attributes)
            if common_attr:
                reasons.append(f"attribute {', '.join(common_attr)}")
                score += len(common_attr) * 2

            # Similar name (suffix match)
            t_name = t_cls.name.lower()
            o_name = cls.name.lower()
            if t_name != o_name:
                # Check suffix overlap
                for suffix in ["controller", "service", "repository", "handler", "dto",
                              "entity", "page", "widget", "composable", "store", "system"]:
                    if t_name.endswith(suffix) and o_name.endswith(suffix):
                        reasons.append(f"suffix -{suffix}")
                        score += 1
                        break

            if reasons:
                scored.append((path, cls.name, reasons, score))

        scored.sort(key=lambda x: x[3], reverse=True)
        return [(p, n, r) for p, n, r, _ in scored[:n]]

    def compact_source(self, path: str) -> str | None:
        """Return a compact version of a source file: signatures only, no bodies, no comments."""
        entry = self.repo.files.get(path)
        if entry is None:
            return None
        full_path = Path(self.repo.project_path) / path
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        import re
        # Strip single-line comments
        content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)
        # Strip multi-line comments
        content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
        # Strip Python-style comments
        content = re.sub(r"#.*$", "", content, flags=re.MULTILINE)
        # Strip excessive blank lines
        content = re.sub(r"\n{3,}", "\n\n", content)

        # Extract signatures: method/function declarations with their first line
        sig_pattern = re.compile(
            r"((?:public|private|protected|internal|static|virtual|override|abstract|async|export|"
            r"function|def|func|void|int|string|bool|var|let|const|class|interface|enum|struct)\s+)*"
            r"(?:[\w<>\[\],\s]+\s+)?\w+\s*\([^)]*\)",
        )

        signatures = []
        for m in sig_pattern.finditer(content):
            line = m.group().strip()
            if len(line) > 200:
                line = line[:197] + "..."
            signatures.append(line)

        if not signatures:
            return None

        return f"Compact view of {path} ({len(signatures)} signatures):\n" + "\n".join(
            f"  {s}" for s in signatures[:80]
        )

    def classify_entities(self, language: str = "") -> dict[str, list[str]]:
        """Classify source files into entity types (controller, service, etc.).

        Uses heuristics: folder path, class name suffix, base types from AST.
        Returns {entity_type: [file_path, ...]}.
        """
        result: dict[str, list[str]] = {}

        for path, fast in self.ast.files.items():
            if language and fast.language != language:
                continue
            for cls in fast.classes:
                etype = self._classify_single_entity(path, cls)
                result.setdefault(etype, []).append(path)

        # Also classify files without AST (by path only)
        for path, entry in self.repo.files.items():
            if entry.file_type not in ("source", "test"):
                continue
            if path in self.ast.files:
                continue
            etype = self._guess_entity_type(path)
            result.setdefault(etype, []).append(path)

        return result

    def _classify_single_entity(self, path: str, cls: ClassDecl) -> str:
        """Classify a single class into entity type based on AST data + path."""
        name_lower = cls.name.lower()
        path_lower = path.lower()

        # Base type signals (strongest)
        for base in cls.base_types + cls.interfaces:
            if not base:
                continue
            b = base.lower()
            if "monobehaviour" in b:
                return "monobehaviour"
            if "scriptableobject" in b:
                return "scriptableobject"
            if "systembase" in b or "isystem" in b:
                return "system"
            if "controller" in b or "controllerbase" in b or "apicontroller" in b:
                return "controller"
            if "irepository" in b or "repository" in b:
                return "repository"
            if "validator" in b or "abstractvalidator" in b:
                return "validator"
            if "irequesthandler" in b or "requesthandler" in b:
                return "handler"
            if "page" in b or "contentpage" in b:
                return "page"
            if "store" in b:
                return "store"

        # Class name suffixes
        if name_lower.endswith("controller"):
            return "controller"
        if name_lower.endswith("service"):
            return "service"
        if name_lower.endswith("repository") or name_lower.endswith("repo"):
            return "repository"
        if name_lower.endswith("dto") or name_lower.endswith("model") or name_lower.endswith("viewmodel"):
            return "dto"
        if name_lower.endswith("entity") or name_lower.endswith("domain"):
            return "entity"
        if name_lower.endswith("handler"):
            return "handler"
        if name_lower.endswith("validator"):
            return "validator"
        if name_lower.endswith("page"):
            return "page"
        if name_lower.endswith("widget") or name_lower.endswith("component"):
            return "widget"
        if name_lower.endswith("composable") or name_lower.startswith("use"):
            return "composable"
        if name_lower.endswith("store"):
            return "store"
        if name_lower.endswith("route") or name_lower.endswith("router"):
            return "route"
        if name_lower.endswith("system"):
            return "system"
        if "prefab" in name_lower:
            return "prefab"
        if name_lower.endswith("middleware"):
            return "middleware"
        if name_lower.endswith("factory"):
            return "factory"
        if name_lower.endswith("manager"):
            return "service"
        if name_lower.endswith("provider"):
            return "service"

        # Folder-based fallback
        return self._guess_entity_type(path)

    def summarize(self) -> str:
        lines = [
            f"Project: {self.repo.project_path}",
            f"Files: {self.repo.file_count} total",
        ]
        for lang, files in sorted(self.repo.files_by_language.items()):
            if files:
                lines.append(f"  {lang}: {len(files)} files")
        lines.append(f"Classes: {self.ast.total_classes}")
        lines.append(f"Methods: {self.ast.total_methods}")
        lines.append(f"Dependency edges: {sum(len(v) for v in self.deps.dependencies.values())}")
        lines.append("")
        lines.append("Structure:")
        lines.append(RepoScanner.print_tree(self.repo.file_tree, max_depth=3))
        return "\n".join(lines)

    @classmethod
    def load(cls, db_path: str) -> ProjectIndex | None:
        """Restore index from SQLite cache. Returns None if not found or corrupted."""
        if not Path(db_path).exists():
            return None

        db = sqlite3.connect(db_path)
        try:
            row = db.execute("SELECT value FROM meta WHERE key='project_path'").fetchone()
            if not row:
                return None
            project_path = row[0]

            # files
            files: dict[str, FileEntry] = {}
            for r in db.execute("SELECT * FROM files"):
                files[r[0]] = FileEntry(
                    path=r[0], size=r[1], mtime=r[2], extension=r[3],
                    language=r[4], file_type=r[5], is_test=bool(r[6]), is_doc=bool(r[7]),
                )

            # repo index
            root = FolderNode(name=Path(project_path).name, path="")
            for rel_path, entry in files.items():
                _add_to_tree_static(root, rel_path, entry)
            by_lang, by_type = _group_files(files)
            repo = RepoIndex(
                project_path=project_path, files=files, file_tree=root,
                file_count=len(files), files_by_language=by_lang, files_by_type=by_type,
            )

            # methods (before classes)
            from src.parsers.base import MethodDecl, Parameter
            methods_by_cls: dict[tuple[str, str], list[MethodDecl]] = {}
            for r in db.execute("SELECT * FROM methods"):
                params = [Parameter(**p) for p in json.loads(r[5])]
                methods_by_cls.setdefault((r[0], r[1]), []).append(
                    MethodDecl(name=r[2], return_type=r[3], parameters=params,
                               modifiers=json.loads(r[6]), loc=r[7]),
                )

            # classes
            from src.parsers.base import ClassDecl, FileAST
            fasts: dict[str, FileAST] = {}
            for r in db.execute("SELECT * FROM classes"):
                path, name = r[0], r[1]
                if path not in fasts:
                    fasts[path] = FileAST(path=path, language=files[path].language)
                fasts[path].classes.append(ClassDecl(
                    name=name, class_type=r[3],
                    base_types=json.loads(r[4]), interfaces=json.loads(r[5]),
                    attributes=json.loads(r[6]), loc=r[7],
                    methods=methods_by_cls.get((path, name), []),
                ))

            # restore calls into methods
            for r in db.execute("SELECT * FROM calls"):
                path, full_method, call = r[0], r[1], r[2]
                if path not in fasts:
                    continue
                parts = full_method.split(".", 1)
                if len(parts) != 2:
                    continue
                cls_name, method_name = parts
                for cls in fasts[path].classes:
                    if cls.name == cls_name:
                        for m in cls.methods:
                            if m.name == method_name and call not in m.calls:
                                m.calls.append(call)
                        break

            ast = ASTIndex(files=fasts)
            ast.total_classes = sum(len(f.classes) for f in fasts.values())
            ast.total_methods = sum(
                len(c.methods) for f in fasts.values() for c in f.classes
            )

            # dependency graph
            deps: dict[str, set[str]] = {}
            dents: dict[str, set[str]] = {}
            for r in db.execute("SELECT * FROM deps"):
                deps.setdefault(r[0], set()).add(r[1])
                dents.setdefault(r[1], set()).add(r[0])
            dep_graph = DependencyGraph(dependencies=deps, dependents=dents)

            return cls(repo=repo, ast=ast, deps=dep_graph)

        except Exception:
            return None
        finally:
            db.close()

    @classmethod
    def load_or_build(cls, config: Config, force: bool = False) -> ProjectIndex:
        """Load from cache if fresh, otherwise full build + save."""
        db_path = str(config.project_path / ".ai-context.db")

        if not force:
            cached = cls.load(db_path)
            if cached is not None:
                scanner = RepoScanner(config)
                new, modified, fresh_repo = scanner.incremental_scan(cached.repo)
                if not new and not modified:
                    return cached
                return cls._incremental_update(cached, fresh_repo, new, modified, config)

        index = cls.build(config)
        index.save(db_path)
        return index

    @classmethod
    def _incremental_update(cls, existing: ProjectIndex, fresh_repo: RepoIndex,
                            new_files: list[str], modified_files: list[str],
                            config: Config) -> ProjectIndex:
        """Reparse only changed files, rebuild dependency graph."""
        changed = set(new_files) | set(modified_files)

        for path in list(existing.ast.files.keys()):
            if path not in fresh_repo.files:
                del existing.ast.files[path]

        for parser_id in config.parsers_needed:
            parser = get_parser(parser_id)
            if parser is None:
                continue
            eligible = [
                p for p in changed
                if p in fresh_repo.files
                and fresh_repo.files[p].ast_eligible
                and fresh_repo.files[p].language == parser.language
            ]
            if not eligible:
                continue
            result = parser.parse(str(config.project_path), eligible)
            for p in eligible:
                existing.ast.files.pop(p, None)
            existing.ast.files.update(result.files)

        existing.repo = fresh_repo
        existing.ast.total_classes = sum(len(f.classes) for f in existing.ast.files.values())
        existing.ast.total_methods = sum(
            len(c.methods) for f in existing.ast.files.values() for c in f.classes
        )
        existing.deps = DependencyGraph.from_ast(existing.ast, fresh_repo)
        return existing

    def save(self, db_path: str) -> None:
        db = sqlite3.connect(db_path)
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript("""
        CREATE TABLE IF NOT EXISTS meta (
              key TEXT PRIMARY KEY,
              value TEXT
          );
          CREATE TABLE IF NOT EXISTS files (
              path TEXT PRIMARY KEY,
              size INTEGER,
              mtime REAL,
              extension TEXT,
              language TEXT,
              file_type TEXT,
              is_test INTEGER,
              is_doc INTEGER
          );
          CREATE TABLE IF NOT EXISTS classes (
              path TEXT,
              name TEXT,
              class_type TEXT,
              base_types TEXT,
              interfaces TEXT,
              attributes TEXT,
              loc INTEGER,
              PRIMARY KEY (path, name)
          );
          CREATE TABLE IF NOT EXISTS methods (
              path TEXT,
              class_name TEXT,
              name TEXT,
              return_type TEXT,
              parameters TEXT,
              modifiers TEXT,
              loc INTEGER,
              PRIMARY KEY (path, class_name, name)
          );
          CREATE TABLE IF NOT EXISTS deps (
              source TEXT,
              target TEXT,
              PRIMARY KEY (source, target)
          );
          CREATE TABLE IF NOT EXISTS calls (
              source_path TEXT,
              source_method TEXT,
              target_method TEXT,
              PRIMARY KEY (source_path, source_method, target_method)
          );
        """)
        db.execute("DELETE FROM meta")
        db.execute("DELETE FROM files")
        db.execute("DELETE FROM classes")
        db.execute("DELETE FROM methods")
        db.execute("DELETE FROM deps")
        db.execute("DELETE FROM calls")

        db.execute("INSERT INTO meta VALUES ('project_path', ?)", (self.repo.project_path,))
        db.execute("INSERT INTO meta VALUES ('scan_time', ?)", (str(time.time()),))

        db.executemany(
            "INSERT INTO files VALUES (?,?,?,?,?,?,?,?)",
            [(e.path, e.size, e.mtime, e.extension, e.language, e.file_type,
              int(e.is_test), int(e.is_doc)) for e in self.repo.files.values()],
        )

        for path, fast in self.ast.files.items():
            for cls in fast.classes:
                db.execute(
                    "INSERT OR REPLACE INTO classes VALUES (?,?,?,?,?,?,?)",
                    (path, cls.name, cls.class_type,
                     json.dumps(cls.base_types), json.dumps(cls.interfaces),
                     json.dumps(cls.attributes), cls.loc),
                )
                for m in cls.methods:
                    params = json.dumps([{"name": p.name, "type": p.type,
                                          "default": p.default_value} for p in m.parameters])
                    db.execute(
                        "INSERT OR IGNORE INTO methods VALUES (?,?,?,?,?,?,?)",
                        (path, cls.name, m.name, m.return_type, params,
                         json.dumps(m.modifiers), m.loc),
                    )

        db.executemany(
            "INSERT INTO deps VALUES (?,?)",
            [(s, t) for s, targets in self.deps.dependencies.items() for t in targets],
        )

        for path, fast in self.ast.files.items():
            for cls in fast.classes:
                for m in cls.methods:
                    for call in m.calls:
                        db.execute(
                            "INSERT OR IGNORE INTO calls VALUES (?,?,?)",
                            (path, f"{cls.name}.{m.name}", call),
                        )

        db.commit()
        db.close()


def _add_to_tree_static(node: FolderNode, rel_path: str, entry: FileEntry) -> None:
    """Build FolderNode tree from flat file paths (used during load)."""
    parts = rel_path.split("/")
    current = node
    for i, part in enumerate(parts[:-1]):
        child = None
        for c in current.children:
            if c.name == part:
                child = c
                break
        if child is None:
            child = FolderNode(name=part, path="/".join(parts[:i + 1]))
            current.children.append(child)
        current = child
    current.files.append(entry)


def _group_files(files: dict[str, FileEntry]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Build files_by_language and files_by_type from flat file dict."""
    by_lang: dict[str, list[str]] = {}
    by_type: dict[str, list[str]] = {}
    for path, entry in files.items():
        by_lang.setdefault(entry.language, []).append(path)
        by_type.setdefault(entry.file_type, []).append(path)
    return by_lang, by_type


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Estimate token count for a text string using tiktoken."""
    import tiktoken
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

