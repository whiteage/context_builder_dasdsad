"""Unity parser — C# via Roslyn + .meta file analysis."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from src.parsers.base import (
    ASTIndex,
    BaseParser,
    ClassDecl,
    FieldDecl,
    FileAST,
    MethodDecl,
    ParseError,
)
from src.parsers.csharp import CSharpParser

logger = logging.getLogger(__name__)

# Unity-specific base classes to track
UNITY_BASE_CLASSES = {
    "MonoBehaviour",
    "ScriptableObject",
    "NetworkBehaviour",
    "StateMachineBehaviour",
    "EditorWindow",
    "Editor",
    "BaseComponent",
    "SystemBase",
    "ISystem",
    "JobComponentSystem",
}

UNITY_ATTRIBUTES = {
    "SerializeField",
    "RequireComponent",
    "Header",
    "Tooltip",
    "Range",
    "Multiline",
    "TextArea",
    "HideInInspector",
    "ContextMenu",
    "MenuItem",
    "AddComponentMenu",
    "CreateAssetMenu",
    "ExecuteAlways",
    "DisallowMultipleComponent",
    "SelectionBase",
}


class UnityParser(BaseParser):
    language = "unity"
    required_tools = ["dotnet"]

    def __init__(self) -> None:
        self._csharp_parser = CSharpParser()

    def check_available(self) -> bool:
        return self._csharp_parser.check_available()

    def parse(self, project_path: str, files: list[str] | None = None) -> ASTIndex:
        project_path = Path(project_path).resolve()
        assets_dir = project_path / "Assets"
        if not assets_dir.is_dir():
            return ASTIndex(errors=[ParseError("", "No Assets/ directory found")])

        # 1. Parse C# scripts via Roslyn (or regex fallback inside CSharpParser)
        cs_files = list(assets_dir.glob("**/*.cs"))
        cs_paths = [str(f) for f in cs_files]
        csharp_index = self._csharp_parser.parse(project_path=str(project_path), files=cs_paths)

        # If Roslyn/regex produced nothing, use Unity-specific regex fallback
        if not csharp_index.files and cs_paths:
            logger.warning("C# parser produced no results, using Unity fallback")
            return self._fallback_parse(project_path)

        # 2. Augment with Unity-specific analysis
        self._augment_with_unity_info(csharp_index, project_path)

        # 3. Parse .meta files
        self._parse_meta_files(csharp_index, assets_dir)

        return csharp_index

    def _augment_with_unity_info(self, index: ASTIndex, project_path: Path) -> None:
        """Tag MonoBehaviour/ScriptableObject classes, find [SerializeField] fields."""
        for file_path, fast in index.files.items():
            for cls in fast.classes:
                is_unity_class = False
                for base_type in cls.base_types:
                    if base_type in UNITY_BASE_CLASSES:
                        is_unity_class = True
                        break

                if is_unity_class:
                    if "Unity" not in cls.attributes:
                        cls.attributes.append("Unity")

                    if cls.class_type == "class" and "MonoBehaviour" in cls.base_types:
                        cls.attributes.append("MonoBehaviour")
                    elif cls.class_type == "class" and "ScriptableObject" in cls.base_types:
                        cls.attributes.append("ScriptableObject")

    def _parse_meta_files(self, index: ASTIndex, assets_dir: Path) -> None:
        """Parse .meta files for GUIDs and asset references."""
        meta_files = list(assets_dir.glob("**/*.meta"))
        for meta_path in meta_files:
            try:
                content = meta_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            rel_path = str(meta_path.relative_to(assets_dir.parent)).replace("\\", "/")

            # Extract GUID
            guid_match = re.search(r"guid:\s*([a-f0-9]{32})", content)
            if not guid_match:
                continue

            # Determine the source file this .meta belongs to
            source_path = rel_path.replace(".meta", "")
            if source_path in index.files:
                fast = index.files[source_path]
                fast.imports.append(f"guid:{guid_match.group(1)}")

    def _fallback_parse(self, project_path: Path) -> ASTIndex:
        """Regex-based parsing when Roslyn is not available."""
        index = ASTIndex()
        cs_files = list((project_path / "Assets").glob("**/*.cs"))

        for file_path in cs_files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            rel_path = str(file_path.relative_to(project_path)).replace("\\", "/")
            fast = FileAST(path=rel_path, language="csharp")

            # Find MonoBehaviour/ScriptableObject classes
            for m in re.finditer(
                r"(class|struct)\s+(\w+)\s*:\s*(\w+)",
                content,
            ):
                cls = ClassDecl(
                    name=m.group(2),
                    class_type=m.group(1),
                    base_types=[m.group(3)],
                )
                if m.group(3) in UNITY_BASE_CLASSES:
                    cls.attributes = ["Unity", m.group(3)]

                # Find [SerializeField] fields
                for fm in re.finditer(
                    r"\[SerializeField\]\s*\n\s*(?:private|public|protected|internal)?\s*"
                    r"([\w<>\[\]]+)\s+(\w+)\s*[;=]",
                    content,
                ):
                    cls.fields.append(FieldDecl(
                        name=fm.group(2),
                        type=fm.group(1),
                        attributes=["SerializeField"],
                    ))

                # Find public methods
                for mm in re.finditer(
                    r"(public|private|protected|internal)?\s*"
                    r"(?:static\s+)?"
                    r"(?:virtual\s+)?"
                    r"(?:override\s+)?"
                    r"([\w<>\[\]]+)\s+(\w+)\s*\(([^)]*)\)",
                    content[m.end():m.end() + 3000],
                ):
                    method = MethodDecl(
                        name=mm.group(3),
                        return_type=mm.group(2),
                        modifiers=[mm.group(1)] if mm.group(1) else [],
                    )
                    cls.methods.append(method)

                fast.classes.append(cls)

            index.files[rel_path] = fast

        index.total_classes = sum(len(f.classes) for f in index.files.values())
        index.total_methods = sum(
            len(c.methods) for f in index.files.values() for c in f.classes
        )
        return index
