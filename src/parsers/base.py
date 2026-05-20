"""Shared dataclasses for AST parsing results."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Parameter:
    name: str
    type: str
    default_value: str | None = None


@dataclass
class MethodDecl:
    name: str
    return_type: str | None = None
    parameters: list[Parameter] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    calls: list[str] = field(default_factory=list)
    loc: int = 0


@dataclass
class ConstructorDecl:
    parameters: list[Parameter] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)


@dataclass
class PropertyDecl:
    name: str
    type: str | None = None
    modifiers: list[str] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)


@dataclass
class FieldDecl:
    name: str
    type: str | None = None
    modifiers: list[str] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)


@dataclass
class ClassDecl:
    name: str
    class_type: str = "class"  # class, interface, record, struct, trait, enum
    base_types: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    attributes: list[str] = field(default_factory=list)
    methods: list[MethodDecl] = field(default_factory=list)
    constructors: list[ConstructorDecl] = field(default_factory=list)
    properties: list[PropertyDecl] = field(default_factory=list)
    fields: list[FieldDecl] = field(default_factory=list)
    loc: int = 0


@dataclass
class FunctionDecl:
    """For non-OOP languages (standalone functions)."""
    name: str
    return_type: str | None = None
    parameters: list[Parameter] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)
    loc: int = 0


@dataclass
class ParseError:
    file_path: str
    message: str


@dataclass
class FileAST:
    path: str
    language: str
    namespace: str | None = None
    imports: list[str] = field(default_factory=list)
    classes: list[ClassDecl] = field(default_factory=list)
    functions: list[FunctionDecl] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ASTIndex:
    files: dict[str, FileAST] = field(default_factory=dict)
    errors: list[ParseError] = field(default_factory=list)
    total_classes: int = 0
    total_methods: int = 0

    def get_file(self, path: str) -> FileAST | None:
        return self.files.get(path)

    def find_class(self, name: str) -> list[tuple[str, ClassDecl]]:
        results = []
        for path, fast in self.files.items():
            for cls in fast.classes:
                if cls.name == name:
                    results.append((path, cls))
        return results

    def get_sample_signatures(self, n: int = 40) -> list[dict]:
        """Return a random sample of class/method signatures for LLM analysis."""
        import random
        all_classes = []
        for path, fast in self.files.items():
            for cls in fast.classes:
                all_classes.append({
                    "file": path,
                    "namespace": fast.namespace,
                    "class": cls.name,
                    "type": cls.class_type,
                    "base_types": cls.base_types,
                    "interfaces": cls.interfaces,
                    "attributes": cls.attributes,
                    "method_count": len(cls.methods),
                    "methods": [
                        {
                            "name": m.name,
                            "return": m.return_type,
                            "params": [f"{p.type} {p.name}" for p in m.parameters],
                            "modifiers": m.modifiers,
                            "attributes": m.attributes,
                        }
                        for m in cls.methods[:5]
                    ],
                    "constructor_params": [
                        [f"{p.type} {p.name}" for p in c.parameters]
                        for c in cls.constructors
                    ],
                })
        if len(all_classes) > n:
            all_classes = random.sample(all_classes, n)
        return all_classes


_KEYWORDS = {
    "if", "for", "while", "switch", "catch", "return", "throw", "new",
    "else", "do", "try", "finally", "using", "lock", "yield", "await",
    "break", "continue", "case", "default", "goto", "sizeof", "typeof",
    "nameof", "is", "as", "in", "out", "ref", "params", "var", "let",
    "const", "async", "function", "class", "interface", "enum", "struct",
    "public", "private", "protected", "internal", "static", "virtual",
    "override", "abstract", "sealed", "readonly", "extern", "partial",
    "get", "set", "init", "with", "where", "select", "from", "group",
    "orderby", "join", "on", "equals", "into", "ascending", "descending",
    "base", "this", "super", "self",
}


def extract_calls(chunk: str) -> list[str]:
    """Extract method/function call names from a code chunk.

    Matches patterns like: method(), obj.method(), Class.method().
    Excludes keywords, control flow, and declarations.
    """
    import re
    calls: set[str] = set()

    # Qualified calls: obj.method() or Class.method()
    for m in re.finditer(r"(\w[\w.]*)\s*\(", chunk):
        full = m.group(1)
        if full.startswith(".") or full.endswith("."):
            continue
        parts = full.split(".")
        for p in parts:
            if p and p not in _KEYWORDS and not p[0].isupper():
                calls.add(p)
        # Also add the last part for qualified names
        last = parts[-1] if parts else full
        if last and last not in _KEYWORDS:
            calls.add(last)

    # Exclude declarations (method definition follows a keyword or type)
    decl_pattern = re.compile(
        r"(?:public|private|protected|internal|static|virtual|override|abstract|async|function|def)\s+(\w+)\s*\([^)]*\)\s*\{"
    )

    result = []
    for c in sorted(calls):
        # Skip if it looks like a method declaration
        if re.search(rf"\b(?:class|interface|function|def)\s+{c}\b", chunk):
            continue
        if c and len(c) > 1:
            result.append(c)

    return result


class BaseParser(ABC):
    language: str
    required_tools: list[str] = []

    @abstractmethod
    def check_available(self) -> bool:
        """Check that the required runtime is installed."""
        ...

    @abstractmethod
    def parse(self, project_path: str, files: list[str] | None = None) -> ASTIndex:
        """Run the parser, return structured ASTIndex."""
        ...
