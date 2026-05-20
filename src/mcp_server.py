#!/usr/bin/env python3
"""MCP server for ctx-builder — exposes project context tools to Claude Code.

Connect Claude Code to this server by adding to .claude/settings.json:
{
  "mcpServers": {
    "ctx-builder": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "<project-root>"
    }
  }
}
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Add project root to path
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.config import load_config
from src.index import ProjectIndex, count_tokens
from src.tools import create_tools

server = Server("ctx-builder")


def _build_index(project_path: str) -> ProjectIndex:
    config = load_config(project_path)
    return ProjectIndex.load_or_build(config)


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="ctx_build",
            description="Build AI-ready context from a codebase. Analyzes repository structure, architecture, conventions, dependencies, and returns optimized context for code review, refactoring, bug fixing, or code generation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Path to project directory (absolute or relative to ctx-builder root). Use '.' for current directory.",
                    },
                    "task": {
                        "type": "string",
                        "description": "Task description: 'Code Review: ...', 'Bug Fixing: ...', 'Code Generation: ...', 'Refactoring: ...', 'Documentation: ...', 'Architecture analysis: ...'",
                    },
                    "provider": {
                        "type": "string",
                        "enum": ["openai", "deepseek", "anthropic", "local"],
                        "default": "deepseek",
                        "description": "LLM provider. 'local' for OpenAI-compatible endpoints (Ollama, LM Studio, vLLM). Set LOCAL_LLM_URL env var.",
                    },
                    "model": {
                        "type": "string",
                        "default": "deepseek-chat",
                        "description": "Model name (e.g. gpt-4o, deepseek-chat, claude-opus-4-7).",
                    },
                },
                "required": ["project", "task"],
            },
        ),
        Tool(
            name="ctx_summary",
            description="Get a quick summary of a project: file counts, languages, structure tree, detected project types. No LLM call — instant.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Path to project directory.",
                    },
                },
                "required": ["project"],
            },
        ),
        Tool(
            name="ctx_search",
            description="Search for a class, method, or symbol in an indexed project. Returns matching symbols with their file paths and signatures.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Path to project directory.",
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Symbol name to search for (case-insensitive partial match).",
                    },
                },
                "required": ["project", "symbol"],
            },
        ),
        Tool(
            name="ctx_dependencies",
            description="Get file dependencies: what a file imports and what imports it.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Path to project directory.",
                    },
                    "file": {
                        "type": "string",
                        "description": "File path relative to project root.",
                    },
                },
                "required": ["project", "file"],
            },
        ),
        Tool(
            name="ctx_entities",
            description="Classify all source files by entity type: controllers, services, repositories, DTOs, entities, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Path to project directory.",
                    },
                },
                "required": ["project"],
            },
        ),
        Tool(
            name="ctx_gitlab_mr",
            description="Fetch a GitLab merge request and build a context task for code review. Requires GITLAB_TOKEN env var.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "GitLab project ID (numeric or URL-encoded path).",
                    },
                    "mr_iid": {
                        "type": "integer",
                        "description": "Merge request internal ID (the number after ! in GitLab).",
                    },
                    "gitlab_url": {
                        "type": "string",
                        "default": "https://gitlab.com",
                        "description": "GitLab instance URL.",
                    },
                },
                "required": ["project_id", "mr_iid"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "ctx_build":
            return await _handle_build(arguments)
        elif name == "ctx_summary":
            return await _handle_summary(arguments)
        elif name == "ctx_search":
            return await _handle_search(arguments)
        elif name == "ctx_dependencies":
            return await _handle_deps(arguments)
        elif name == "ctx_entities":
            return await _handle_entities(arguments)
        elif name == "ctx_gitlab_mr":
            return await _handle_gitlab_mr(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _handle_build(args: dict) -> list[TextContent]:
    project = args["project"]
    task = args["task"]
    provider = args.get("provider", "deepseek")
    model = args.get("model", "deepseek-chat")

    # Resolve project path
    project_path = Path(project)
    if not project_path.is_absolute():
        project_path = _project_root / project_path
    project_path = project_path.resolve()
    if not project_path.is_dir():
        return [TextContent(type="text", text=f"Project not found: {project_path}")]

    config = load_config(str(project_path))
    detected = [p.label for p in config.project_types]

    # Build index
    index = ProjectIndex.load_or_build(config)

    # For summary/search/deps/entities, we don't need the LLM — we can return structured data directly
    # For ctx_build, we need the full agent with LLM

    # Create model
    from src.cli import create_model
    from src.agent import CtxBuilderAgent

    llm = create_model(provider, model)
    tools = create_tools(index)
    agent = CtxBuilderAgent(model=llm, tools=tools)

    result = agent.run(task)
    if not result:
        return [TextContent(type="text", text="Agent produced no output. The model may have returned empty content. Try a different model or provider.")]

    tokens = count_tokens(result)

    header = (
        f"Project: {project_path.name}\n"
        f"Detected: {detected}\n"
        f"Provider: {provider}, Model: {model}\n"
        f"Task: {task}\n"
        f"Output: ~{tokens} tokens\n\n"
    )

    return [TextContent(type="text", text=header + result)]


async def _handle_summary(args: dict) -> list[TextContent]:
    project_path = _resolve_path(args["project"])
    if isinstance(project_path, str):
        return [TextContent(type="text", text=project_path)]

    config = load_config(str(project_path))
    index = ProjectIndex.load_or_build(config)
    return [TextContent(type="text", text=index.summarize())]


async def _handle_search(args: dict) -> list[TextContent]:
    project_path = _resolve_path(args["project"])
    if isinstance(project_path, str):
        return [TextContent(type="text", text=project_path)]

    config = load_config(str(project_path))
    index = ProjectIndex.load_or_build(config)

    symbol = args["symbol"]
    results = index.find_symbols(name=symbol)

    if not results:
        return [TextContent(type="text", text=f"No symbols found matching '{symbol}'")]

    lines = [f"Found {len(results)} matching '{symbol}':"]
    for r in results[:30]:
        if r["type"] == "method":
            params = ", ".join(f"{p.type} {p.name}" for p in r["parameters"])
            lines.append(f"  [{r['type']}] {r['class_name']}.{r['name']}({params}) in {r['path']}")
        elif r["type"] == "function":
            params = ", ".join(f"{p.type} {p.name}" for p in r["parameters"])
            lines.append(f"  [{r['type']}] {r['name']}({params}) in {r['path']}")
        else:
            lines.append(f"  [{r['type']}] {r['name']} in {r['path']}")
            for m in r.get("methods", [])[:3]:
                params = ", ".join(f"{p.type} {p.name}" for p in m.parameters)
                lines.append(f"    {m.return_type or 'void'} {m.name}({params})")
    if len(results) > 30:
        lines.append(f"  ... ({len(results) - 30} more)")
    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_deps(args: dict) -> list[TextContent]:
    project_path = _resolve_path(args["project"])
    if isinstance(project_path, str):
        return [TextContent(type="text", text=project_path)]

    config = load_config(str(project_path))
    index = ProjectIndex.load_or_build(config)

    file_path = args["file"]
    if file_path not in index.repo.files:
        return [TextContent(type="text", text=f"File not found: {file_path}")]

    deps = index.get_dependencies(file_path)
    dents = index.get_dependents(file_path)

    lines = [f"Dependencies for: {file_path}"]
    lines.append(f"  Imports ({len(deps)}):")
    for d in deps[:20]:
        lines.append(f"    {d}")
    lines.append(f"  Imported by ({len(dents)}):")
    for d in dents[:20]:
        lines.append(f"    {d}")
    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_entities(args: dict) -> list[TextContent]:
    project_path = _resolve_path(args["project"])
    if isinstance(project_path, str):
        return [TextContent(type="text", text=project_path)]

    config = load_config(str(project_path))
    index = ProjectIndex.load_or_build(config)

    result = index.classify_entities()
    lines = [f"Entity classification ({sum(len(v) for v in result.values())} files):"]
    for etype, files in sorted(result.items()):
        if files:
            lines.append(f"  {etype}: {len(files)} files — {', '.join(Path(f).name for f in files[:5])}")
    return [TextContent(type="text", text="\n".join(lines))]


async def _handle_gitlab_mr(args: dict) -> list[TextContent]:
    from src.gitlab import GitLabClient

    project_id = args["project_id"]
    mr_iid = args["mr_iid"]
    gitlab_url = args.get("gitlab_url", "https://gitlab.com")

    client = GitLabClient(gitlab_url)
    task = client.build_mr_context(project_id, mr_iid)
    return [TextContent(type="text", text=task)]


def _resolve_path(project: str) -> Path | str:
    p = Path(project)
    if not p.is_absolute():
        p = _project_root / p
    p = p.resolve()
    if not p.is_dir():
        return f"Project not found: {p}"
    return p


def main():
    import asyncio
    async def run():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())
    asyncio.run(run())


if __name__ == "__main__":
    main()
