"""C++ parser using tree-sitter AST with regex fallback."""

from __future__ import annotations

import logging
import re
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
    extract_calls,
)

logger = logging.getLogger(__name__)

TREE_SITTER_AVAILABLE = False
try:
    import tree_sitter
    import tree_sitter_cpp as tscpp
    _TS_LANG = tree_sitter.Language(tscpp.language())
    TREE_SITTER_AVAILABLE = True
except ImportError:
    logger.warning("tree-sitter / tree-sitter-cpp not installed, using regex fallback")

INCLUDE_RE = re.compile(r'#include\s+[<"]([^>"]+)[>"]')

# UE macros that confuse tree-sitter — strip them for clean parsing
_UE_MACRO_RE = re.compile(r'(?:UFUNCTION|UPROPERTY|UCLASS|USTRUCT|UENUM)\s*\([^)]*\)', re.MULTILINE)
# UE API export macro (appears before class name)
_UE_API_RE = re.compile(r'\b\w+_API\b')


def _is_ue_macro(text: str) -> str | None:
    t = text.strip()
    for m in ("UFUNCTION", "UPROPERTY", "UCLASS", "USTRUCT", "UENUM"):
        if m in t:
            return m
    return None


def _preprocess_ue_source(source: str) -> str:
    """Remove UE macros that confuse tree-sitter. Replace with whitespace of same length to preserve byte offsets."""
    cleaned = _UE_MACRO_RE.sub(
        lambda m: "\n" * m.group().count("\n") + " " * (len(m.group()) - m.group().count("\n")),
        source,
    )
    # Also strip API export macros (e.g. SURVIVALGAME_API) — same-length preservation
    cleaned = re.sub(r'\b\w+_API\b', lambda m: " " * len(m.group()), cleaned)
    return cleaned


class CppParser(BaseParser):
    language = "cpp"
    required_tools = []

    def check_available(self) -> bool:
        return True  # Always available: tree-sitter or regex fallback

    def parse(self, project_path: str, files: list[str] | None = None) -> ASTIndex:
        project_path = Path(project_path).resolve()
        source_files = self._collect_files(project_path, files)

        if TREE_SITTER_AVAILABLE:
            return self._parse_with_treesitter(project_path, source_files)
        return self._parse_with_regex(source_files)

    def _collect_files(self, project_path: Path, files: list[str] | None) -> list[Path]:
        if files:
            return [project_path / f for f in files if (project_path / f).exists()]
        result = []
        for ext in (".cpp", ".h", ".hpp", ".cxx", ".cc"):
            result.extend(project_path.glob(f"**/*{ext}"))
        return sorted(result)

    # ── tree-sitter implementation ──────────────────────────────────

    def _parse_with_treesitter(self, project_path: Path, files: list[Path]) -> ASTIndex:
        index = ASTIndex()
        parser = tree_sitter.Parser(_TS_LANG)

        for fpath in files:
            try:
                with open(fpath, encoding="utf-8", errors="replace") as f:
                    source = f.read()
            except Exception:
                continue

            rel = str(fpath.relative_to(project_path)).replace("\\", "/")
            fast = FileAST(path=rel, language="cpp")

            try:
                # Preprocess to remove UE macros that confuse tree-sitter
                cleaned = _preprocess_ue_source(source)
                tree = parser.parse(cleaned.encode())
                fast = self._walk_tree(fast, tree.root_node, source)
            except Exception as e:
                fast.errors.append(str(e))

            index.files[rel] = fast

        index.total_classes = sum(len(f.classes) for f in index.files.values())
        index.total_methods = sum(
            len(c.methods) for f in index.files.values() for c in f.classes
        )
        return index

    def _walk_tree(self, fast: FileAST, root, source: str) -> FileAST:
        # Collect #include paths
        for child in root.children:
            if child.type == "preproc_include":
                path_node = child.child_by_field_name("path")
                if path_node:
                    p = path_node.text.decode().strip('"<>')
                    fast.imports.append(p)

        # Walk top-level and find class_specifier / struct_specifier
        self._walk_node(fast, root, source, pending_ue_attrs=[])
        return fast

    def _walk_node(self, fast: FileAST, node, source: str,
                   pending_ue_attrs: list[str]) -> list[str]:
        """Walk recursively. Returns accumulated UE attributes for next class."""
        for child in node.children:
            if child.type in ("class_specifier", "struct_specifier"):
                # Skip forward declarations (no body)
                if child.child_by_field_name("body") is not None:
                    cls = self._extract_class(child, source, pending_ue_attrs)
                    if cls:
                        fast.classes.append(cls)
                    pending_ue_attrs = []
            elif child.type == "function_definition":
                # UE macros can cause class_specifier to be inside function_definition
                # E.g. UCLASS() followed by class FOO_API AMyClass : public AParent { ... }
                for fc in child.children:
                    if fc.type in ("class_specifier", "struct_specifier"):
                        if fc.child_by_field_name("body") is not None:
                            cls = self._extract_class(fc, source, pending_ue_attrs)
                            if cls:
                                fast.classes.append(cls)
                            pending_ue_attrs = []
            elif child.type == "declaration":
                text = child.text.decode()
                ue = _is_ue_macro(text)
                if ue:
                    pending_ue_attrs.append(ue)
            elif child.type == "expression_statement":
                text = child.text.decode()
                ue = _is_ue_macro(text)
                if ue:
                    pending_ue_attrs.append(ue)
            elif child.type == "ERROR":
                text = child.text.decode()
                ue = _is_ue_macro(text)
                if ue:
                    pending_ue_attrs.append(ue)
            else:
                self._walk_node(fast, child, source, pending_ue_attrs)
        return pending_ue_attrs

    def _extract_class(self, node, source: str,
                       file_ue_attrs: list[str]) -> ClassDecl | None:
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return None
        cls_name = name_node.text.decode()

        cls_type = "struct" if node.type == "struct_specifier" else "class"

        # Base types — check the class_specifier for base_class_clause
        base_types: list[str] = []
        for child in node.children:
            if child.type == "base_class_clause":
                for bc in child.named_children:
                    if bc.type in ("type_identifier", "qualified_identifier"):
                        base_name = bc.text.decode()
                        if not base_name.endswith("_API"):
                            base_types.append(base_name)

        # Class-level UE attributes (from original source, since preprocessing removed them)
        attrs: list[str] = list(set(file_ue_attrs))
        body = node.child_by_field_name("body")
        body_text = body.text.decode() if body else ""

        # Check original source for macros (they're in file_ue_attrs from expression_statement)
        if body and "GENERATED_BODY()" in body_text:
            attrs.append("GENERATED_BODY")
        if body and "GENERATED_UCLASS_BODY()" in body_text:
            attrs.append("GENERATED_BODY")
        if "UCLASS" not in attrs:
            # Check if there's UCLASS in the original source before this class
            cls_start = node.start_byte
            if cls_start > 0 and "UCLASS" in source[max(0, cls_start - 200):cls_start]:
                attrs.append("UCLASS")

        cls = ClassDecl(
            name=cls_name,
            class_type=cls_type,
            base_types=base_types,
            attributes=attrs,
        )

        # Walk body
        if body:
            self._extract_members(body, cls, body_text, source)

        cls.loc = body_text.count("\n") if body else 0
        return cls

    def _find_real_class_name(self, node):
        """Handle `class SURVIVALGAME_API ASCharacter` pattern."""
        found_api = False
        for child in node.children:
            if child.type == "type_identifier" and child.text.decode().endswith("_API"):
                found_api = True
                continue
            if found_api and child.type == "type_identifier":
                return child
        return None

    def _extract_members(self, body_node, cls: ClassDecl, body_text: str, source: str):
        """Walk field_declaration_list to find methods, fields, constructors."""
        seen_methods: set[str] = set()

        for child in body_node.children:
            if child.type != "field_declaration":
                continue

            # Look at original source (before preprocessing) for UE macro annotations
            ue_macro = self._find_ue_macro_before(source, child.start_byte)

            # Determine if this is a method or field
            func_decl = None
            field_id = None
            type_str = ""
            modifiers: list[str] = []
            attrs: list[str] = []

            for fc in child.children:
                if fc.type == "function_declarator":
                    func_decl = fc
                elif fc.type == "field_identifier":
                    field_id = fc
                elif fc.type in ("virtual",):
                    modifiers.append("virtual")
                elif fc.type == "virtual_specifier":
                    spec = fc.text.decode().strip()
                    if spec:
                        modifiers.append(spec)
                elif fc.type in ("type_identifier", "primitive_type", "qualified_identifier",
                                 "struct_specifier", "enum_specifier",
                                 "template_type", "template_function", "sized_type_specifier"):
                    type_str = fc.text.decode()
                elif fc.type == "pointer_declarator":
                    type_str += "*" if not type_str.endswith("*") else ""

            # Map UE macro from original source
            if ue_macro:
                attrs.append(ue_macro)

            if func_decl:
                # It's a method
                method_name = ""
                for fc in func_decl.children:
                    if fc.type == "field_identifier":
                        method_name = fc.text.decode()
                        break
                    elif fc.type == "destructor_name":
                        method_name = fc.text.decode()
                        break
                    elif fc.type == "identifier":
                        method_name = fc.text.decode()
                        break

                if not method_name or method_name in seen_methods:
                    continue
                seen_methods.add(method_name)

                # Parse modifiers from full text
                full_text = child.text.decode()
                if "virtual" in full_text and "virtual" not in modifiers:
                    modifiers.append("virtual")
                if "override" in full_text and "override" not in modifiers:
                    modifiers.append("override")
                if "static" in full_text and "static" not in modifiers:
                    modifiers.append("static")
                if "const" in full_text and "const" not in modifiers:
                    modifiers.append("const")

                if not type_str:
                    type_str = self._extract_return_type(child, method_name)

                params = self._extract_params(func_decl)

                cls.methods.append(MethodDecl(
                    name=method_name,
                    return_type=type_str if type_str else None,
                    parameters=params,
                    modifiers=modifiers,
                    attributes=attrs,
                ))
            elif field_id:
                field_name = field_id.text.decode()
                if field_name in ("if", "for", "while", "GENERATED_BODY"):
                    continue

                if not type_str:
                    type_str = self._extract_field_type(child, field_name)

                cls.fields.append(FieldDecl(
                    name=field_name,
                    type=type_str if type_str else None,
                    attributes=attrs,
                ))

        # Extract constructors
        cls.constructors = self._extract_constructors(body_text, cls.name)

    def _find_ue_macro_before(self, source: str, byte_offset: int) -> str | None:
        """Check if original source has UFUNCTION() or UPROPERTY() just before byte_offset."""
        # Look back up to 200 bytes for a UE macro
        lookback = source[max(0, byte_offset - 200):byte_offset]
        # Match the last UE macro in the lookback window
        m = re.search(r'(UFUNCTION|UPROPERTY)\s*\([^)]*\)\s*$', lookback, re.DOTALL)
        if m:
            return m.group(1)
        return None

    def _extract_return_type(self, node, method_name: str) -> str:
        """Get the return type by looking at text before the method name."""
        text = node.text.decode()
        # Find method name in text
        idx = text.find(method_name)
        if idx > 0:
            before = text[:idx].strip()
            # Remove leading keywords
            for kw in ("virtual", "static", "inline", "FORCEINLINE", "const", "constexpr"):
                before = re.sub(rf'\b{kw}\b', '', before).strip()
            # Remove pointer/reference marks
            before = before.rstrip("*& ")
            return before
        return ""

    def _extract_field_type(self, node, field_name: str) -> str:
        """Get field type from text before field name."""
        text = node.text.decode()
        idx = text.find(field_name)
        if idx > 0:
            before = text[:idx].strip()
            before = before.rstrip("*& ")
            return before
        return ""

    def _extract_params(self, func_decl) -> list[Parameter]:
        params: list[Parameter] = []
        param_list = func_decl.child_by_field_name("parameters")
        if param_list is None:
            return params

        for child in param_list.children:
            if child.type == "parameter_declaration":
                ptype = ""
                pname = ""
                default = None
                for pc in child.children:
                    if pc.type in ("type_identifier", "primitive_type", "qualified_identifier",
                                   "template_type", "sized_type_specifier"):
                        ptype = pc.text.decode()
                    elif pc.type == "field_identifier":
                        pname = pc.text.decode()
                    elif pc.type == "pointer_declarator" and ptype:
                        ptype += "*"
                    elif pc.type == "reference_declarator" and ptype:
                        ptype += "&"
                if "=" in child.text.decode():
                    default = child.text.decode().split("=", 1)[1].strip().rstrip(";")

                if pname:
                    params.append(Parameter(name=pname, type=ptype or "auto", default_value=default))
        return params

    def _extract_constructors(self, body_text: str, class_name: str) -> list[ConstructorDecl]:
        constructors: list[ConstructorDecl] = []
        for m in re.finditer(
            rf'{re.escape(class_name)}\s*\(([^)]*)\)',
            body_text,
        ):
            params_str = m.group(1)
            cparams: list[Parameter] = []
            if params_str.strip():
                for p in params_str.split(","):
                    p = p.strip()
                    default = None
                    if "=" in p:
                        p, default = p.split("=", 1)
                        p = p.strip()
                        default = default.strip()
                    parts = p.split()
                    if len(parts) >= 2:
                        cparams.append(Parameter(name=parts[-1].lstrip("*&"), type=" ".join(parts[:-1]), default_value=default))
            constructors.append(ConstructorDecl(parameters=cparams))
        return constructors

    # ── Regex fallback ──────────────────────────────────────────────

    def _parse_with_regex(self, source_files: list[Path]) -> ASTIndex:
        index = ASTIndex()

        for fpath in source_files:
            try:
                with open(fpath, encoding="utf-8", errors="replace") as f:
                    content = f.read()
            except Exception:
                continue

            rel = str(fpath).replace("\\", "/")
            fast = FileAST(path=rel, language="cpp")

            try:
                for m in INCLUDE_RE.finditer(content):
                    fast.imports.append(m.group(1))
                classes = self._regex_extract_classes(content)
                fast.classes = classes
            except Exception as e:
                fast.errors.append(str(e))

            index.files[rel] = fast

        index.total_classes = sum(len(f.classes) for f in index.files.values())
        index.total_methods = sum(
            len(c.methods) for f in index.files.values() for c in f.classes
        )
        return index

    def _regex_extract_classes(self, content: str) -> list[ClassDecl]:
        classes: list[ClassDecl] = []
        for m in re.finditer(
            r'(?:class|struct)\s+(?:\w+(?:_API)?\s+)?(\w+)\s*(?::\s*(.+?))?\s*\{',
            content,
        ):
            cls_name = m.group(1)
            bases_str = m.group(2) or ""
            cls_type = "class"

            body_start = m.end()
            body_end = self._match_brace(content, body_start - 1)
            body = content[body_start:body_end] if body_end > body_start else ""

            base_types = []
            if bases_str.strip():
                for base in re.split(r',\s*', bases_str):
                    base = re.sub(r'\b(?:public|private|protected)\s+', '', base.strip())
                    if base.strip():
                        base_types.append(base.strip())

            attrs = []
            if 'UCLASS' in content[m.start():body_start]:
                attrs.append('UCLASS')
            if 'GENERATED_BODY()' in body:
                attrs.append('GENERATED_BODY')

            cls = ClassDecl(name=cls_name, class_type=cls_type, base_types=base_types, attributes=attrs)

            # Methods
            for mm in re.finditer(
                r'(?:UFUNCTION\s*\([^)]*\)\s*)?'
                r'(?:virtual\s+)?(?:static\s+)?(?:FORCEINLINE\s+)?'
                r'([\w:<>&,\s\*]+?)\s+(\w+)\s*\(([^)]*)\)\s*(?:const\s*)?(?:override\s*)?;',
                body,
            ):
                ret_type = mm.group(1).strip()
                method_name = mm.group(2)
                if method_name.startswith("~") or method_name in ("if", "for", "while", "return"):
                    continue
                if ret_type in ("return", "if", "for", "while"):
                    continue

                rparams = []
                params_str = mm.group(3)
                if params_str.strip():
                    for p in params_str.split(","):
                        p = p.strip()
                        default = None
                        if "=" in p:
                            p, default = p.split("=", 1)
                            p = p.strip()
                            default = default.strip()
                        parts = p.split()
                        if len(parts) >= 2:
                            rparams.append(Parameter(name=parts[-1].lstrip("*&"), type=" ".join(parts[:-1]), default_value=default))

                rmods = []
                if "virtual" in mm.group(0):
                    rmods.append("virtual")
                if "override" in mm.group(0):
                    rmods.append("override")
                if "static" in mm.group(0):
                    rmods.append("static")
                if "const" in mm.group(0):
                    rmods.append("const")

                rattrs = ["UFUNCTION"] if mm.group(0).strip().startswith("UFUNCTION") else []

                cls.methods.append(MethodDecl(name=method_name, return_type=ret_type, parameters=rparams, modifiers=rmods, attributes=rattrs))

            # Fields with UPROPERTY
            for fm in re.finditer(
                r'UPROPERTY\s*\([^)]*\)\s*\n\s*([\w:<>&,\s\*]+?)\s+(\w+)\s*;',
                body,
            ):
                cls.fields.append(FieldDecl(name=fm.group(2), type=fm.group(1).strip(), attributes=["UPROPERTY"]))

            cls.loc = body.count("\n")
            classes.append(cls)

        return classes

    @staticmethod
    def _match_brace(text: str, start: int) -> int:
        depth = 0
        i = start
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return i
            i += 1
        return len(text)

    # ── Public raw API ──────────────────────────────────────────────

    def parse_raw(self, file_contents: dict[str, str]) -> ASTIndex:
        """Parse from dict of {path: source_code}."""
        if TREE_SITTER_AVAILABLE:
            index = ASTIndex()
            parser = tree_sitter.Parser(_TS_LANG)
            for path, content in file_contents.items():
                fast = FileAST(path=path, language="cpp")
                try:
                    cleaned = _preprocess_ue_source(content)
                    tree = parser.parse(cleaned.encode())
                    fast = self._walk_tree(fast, tree.root_node, content)
                except Exception as e:
                    fast.errors.append(str(e))
                index.files[path] = fast
            index.total_classes = sum(len(f.classes) for f in index.files.values())
            index.total_methods = sum(
                len(c.methods) for f in index.files.values() for c in f.classes
            )
            return index

        return self._parse_with_regex_flat(file_contents)

    def _parse_with_regex_flat(self, file_contents: dict[str, str]) -> ASTIndex:
        index = ASTIndex()
        for path, content in file_contents.items():
            fast = FileAST(path=path, language="cpp")
            try:
                for m in INCLUDE_RE.finditer(content):
                    fast.imports.append(m.group(1))
                fast.classes = self._regex_extract_classes(content)
            except Exception as e:
                fast.errors.append(str(e))
            index.files[path] = fast
        index.total_classes = sum(len(f.classes) for f in index.files.values())
        index.total_methods = sum(
            len(c.methods) for f in index.files.values() for c in f.classes
        )
        return index
