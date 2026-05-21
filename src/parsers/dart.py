"""Dart parser — calls Dart Analyzer via subprocess."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from pathlib import Path

from src.parsers.base import (
    ASTIndex,
    BaseParser,
    ClassDecl,
    ConstructorDecl,
    FileAST,
    FunctionDecl,
    MethodDecl,
    Parameter,
    ParseError,
    PropertyDecl,
    extract_calls,
)

logger = logging.getLogger(__name__)

DART_ANALYZER_SCRIPT = (
    Path(__file__).parent.parent.parent / "parsers" / "dart-analyzer" / "analyze.dart"
).resolve()


def _find_dart_exe() -> str:
    """Return the best available dart executable path (or 'dart' if in PATH)."""
    try:
        result = subprocess.run(
            ["dart", "--version"], capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return "dart"
    except FileNotFoundError:
        pass

    import glob as _glob
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        winget_root = Path(local_appdata) / "Microsoft" / "WinGet" / "Packages"
        if winget_root.is_dir():
            pattern = str(winget_root / "Google.DartSDK*" / "dart-sdk" / "bin" / "dart.exe")
            matches = _glob.glob(pattern)
            if matches:
                return matches[0]

    return "dart"


class DartParser(BaseParser):
    language = "dart"
    required_tools = ["dart"]

    def check_available(self) -> bool:
        try:
            exe = _find_dart_exe()
            result = subprocess.run(
                [exe, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def parse(self, project_path: str, files: list[str] | None = None) -> ASTIndex:
        project_path = Path(project_path).resolve()

        if not DART_ANALYZER_SCRIPT.exists():
            logger.warning(f"Dart analyzer not found at {DART_ANALYZER_SCRIPT}, using fallback")
            return self._parse_fallback(project_path, files)

        cmd = [_find_dart_exe(), "run", str(DART_ANALYZER_SCRIPT), str(project_path)]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True,
                timeout=120,
            )
            if result.returncode != 0:
                logger.warning("Dart analyzer failed, using regex fallback: %s", result.stderr[:200])
                return self._parse_fallback(project_path, files)
            return _parse_dart_output(result.stdout)
        except subprocess.TimeoutExpired:
            logger.warning("Dart analyzer timed out, using regex fallback")
            return self._parse_fallback(project_path, files)
        except FileNotFoundError:
            logger.warning("dart not found, using regex fallback")
            return self._parse_fallback(project_path, files)

    def _parse_fallback(self, project_path: Path, files: list[str] | None = None) -> ASTIndex:
        """Regex-based fallback for Dart files."""
        index = ASTIndex()

        for file_path_str in (files or []):
            full_path = (project_path / file_path_str).resolve()
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            fast = FileAST(path=file_path_str, language="dart")

            try:
                # Imports
                for m in re.finditer(
                    r"import\s+['\"]([^'\"]+)['\"]", content
                ):
                    fast.imports.append(m.group(1))
                for m in re.finditer(
                    r"export\s+['\"]([^'\"]+)['\"]", content
                ):
                    fast.imports.append(m.group(1))
                # part directives
                for m in re.finditer(r"part\s+['\"]([^'\"]+)['\"]", content):
                    fast.imports.append(m.group(1))

                # Classes, mixins, enums, extensions
                for m in re.finditer(
                    r"(?:@(\w+)\s*\n\s*)*"
                    r"(?:abstract\s+)?"
                    r"(class|mixin|enum|extension)\s+(\w+)",
                    content,
                ):
                    cls = ClassDecl(name=m.group(3), class_type=m.group(2))

                    # extends/implements/with
                    body_start = content.find("{", m.end())
                    header = content[m.end():body_start] if body_start > 0 else ""
                    extends_match = re.search(r"extends\s+(\w+)", header)
                    if extends_match:
                        cls.base_types.append(extends_match.group(1))
                    impl_match = re.search(r"implements\s+([\w,\s]+?)(?:\{|with|$)", header)
                    if impl_match:
                        cls.interfaces = [
                            i.strip() for i in impl_match.group(1).split(",")
                        ]
                    with_match = re.search(r"with\s+([\w,\s]+?)(?:\{|implements|$)", header)
                    if with_match:
                        for mxn in with_match.group(1).split(","):
                            cls.interfaces.append(mxn.strip())

                    # Methods
                    chunk = content[m.end():m.end() + 5000]
                    chunk_start = m.end()
                    for mm in re.finditer(
                        r"(?:@(\w+)\s*\n\s*)*"
                        r"((?:static|const|final|\s)+)?"
                        r"(?:([\w<>,\s]+)\s+)?"
                        r"(\w+)\s*\(([^)]*)\)",
                        chunk,
                    ):
                        modifiers_str = (mm.group(2) or "").strip()
                        body_chunk = content[chunk_start + mm.end():chunk_start + mm.end() + 2000]
                        method = MethodDecl(
                            name=mm.group(4),
                            return_type=mm.group(3).strip() if mm.group(3) else None,
                            modifiers=[x for x in modifiers_str.split() if x] if modifiers_str else [],
                            calls=extract_calls(body_chunk),
                        )
                        params_str = mm.group(5)
                        if params_str.strip():
                            for p in params_str.split(","):
                                p = p.strip()
                                if " " in p:
                                    parts = p.split()
                                    method.parameters.append(
                                        Parameter(name=parts[-1], type=" ".join(parts[:-1]))
                                    )
                        cls.methods.append(method)

                    fast.classes.append(cls)

                # Top-level functions
                for m in re.finditer(
                    r"(?:@(\w+)\s*\n\s*)*"
                    r"(?:([\w<>,\s]+)\s+)?"
                    r"(\w+)\s*\(([^)]*)\)\s*(?:async\s*)?\{",
                    content,
                ):
                    # Skip class methods (they are inside a class context)
                    func = FunctionDecl(name=m.group(3))
                    for p in m.group(4).split(","):
                        p = p.strip()
                        if " " in p:
                            parts = p.split()
                            func.parameters.append(
                                Parameter(name=parts[-1], type=" ".join(parts[:-1]))
                            )
                    fast.functions.append(func)

            except Exception as e:
                fast.errors.append(str(e))

            index.files[file_path_str] = fast

        index.total_classes = sum(len(f.classes) for f in index.files.values())
        index.total_methods = sum(
            len(c.methods) for f in index.files.values() for c in f.classes
        )
        return index


def _parse_dart_output(stdout: str) -> ASTIndex:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stdout, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            return ASTIndex(errors=[ParseError("", "JSON parse error from Dart analyzer")])

    index = ASTIndex()
    for file_data in data.get("files", []):
        path = file_data.get("path", "")
        fast = FileAST(
            path=path,
            language="dart",
            namespace=file_data.get("library"),
            imports=file_data.get("imports", []),
        )

        for cls_data in file_data.get("classes", []):
            cls = ClassDecl(
                name=cls_data.get("name", ""),
                class_type=cls_data.get("type", "class"),
                base_types=cls_data.get("extends", []),
                interfaces=cls_data.get("implements", []) + cls_data.get("with", []),
                attributes=cls_data.get("annotations", []),
                loc=cls_data.get("loc", 0),
            )
            for m in cls_data.get("methods", []):
                params = [
                    Parameter(name=p.get("name", ""), type=p.get("type", "dynamic"))
                    for p in m.get("parameters", [])
                ]
                cls.methods.append(MethodDecl(
                    name=m.get("name", ""),
                    return_type=m.get("return_type"),
                    parameters=params,
                    modifiers=m.get("modifiers", []),
                    calls=m.get("calls", []),
                    loc=m.get("loc", 0),
                ))
            for c in cls_data.get("constructors", []):
                params = [
                    Parameter(name=p.get("name", ""), type=p.get("type", "dynamic"))
                    for p in c.get("parameters", [])
                ]
                cls.constructors.append(ConstructorDecl(parameters=params))
            for prop in cls_data.get("properties", []):
                cls.properties.append(PropertyDecl(
                    name=prop.get("name", ""),
                    type=prop.get("type"),
                    modifiers=prop.get("modifiers", []),
                ))
            fast.classes.append(cls)

        for func_data in file_data.get("functions", []):
            fast.functions.append(FunctionDecl(
                name=func_data.get("name", ""),
                return_type=func_data.get("return_type"),
                parameters=[
                    Parameter(name=p.get("name", ""), type=p.get("type", "dynamic"))
                    for p in func_data.get("parameters", [])
                ],
            ))

        index.files[path] = fast

    index.total_classes = sum(len(f.classes) for f in index.files.values())
    index.total_methods = sum(
        len(c.methods) for f in index.files.values() for c in f.classes
    )
    return index
