"""TypeScript / Vue parser — calls TS Compiler API via subprocess."""

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

TS_ANALYZER_SCRIPT = (
    Path(__file__).parent.parent.parent / "parsers" / "ts-analyzer" / "analyze.mjs"
)


class TypeScriptParser(BaseParser):
    language = "typescript"
    required_tools = ["node"]

    def check_available(self) -> bool:
        try:
            result = subprocess.run(
                ["node", "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def parse(self, project_path: str, files: list[str] | None = None) -> ASTIndex:
        project_path = Path(project_path).resolve()

        if not TS_ANALYZER_SCRIPT.exists():
            logger.warning(f"TS analyzer not found at {TS_ANALYZER_SCRIPT}, using fallback")
            return self._parse_fallback(project_path, files)

        cmd = ["node", str(TS_ANALYZER_SCRIPT), str(project_path)]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True,
                timeout=120, cwd=str(project_path),
            )
            if result.returncode != 0:
                logger.error(f"TS analyzer failed: {result.stderr[:500]}")
                return self._parse_fallback(project_path, files)
            return _parse_ts_output(result.stdout)
        except subprocess.TimeoutExpired:
            logger.error("TS analyzer timed out")
            return self._parse_fallback(project_path, files)
        except FileNotFoundError:
            logger.warning("node not found, using regex fallback")
            return self._parse_fallback(project_path, files)

    def _parse_fallback(self, project_path: Path, files: list[str] | None = None) -> ASTIndex:
        """Regex-based fallback for TypeScript/Vue files."""
        index = ASTIndex()

        for file_path_str in (files or []):
            full_path = (project_path / file_path_str).resolve()
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            # For Vue files, extract script block
            if full_path.suffix == ".vue":
                script_match = re.search(
                    r"<script[^>]*>(.*?)</script>", content, re.DOTALL
                )
                if script_match:
                    content = script_match.group(1)
                else:
                    content = ""

            fast = FileAST(path=file_path_str, language="typescript")

            try:
                # Imports
                for m in re.finditer(
                    r"import\s+(?:type\s+)?(?:\{[^}]*\}|[\w*]+|\w+)\s+from\s+['\"]([^'\"]+)['\"]",
                    content,
                ):
                    fast.imports.append(m.group(1))

                for m in re.finditer(
                    r"import\s+['\"]([^'\"]+)['\"]",
                    content,
                ):
                    fast.imports.append(m.group(1))

                # require() calls
                for m in re.finditer(r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", content):
                    if m.group(1) not in fast.imports:
                        fast.imports.append(m.group(1))

                # Classes
                for m in re.finditer(
                    r"(?:@(\w+)\s*\n\s*)*"
                    r"(?:export\s+)?(?:abstract\s+)?"
                    r"(class|interface|type)\s+(\w+)",
                    content,
                ):
                    cls = ClassDecl(name=m.group(3), class_type=m.group(2))

                    # extends/implements
                    body_start = content.find("{", m.end())
                    header = content[m.end():body_start] if body_start > 0 else ""
                    extends_match = re.search(r"extends\s+([\w,\s]+?)(?:\{|implements|$)", header)
                    if extends_match:
                        cls.base_types = [
                            b.strip() for b in extends_match.group(1).split(",")
                        ]
                    impl_match = re.search(r"implements\s+([\w,\s]+?)(?:\{|$)", header)
                    if impl_match:
                        cls.interfaces = [
                            i.strip() for i in impl_match.group(1).split(",")
                        ]

                    # Methods
                    chunk = content[m.end():m.end() + 5000]
                    for mm in re.finditer(
                        r"(?:@(\w+)\s*\n\s*)*"
                        r"(public|private|protected|static|async|\s)*"
                        r"(\w+)\s*\(([^)]*)\)",
                        chunk,
                    ):
                        body_chunk = chunk[mm.end():mm.end() + 2000]
                        method = MethodDecl(
                            name=mm.group(3),
                            modifiers=[x for x in (mm.group(2) or "").split() if x],
                            calls=extract_calls(body_chunk),
                        )
                        params_str = mm.group(4)
                        if params_str.strip():
                            for p in params_str.split(","):
                                p = p.strip()
                                if ":" in p:
                                    p_name, p_type = p.split(":", 1)
                                    method.parameters.append(
                                        Parameter(name=p_name.strip(), type=p_type.strip())
                                    )
                                elif p:
                                    method.parameters.append(
                                        Parameter(name=p, type="any")
                                    )
                        cls.methods.append(method)

                    fast.classes.append(cls)

                # Standalone functions
                for m in re.finditer(
                    r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)",
                    content,
                ):
                    func = FunctionDecl(name=m.group(1))
                    params_str = m.group(2)
                    if params_str.strip():
                        for p in params_str.split(","):
                            p = p.strip()
                            if ":" in p:
                                p_name, p_type = p.split(":", 1)
                                func.parameters.append(
                                    Parameter(name=p_name.strip(), type=p_type.strip())
                                )
                            elif p:
                                func.parameters.append(Parameter(name=p, type="any"))
                    fast.functions.append(func)

            except Exception as e:
                fast.errors.append(str(e))

            index.files[file_path_str] = fast

        index.total_classes = sum(len(f.classes) for f in index.files.values())
        index.total_methods = sum(
            len(c.methods) for f in index.files.values() for c in f.classes
        )
        return index


def _parse_ts_output(stdout: str) -> ASTIndex:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stdout, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            return ASTIndex(errors=[ParseError("", "JSON parse error from TS analyzer")])

    index = ASTIndex()
    for file_data in data.get("files", []):
        path = file_data.get("path", "")
        fast = FileAST(
            path=path,
            language="typescript",
            namespace=file_data.get("module"),
            imports=file_data.get("imports", []),
        )

        for cls_data in file_data.get("classes", []):
            cls = ClassDecl(
                name=cls_data.get("name", ""),
                class_type=cls_data.get("type", "class"),
                base_types=cls_data.get("extends", []),
                interfaces=cls_data.get("implements", []),
                attributes=cls_data.get("decorators", []),
                loc=cls_data.get("loc", 0),
            )
            for m in cls_data.get("methods", []):
                params = [
                    Parameter(name=p.get("name", ""), type=p.get("type", "any"))
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
                    Parameter(name=p.get("name", ""), type=p.get("type", "any"))
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
                    Parameter(name=p.get("name", ""), type=p.get("type", "any"))
                    for p in func_data.get("parameters", [])
                ],
            ))

        index.files[path] = fast

    index.total_classes = sum(len(f.classes) for f in index.files.values())
    index.total_methods = sum(
        len(c.methods) for f in index.files.values() for c in f.classes
    )
    return index
