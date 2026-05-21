"""Load and merge .ai-context.yml configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


DEFAULT_EXCLUDE = [
    "node_modules/**",
    ".git/**",
    "bin/**",
    "obj/**",
    "Library/**",
    "Temp/**",
    "dist/**",
    "build/**",
    "generated/**",
    "__pycache__/**",
    ".venv/**",
    "vendor/**",
    ".next/**",
    ".nuxt/**",
    "coverage/**",
    "*.min.js",
    "*.generated.*",
    "*.g.cs",
    "*.g.i.cs",
    "*.designer.cs",
    # UE-specific
    "Binaries/**",
    "Intermediate/**",
    "DerivedDataCache/**",
    "Saved/**",
    ".vs/**",
    # Security
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.pfx",
    "*.p12",
    "*credentials*",
    "*credential*",
    "*secret*",
    "*private_key*",
    "*private-key*",
    "**/secrets/**",
    "**/Secrets/**",
]

DEFAULT_CONFIG: dict[str, Any] = {
    "architecture": {"auto_detect": True},
    "indexing": {"exclude": DEFAULT_EXCLUDE},
    "context": {
        "max_tokens": 120000,
        "agent_token_budget": 30000,
        "max_steps": 12,
        "include_tests": True,
        "include_docs": True,
    },
    "similarity": {"enabled": True},
    "vector_search": {"enabled": False},
    "model": {
        "provider": "deepseek",
        "name": "deepseek-chat"
    }
}

PROJECT_MARKERS = {
    "aspnet": {
        "extensions": [".csproj", ".sln"],
        "label": "ASP.NET Core",
        "parser": "csharp",
    },
    "laravel": {
        "files": ["composer.json"],
        "label": "Laravel / PHP",
        "parser": "php",
        "check_deps": ["laravel/framework"],
    },
    "vue": {
        "files": ["package.json"],
        "label": "Vue.js",
        "parser": "typescript",
        "check_deps": ["vue"],
    },
    "node": {
        "files": ["package.json"],
        "label": "Node.js / TypeScript",
        "parser": "typescript",
        "exclude_deps": ["vue"],
    },
    "flutter": {
        "files": ["pubspec.yaml"],
        "label": "Flutter / Dart",
        "parser": "dart",
    },
    "unity": {
        "files": ["Assets"],
        "label": "Unity",
        "parser": "unity",
        "check_files": ["*.unity", "*.meta"],
    },
    "ue": {
        "extensions": [".uproject"],
        "label": "Unreal Engine",
        "parser": "cpp",
    },
}

# Files/directories that signal a directory is a standalone project root.
# When walking for auto-detection, we stop descending into these.
# Strong project-root markers — a directory with any of these is a standalone
# project and should not be descended into during auto-detection walks.
# Note: package.json, composer.json, pubspec.yaml are intentionally NOT here —
# they commonly live in polyglot subdirectories (e.g. rustdesk/flutter/pubspec.yaml).
_SUBPROJECT_MARKERS = frozenset({
    ".git", ".ai-context.yml", "pyproject.toml", "Cargo.toml",
    "CLAUDE.md", "AGENTS.md", ".uproject",
})


@dataclass
class ProjectType:
    type_id: str
    label: str
    parser: str


@dataclass
class Config:
    project_path: Path
    config_path: Path | None = None

    architecture_auto_detect: bool = True
    index_exclude: list[str] = field(default_factory=lambda: DEFAULT_EXCLUDE.copy())
    max_tokens: int = 120000
    agent_token_budget: int = 30000
    max_steps: int = 12
    include_tests: bool = True
    include_docs: bool = True
    similarity_enabled: bool = True
    vector_search_enabled: bool = False
    model_provider: str = "deepseek"
    model_name: str = "deepseek-chat"

    project_types: list[ProjectType] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def has_csharp(self) -> bool:
        return any(p.parser == "csharp" for p in self.project_types)

    @property
    def has_unity(self) -> bool:
        return any(p.parser == "unity" for p in self.project_types)

    @property
    def parsers_needed(self) -> list[str]:
        return list({p.parser for p in self.project_types})


def _merge_config(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            base[key] = _merge_config(base[key], value)
        else:
            base[key] = value
    return base


def load_config(
    project_path: str | Path,
    config_path: str | Path | None = None,
) -> Config:
    project_path = Path(project_path).resolve()
    if not project_path.is_dir():
        raise ValueError(f"Project path is not a directory: {project_path}")

    config = Config(project_path=project_path)
    merged = {"architecture": {}, "indexing": {}, "context": {}, "similarity": {}, "vector_search": {}, "model": {}}
    merged.update({"architecture": DEFAULT_CONFIG["architecture"].copy()})
    merged.update({"indexing": DEFAULT_CONFIG["indexing"].copy()})
    merged.update({"context": DEFAULT_CONFIG["context"].copy()})
    merged.update({"similarity": DEFAULT_CONFIG["similarity"].copy()})
    merged.update({"vector_search": DEFAULT_CONFIG["vector_search"].copy()})
    merged.update({"model": DEFAULT_CONFIG["model"].copy()})

    # Load user config
    if config_path:
        user_config_path = Path(config_path)
    else:
        user_config_path = project_path / ".ai-context.yml"

    if user_config_path.exists():
        with open(user_config_path, encoding="utf-8") as f:
            user_data = yaml.safe_load(f) or {}
        merged = _merge_config(merged, user_data)
        config.config_path = user_config_path

    # Apply to config object
    config.architecture_auto_detect = merged["architecture"].get("auto_detect", True)
    config.index_exclude = merged["indexing"].get("exclude", DEFAULT_EXCLUDE)
    config.max_tokens = merged["context"].get("max_tokens", 120000)
    config.agent_token_budget = merged["context"].get("agent_token_budget", 30000)
    config.max_steps = merged["context"].get("max_steps", 12)
    config.include_tests = merged["context"].get("include_tests", True)
    config.include_docs = merged["context"].get("include_docs", True)
    config.similarity_enabled = merged["similarity"].get("enabled", True)
    config.vector_search_enabled = merged["vector_search"].get("enabled", False)
    config.raw = merged
    config.model_provider = merged["model"].get("provider", "deepseek")
    config.model_name = merged["model"].get("name", "deepseek-chat")
    # Detect project types
    config.project_types = _detect_project_types(project_path)

    return config


def _is_subproject_root(dir_path: Path) -> bool:
    """Return True if *dir_path* has its own project markers and should be treated
    as an independent project (stop boundary for auto-detection walks)."""
    try:
        children = {p.name for p in dir_path.iterdir()}
    except OSError:
        return True  # can't read — treat as boundary for safety

    # File/directory markers (e.g. .git, package.json, pyproject.toml)
    if children & _SUBPROJECT_MARKERS:
        return True

    # Structural markers — directory looks like a known project type
    if "Assets" in children:
        assets = dir_path / "Assets"
        if assets.is_dir():
            if any(assets.glob("*.unity")) or any(assets.glob("*.meta")):
                return True

    return False


def _walk_project_dirs(root: Path, max_depth: int = 5) -> list[Path]:
    """Walk directories up to *max_depth*, stopping at sub-project boundaries.
    Returns directories that belong to this project: *root* plus any descendant
    that is NOT itself a sub-project root."""
    dirs: list[Path] = [root]
    todo: list[tuple[Path, int]] = [(root, 0)]

    while todo:
        current, depth = todo.pop()
        if depth >= max_depth:
            continue
        try:
            for child in sorted(current.iterdir()):
                if not child.is_dir() or child.name.startswith("."):
                    continue
                if _is_subproject_root(child):
                    continue  # foreign project — skip entirely
                dirs.append(child)
                todo.append((child, depth + 1))
        except OSError:
            continue
    return dirs


def _detect_project_types(project_path: Path) -> list[ProjectType]:
    detected: list[ProjectType] = []

    # Unreal Engine: .uproject files (up to 2 levels, common UE layout)
    uproject_files = list(project_path.glob("*.uproject")) + list(project_path.glob("*/*.uproject"))
    if uproject_files:
        detected.append(ProjectType("ue", "Unreal Engine", "cpp"))
        return detected  # UE projects are self-contained — don't mix with others

    # Walk directories to find nested project markers, stopping at sub-project boundaries
    walk_dirs = _walk_project_dirs(project_path)

    # ASP.NET: .csproj or .sln (only in visited directories, not deeper)
    if not any(p.parser == "cpp" for p in detected):
        csproj_files: list[Path] = []
        for d in walk_dirs:
            csproj_files.extend(d.glob("*.csproj"))
            csproj_files.extend(d.glob("*.sln"))
        if csproj_files:
            detected.append(ProjectType("aspnet", "ASP.NET Core", "csharp"))

    # Unity: check visited directories for Assets/
    for d in walk_dirs:
        assets_dir = d / "Assets"
        if assets_dir.is_dir():
            has_meta = any(assets_dir.glob("*.meta"))
            has_unity = any(assets_dir.glob("*.unity"))
            if has_meta or has_unity:
                detected.append(ProjectType("unity", "Unity", "unity"))
                if not any(p.parser == "csharp" for p in detected):
                    detected.append(ProjectType("aspnet", "ASP.NET Core", "csharp"))
                break

    # PHP / Laravel: check visited directories for composer.json
    for d in walk_dirs:
        composer_json = d / "composer.json"
        if composer_json.exists():
            try:
                import json
                with open(composer_json) as f:
                    composer_data = json.load(f)
                deps = {**composer_data.get("require", {}), **composer_data.get("require-dev", {})}
                if "laravel/framework" in deps:
                    detected.append(ProjectType("laravel", "Laravel / PHP", "php"))
                else:
                    detected.append(ProjectType("php", "PHP", "php"))
            except Exception:
                detected.append(ProjectType("php", "PHP", "php"))
            break

    # Node / Vue / TypeScript: check visited directories for package.json
    for d in walk_dirs:
        package_json = d / "package.json"
        if package_json.exists():
            try:
                import json
                with open(package_json) as f:
                    pkg = json.load(f)
                all_deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "vue" in all_deps:
                    detected.append(ProjectType("vue", "Vue.js", "typescript"))
                else:
                    detected.append(ProjectType("node", "Node.js / TypeScript", "typescript"))
            except Exception:
                detected.append(ProjectType("node", "Node.js / TypeScript", "typescript"))
            break

    # Flutter / Dart: check visited directories for pubspec.yaml
    pubspec = project_path / "pubspec.yaml"
    if not pubspec.exists():
        for d in walk_dirs:
            candidate = d / "pubspec.yaml"
            if candidate.exists():
                pubspec = candidate
                break
    if pubspec.exists():
        detected.append(ProjectType("flutter", "Flutter / Dart", "dart"))

    return detected


def load_default_config_for_test(project_path: str | Path = ".") -> Config:
    """Create a default config for testing without a real project."""
    config = Config(project_path=Path(project_path).resolve())
    config.project_types = [ProjectType("aspnet", "ASP.NET Core", "csharp")]
    return config
