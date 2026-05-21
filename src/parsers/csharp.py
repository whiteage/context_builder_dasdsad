"""C# parser — calls Roslyn Analyzer via subprocess."""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path

from src.parsers.base import (
    ASTIndex,
    BaseParser,
    ClassDecl,
    ConstructorDecl,
    FieldDecl,
    FileAST,
    MethodDecl,
    Parameter,
    ParseError,
    PropertyDecl,
    extract_calls,
)

logger = logging.getLogger(__name__)

# Locate the Roslyn analyzer DLL (pre-built, absolute path to avoid cwd issues).
_ROSLYN_BASE = (Path(__file__).parent.parent.parent / "parsers" / "roslyn-analyzer").resolve()
_ROSLYN_DLL = (_ROSLYN_BASE / "bin" / "Release" / "net8.0" / "RoslynAnalyzer.dll").resolve()


class CSharpParser(BaseParser):
    language = "csharp"
    required_tools = ["dotnet"]

    def check_available(self) -> bool:
        try:
            result = subprocess.run(
                ["dotnet", "--version"],
                capture_output=True, text=True, timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def parse(self, project_path: str, files: list[str] | None = None) -> ASTIndex:
        project_path = Path(project_path).resolve()

        # Use bounded walk to find .csproj/.sln without leaking into nested projects
        from src.config import _walk_project_dirs
        walk_dirs = _walk_project_dirs(project_path)
        csproj_files: list[Path] = []
        sln_files: list[Path] = []
        for d in walk_dirs:
            csproj_files.extend(d.glob("*.csproj"))
            sln_files.extend(d.glob("*.sln"))

        target = None
        if sln_files:
            target = str(sln_files[0])
        elif csproj_files:
            target = str(csproj_files[0])

        cmd = [
            "dotnet", str(_ROSLYN_DLL),
            "--project", str(project_path),
        ]
        if target:
            cmd.extend(["--target", target])
        if files and len(files) <= 100:
            cmd.append("--files")
            cmd.extend(files)
        elif files:
            logger.debug("%d files requested, skipping --files (Roslyn will auto-discover)", len(files))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True,
                timeout=120,
                env={**os.environ, "DOTNET_CLI_TELEMETRY_OPTOUT": "1"},
            )
            if result.returncode != 0:
                logger.warning("Roslyn analyzer failed, using regex fallback: %s", result.stderr[:200])
                return self._parse_fallback(project_path, files)

            parsed = _parse_output(result.stdout)
            if not parsed.files:
                logger.warning("Roslyn produced no results, using regex fallback")
                return self._parse_fallback(project_path, files)
            # Roslyn doesn't extract method calls — enrich from source
            _enrich_calls_from_source(project_path, parsed)
            return parsed
        except subprocess.TimeoutExpired:
            logger.warning("Roslyn analyzer timed out, using regex fallback")
            return self._parse_fallback(project_path, files)
        except FileNotFoundError:
            logger.warning("dotnet not found, using regex fallback")
            return self._parse_fallback(project_path, files)

    def _parse_fallback(self, project_path: Path, files: list[str] | None = None) -> ASTIndex:
        """Fallback: use regex to extract basic info without Roslyn."""
        import re
        index = ASTIndex()

        if files is None:
            return index

        for file_path in files:
            full_path = (project_path / file_path).resolve()
            try:
                content = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            fast = FileAST(path=file_path, language="csharp")
            try:
                # Extract namespace
                ns_match = re.search(r"namespace\s+([\w.]+)", content)
                if ns_match:
                    fast.namespace = ns_match.group(1)

                # Extract usings
                for m in re.finditer(r"using\s+([\w.]+)\s*;", content):
                    fast.imports.append(m.group(1))

                # Extract class/interface/record/struct declarations
                for m in re.finditer(
                    r"(?:\[([^\]]+)\]\s*\n\s*)*"
                    r"(public|private|protected|internal|static|sealed|abstract|partial|\s)*"
                    r"(class|interface|record|struct)\s+(\w+)",
                    content,
                ):
                    class_name = m.group(4)
                    class_type = m.group(3)
                    cls = ClassDecl(name=class_name, class_type=class_type)

                    # Base types
                    body_start = content.find("{", m.end())
                    header = content[m.end():body_start] if body_start > 0 else ""
                    base_match = re.search(r":\s*(.+?)(?:\{|where)", header)
                    if base_match:
                        bases = [b.strip() for b in base_match.group(1).split(",")]
                        for b in bases:
                            if b.startswith("I"):
                                cls.interfaces.append(b)
                            else:
                                cls.base_types.append(b)

                    # Methods — match declarations, filter out invocations by checking
                    # that the match is followed by a '{' body start.
                    search_start = m.end()
                    for mm in re.finditer(
                        r"(?:\[([^\]]+)\]\s*)*"                  # Attributes (optional)
                        r"((?:(?:public|private|protected|internal|static|virtual|override|abstract|async|extern|unsafe|partial|sealed|readonly|volatile)\s+)*)"
                        r"(?:([\w<>\[\],.]+)\s+)?"              # Return type (optional, no spaces)
                        r"(\w+)\s*\(([^)]*)\)",                   # Method name + params
                        content[search_start:search_start + 5000],
                    ):
                        body_start = search_start + mm.end()
                        body_chunk = content[body_start:body_start + 2000]
                        # Skip method invocations: declarations have '{' before any ';'
                        stripped = body_chunk.lstrip()
                        if stripped and stripped[0] != '{':
                            continue
                        method = MethodDecl(
                            name=mm.group(4),
                            return_type=mm.group(3).strip() if mm.group(3) else None,
                            modifiers=[x for x in (
                                mm.group(2) or "").split() if x],
                            calls=extract_calls(body_chunk),
                        )
                        # Parse parameters
                        params_str = mm.group(5)
                        if params_str.strip():
                            for p in params_str.split(","):
                                p = p.strip()
                                parts = p.split()
                                if len(parts) >= 2:
                                    method.parameters.append(
                                        Parameter(name=parts[-1], type=" ".join(parts[:-1]))
                                    )
                        cls.methods.append(method)

                    fast.classes.append(cls)

            except Exception as e:
                fast.errors.append(str(e))

            index.files[file_path] = fast

        index.total_classes = sum(len(f.classes) for f in index.files.values())
        index.total_methods = sum(
            len(c.methods) for f in index.files.values() for c in f.classes
        )
        return index


def _enrich_calls_from_source(project_path: str, index: ASTIndex) -> None:
    """Post-process Roslyn output: extract method calls from source files.

    Roslyn doesn't export call information, so we scan method bodies with
    the same regex-based approach used in the fallback parser. Processes
    all files that have methods but no call data.
    """
    import re
    project_dir = Path(project_path)

    method_re = re.compile(
        r"(?:\[([^\]]+)\]\s*)*"
        r"((?:(?:public|private|protected|internal|static|virtual|override|abstract|async|extern|unsafe|partial|sealed|readonly|volatile)\s+)*)"
        r"(?:([\w<>\[\],.]+)\s+)?"
        r"(\w+)\s*\(([^)]*)\)",
    )

    for file_path, fast in index.files.items():
        if not fast.classes or any(
            m.calls for cls in fast.classes for m in cls.methods if m.calls
        ):
            continue
        try:
            source = (project_dir / file_path).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # Build a method-name → set of calls map from the source
        method_calls: dict[str, list[str]] = {}
        for mm in method_re.finditer(source):
            method_name = mm.group(4)
            body_start = mm.end()
            body_chunk = source[body_start:body_start + 2000]
            stripped = body_chunk.lstrip()
            if stripped and stripped[0] != "{":
                continue
            calls = extract_calls(body_chunk)
            if calls:
                method_calls[method_name] = list(calls)

        if not method_calls:
            continue

        # Assign calls to matching methods
        for cls in fast.classes:
            for m in cls.methods:
                if m.name in method_calls:
                    m.calls = method_calls[m.name]


def _parse_output(stdout: str) -> ASTIndex:
    """Parse JSON output from Roslyn Analyzer."""
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as e:
        # Try to find JSON in the output
        import re
        match = re.search(r"\{.*\}", stdout, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            return ASTIndex(errors=[ParseError("", f"JSON parse error: {e}")])

    index = ASTIndex()

    for file_data in data.get("files", []):
        path = file_data.get("path", "")
        fast = FileAST(
            path=path,
            language="csharp",
            namespace=file_data.get("namespace"),
            imports=file_data.get("usings", []),
        )

        for cls_data in file_data.get("classes", []):
            cls = ClassDecl(
                name=cls_data.get("name", ""),
                class_type=cls_data.get("type", "class"),
                base_types=cls_data.get("base_types", []),
                interfaces=cls_data.get("interfaces", []),
                attributes=cls_data.get("attributes", []),
                loc=cls_data.get("loc", 0),
            )

            for m in cls_data.get("methods", []):
                params = [
                    Parameter(name=p.get("name", ""), type=p.get("type", "object"))
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
                    Parameter(name=p.get("name", ""), type=p.get("type", "object"))
                    for p in c.get("parameters", [])
                ]
                cls.constructors.append(ConstructorDecl(
                    parameters=params,
                    modifiers=c.get("modifiers", []),
                    attributes=c.get("attributes", []),
                ))

            for prop in cls_data.get("properties", []):
                cls.properties.append(PropertyDecl(
                    name=prop.get("name", ""),
                    type=prop.get("type"),
                    modifiers=prop.get("modifiers", []),
                    attributes=prop.get("attributes", []),
                ))

            for field in cls_data.get("fields", []):
                cls.fields.append(FieldDecl(
                    name=field.get("name", ""),
                    type=field.get("type"),
                    modifiers=field.get("modifiers", []),
                    attributes=field.get("attributes", []),
                ))

            fast.classes.append(cls)

        index.files[path] = fast

    for err in data.get("errors", []):
        index.errors.append(ParseError(
            file_path=err.get("file", ""),
            message=err.get("message", ""),
        ))

    index.total_classes = sum(len(f.classes) for f in index.files.values())
    index.total_methods = sum(
        len(c.methods) for f in index.files.values() for c in f.classes
    )
    return index
