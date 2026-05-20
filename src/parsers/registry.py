"""Parser registry — get the right parser for a language, check availability."""

from __future__ import annotations

import logging
import shutil

from src.parsers.base import BaseParser
from src.parsers.csharp import CSharpParser
from src.parsers.php import PHPParser
from src.parsers.typescript import TypeScriptParser
from src.parsers.dart import DartParser
from src.parsers.unity import UnityParser
from src.parsers.cpp import CppParser

logger = logging.getLogger(__name__)


def _tool_available(command: str) -> bool:
    return shutil.which(command) is not None


PARSER_REGISTRY: dict[str, type[BaseParser]] = {
    "csharp": CSharpParser,
    "php": PHPParser,
    "typescript": TypeScriptParser,
    "dart": DartParser,
    "unity": UnityParser,
    "cpp": CppParser,
}

TOOL_CHECKS: dict[str, list[str]] = {
    "csharp": ["dotnet"],
    "php": ["php"],
    "typescript": ["node"],
    "dart": ["dart"],
    "unity": ["dotnet"],
    "cpp": [],
}


def get_parser(parser_id: str) -> BaseParser | None:
    """Get parser instance by ID. Returns None if parser not found."""
    cls = PARSER_REGISTRY.get(parser_id)
    if cls is None:
        logger.warning(f"No parser registered for: {parser_id}")
        return None
    return cls()


def check_available(parser_id: str) -> bool:
    """Check if a parser's runtime is installed."""
    tools = TOOL_CHECKS.get(parser_id, [])
    for tool in tools:
        if not _tool_available(tool):
            return False
    return True


def available_parsers() -> dict[str, bool]:
    """Return {parser_id: is_available} for all registered parsers."""
    return {pid: check_available(pid) for pid in PARSER_REGISTRY}


def all_parser_ids() -> list[str]:
    return list(PARSER_REGISTRY.keys())
