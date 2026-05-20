"""PHP parser — calls PHP Parser via subprocess."""

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
    MethodDecl,
    Parameter,
    ParseError,
    PropertyDecl,
    extract_calls,
)

logger = logging.getLogger(__name__)

PHP_PARSER_SCRIPT = (
    Path(__file__).parent.parent.parent / "parsers" / "php-parser" / "analyze.php"
)


def _find_php_exe() -> str:
    """Return the best available php executable path (or 'php' if in PATH)."""
    # Try default PATH first
    try:
        result = subprocess.run(
            ["php", "--version"], capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return "php"
    except FileNotFoundError:
        pass

    # Search winget packages directory
    import glob as _glob
    local_appdata = os.environ.get("LOCALAPPDATA", "")
    if local_appdata:
        winget_root = Path(local_appdata) / "Microsoft" / "WinGet" / "Packages"
        if winget_root.is_dir():
            pattern = str(winget_root / "PHP.PHP.*" / "php.exe")
            matches = _glob.glob(pattern)
            if matches:
                return matches[0]

    return "php"


class PHPParser(BaseParser):
    language = "php"
    required_tools = ["php"]

    def check_available(self) -> bool:
        try:
            exe = _find_php_exe()
            result = subprocess.run(
                [exe, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def parse(self, project_path: str, files: list[str] | None = None) -> ASTIndex:
        project_path = Path(project_path).resolve()

        if not PHP_PARSER_SCRIPT.exists():
            logger.warning(f"PHP parser script not found at {PHP_PARSER_SCRIPT}, using fallback")
            return self._parse_fallback(project_path, files)

        cmd = [_find_php_exe(), str(PHP_PARSER_SCRIPT), str(project_path)]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True,
                timeout=120, cwd=str(project_path),
            )
            if result.returncode != 0:
                logger.warning("PHP parser failed, using regex fallback: %s", result.stderr[:200])
                return self._parse_fallback(project_path, files)
            return _parse_php_output(result.stdout)
        except FileNotFoundError:
            logger.warning("php not found, using regex fallback")
            return self._parse_fallback(project_path, files)
        except subprocess.TimeoutExpired:
            logger.warning("PHP parser timed out, using regex fallback")
            return self._parse_fallback(project_path, files)
        except FileNotFoundError:
            logger.warning("php not found, using regex fallback")
            return self._parse_fallback(project_path, files)

    def _parse_fallback(self, project_path: Path, files: list[str] | None = None) -> ASTIndex:
        """Regex-based fallback for PHP files."""
        index = ASTIndex()

        for file_path_str in (files or []):
            full_path = (project_path / file_path_str).resolve()
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            fast = FileAST(path=file_path_str, language="php")

            try:
                # Namespace
                ns_match = re.search(r"namespace\s+([\w\\]+)\s*;", content)
                if ns_match:
                    fast.namespace = ns_match.group(1)

                # Use imports
                for m in re.finditer(r"use\s+([\w\\]+)(?:\s+as\s+(\w+))?\s*;", content):
                    fast.imports.append(m.group(1))

                # Classes
                for m in re.finditer(
                    r"(?:#\[([^\]]+)\]\s*\n\s*)*"
                    r"(?:abstract\s+|final\s+)*"
                    r"(class|interface|trait|enum)\s+(\w+)",
                    content,
                ):
                    cls = ClassDecl(name=m.group(3), class_type=m.group(2))

                    # extends/implements
                    body_start = content.find("{", m.end())
                    header = content[m.end():body_start] if body_start > 0 else ""
                    extends_match = re.search(r"extends\s+([\w\\]+)", header)
                    if extends_match:
                        cls.base_types.append(extends_match.group(1))
                    impl_match = re.search(r"implements\s+([\w\\,\s]+)", header)
                    if impl_match:
                        cls.interfaces = [
                            i.strip() for i in impl_match.group(1).split(",")
                        ]

                    # Methods
                    chunk = content[m.end():m.end() + 5000]
                    for mm in re.finditer(
                        r"(?:#\[([^\]]+)\]\s*\n\s*)*"
                        r"(public|private|protected|static|\s)*"
                        r"function\s+(\w+)\s*\(([^)]*)\)",
                        chunk,
                    ):
                        body_chunk = content[mm.end():mm.end() + 2000]
                        method = MethodDecl(name=mm.group(3), calls=extract_calls(body_chunk))
                        params_str = mm.group(4)
                        if params_str.strip():
                            for p in params_str.split(","):
                                p = p.strip()
                                if " " in p:
                                    p_type, p_name = p.rsplit(" ", 1)
                                    method.parameters.append(
                                        Parameter(name=p_name.strip(), type=p_type.strip())
                                    )

                        # Return type
                        rt_match = re.search(
                            r"\)\s*:\s*(\??[\w\\]+)", chunk[mm.start():mm.start() + 200]
                        )
                        if rt_match:
                            method.return_type = rt_match.group(1)

                        cls.methods.append(method)

                    fast.classes.append(cls)

            except Exception as e:
                fast.errors.append(str(e))

            index.files[file_path_str] = fast

        index.total_classes = sum(len(f.classes) for f in index.files.values())
        index.total_methods = sum(
            len(c.methods) for f in index.files.values() for c in f.classes
        )
        return index


def _parse_php_output(stdout: str) -> ASTIndex:
    """Parse JSON output from PHP Parser."""
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stdout, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            return ASTIndex(errors=[ParseError("", "JSON parse error from PHP parser")])

    index = ASTIndex()
    for file_data in data.get("files", []):
        path = file_data.get("path", "")
        fast = FileAST(
            path=path,
            language="php",
            namespace=file_data.get("namespace"),
            imports=file_data.get("uses", []),
        )

        for cls_data in file_data.get("classes", []):
            cls = ClassDecl(
                name=cls_data.get("name", ""),
                class_type=cls_data.get("type", "class"),
                base_types=cls_data.get("extends", []),
                interfaces=cls_data.get("implements", []),
                attributes=cls_data.get("attributes", []),
                loc=cls_data.get("loc", 0),
            )

            for m in cls_data.get("methods", []):
                params = [
                    Parameter(name=p.get("name", ""), type=p.get("type", "mixed"))
                    for p in m.get("parameters", [])
                ]
                cls.methods.append(MethodDecl(
                    name=m.get("name", ""),
                    return_type=m.get("return_type"),
                    parameters=params,
                    modifiers=m.get("modifiers", []),
                    attributes=m.get("attributes", []),
                    calls=m.get("calls", []),
                    loc=m.get("loc", 0),
                ))

            for c in cls_data.get("constructors", []):
                params = [
                    Parameter(name=p.get("name", ""), type=p.get("type", "mixed"))
                    for p in c.get("parameters", [])
                ]
                cls.constructors.append(ConstructorDecl(
                    parameters=params,
                    modifiers=c.get("modifiers", []),
                ))

            for prop in cls_data.get("properties", []):
                cls.properties.append(PropertyDecl(
                    name=prop.get("name", ""),
                    type=prop.get("type"),
                    modifiers=prop.get("modifiers", []),
                    attributes=prop.get("attributes", []),
                ))

            fast.classes.append(cls)

        index.files[path] = fast

    index.total_classes = sum(len(f.classes) for f in index.files.values())
    index.total_methods = sum(
        len(c.methods) for f in index.files.values() for c in f.classes
    )
    return index
