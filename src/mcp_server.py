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

import sys
from pathlib import Path

# Add project root to path
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))

from dotenv import load_dotenv
load_dotenv(_project_root / ".env")

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.config import load_config
from src.index import ProjectIndex, count_tokens
from src.tools import create_tools

server = Server("ctx-builder")


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
                        "description": "LLM provider. 'local' for OpenAI-compatible endpoints (Ollama, LM Studio, vLLM). Set LOCAL_LLM_URL env var. Defaults to CTX_BUILDER_DEFAULT_PROVIDER env var.",
                    },
                    "model": {
                        "type": "string",
                        "description": "Model name (e.g. gpt-4o, deepseek-chat, claude-opus-4-7). Defaults to CTX_BUILDER_DEFAULT_MODEL env var.",
                    },
                },
                "required": ["project", "task"],
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
        elif name == "ctx_gitlab_mr":
            return await _handle_gitlab_mr(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def _handle_build(args: dict) -> list[TextContent]:
    project = args["project"]
    task = args["task"]

    # Resolve project path
    project_path = Path(project)
    if not project_path.is_absolute():
        project_path = _project_root / project_path
    project_path = project_path.resolve()
    if not project_path.is_dir():
        return [TextContent(type="text", text=f"Project not found: {project_path}")]

    config = load_config(str(project_path))
    provider = args.get("provider") or config.model_provider
    model = args.get("model") or config.model_name
    if not model:
        return [TextContent(type="text", text="Не указана модель. Установите CTX_BUILDER_DEFAULT_MODEL в .env или передайте параметр model")]
    if not provider:
        return [TextContent(type="text", text="Не указан провайдер. Установите CTX_BUILDER_DEFAULT_PROVIDER в .env или передайте параметр provider")]
    detected = [p.label for p in config.project_types]

    # Build index
    index = ProjectIndex.load_or_build(config)

    # Create model
    from src.cli import create_model
    from src.agent import CtxBuilderAgent

    from src.tools import ToolContext
    ctx = ToolContext(token_budget=config.agent_token_budget)
    llm = create_model(provider, model)
    tools = create_tools(index, ctx)
    agent = CtxBuilderAgent(model=llm, tools=tools, ctx=ctx)

    result = agent.run(task, token_budget=config.agent_token_budget)
    if not result:
        return [TextContent(type="text", text="Agent produced no output. The model may have returned empty content. Try a different model or provider.")]

    tokens = count_tokens(result)

    # Debug: show what tools gatherer actually called
    tools_called = getattr(agent, 'last_tools', [])
    steps = getattr(agent, 'last_steps', 0)
    has_code = getattr(agent, 'last_has_code', False)
    tool_sizes = getattr(agent, 'last_tool_bytes', {})
    debug_line = f"[DEBUG] Steps: {steps} | Tools: {', '.join(tools_called)} | Has code: {has_code}"
    if tool_sizes:
        debug_line += " | " + " ".join(f"{k}={v}B" for k, v in tool_sizes.items())

    header = (
        f"Project: {project_path.name}\n"
        f"Detected: {detected}\n"
        f"Provider: {provider}, Model: {model}\n"
        f"Task: {task}\n"
        f"Output: ~{tokens} tokens\n"
        f"{debug_line}\n\n"
    )

    return [TextContent(type="text", text=header + result)]


async def _handle_gitlab_mr(args: dict) -> list[TextContent]:
    from src.gitlab import GitLabClient

    project_id = args["project_id"]
    mr_iid = args["mr_iid"]
    gitlab_url = args.get("gitlab_url", "https://gitlab.com")

    client = GitLabClient(gitlab_url)
    task = client.build_mr_context(project_id, mr_iid)
    return [TextContent(type="text", text=task)]


def main():
    import asyncio
    async def run():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())
    asyncio.run(run())


if __name__ == "__main__":
    main()
