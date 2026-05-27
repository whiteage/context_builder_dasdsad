#!/usr/bin/env python3
"""MCP server for ctx-builder — 1 tool: ctx_build.

ctx_build collects AI-optimized context from a codebase (8-section document:
summary, architecture, related files, dependency graph, conventions,
similar implementations, task context, relevant code snippets).

Supports local projects and GitLab repositories (project or MR URLs).
Clones via git, reuses local copies, checks out branches or MR HEADs.
Writes progress to .ctx_build_progress during execution.

Connect to Claude Code via .claude/settings.json:
{
  "mcpServers": {
    "ctx-builder": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "<project-root>"
    }
  }
}

Requires: GITLAB_TOKEN env var for GitLab integration.
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
            description="Build AI-ready context from a codebase. Analyzes repository structure, architecture, conventions, dependencies, and returns optimized context for code review, refactoring, bug fixing, or code generation. Supports GitLab project and MR URLs — clones the repo, runs the full pipeline locally.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Path to project directory. For local projects: path to the repo. For GitLab repos: parent directory where the repo will be cloned (e.g. 'ctx_build_bench'). Use '.' for current directory.",
                    },
                    "task": {
                        "type": "string",
                        "description": "Task description for the agent (e.g. 'Code Review: ...', 'Bug Fixing: ...'). Optional when gitlab_repo is set — auto-generated from MR/project metadata.",
                    },
                    "gitlab_repo": {
                        "type": "string",
                        "description": "GitLab project or MR URL. Clones to {project}/ns/name, reuses local copy if exists. Formats: project URL (https://gitlab.com/group/project), MR URL (.../-/merge_requests/123), short form (group/project or group/project:123). Requires GITLAB_TOKEN env var.",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch to checkout (project mode only, ignored for MRs). Default: project's default branch.",
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
                "required": ["project"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "ctx_build":
            return await _handle_build(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


def _log_progress(project_path: Path, line: str) -> None:
    """Write a progress line to .ctx_build_progress in the project directory."""
    import time as _time
    ts = _time.strftime("%H:%M:%S")
    log_path = project_path / ".ctx_build_progress"
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {line}\n")
    except Exception:
        pass


async def _run_ctx_build(project_path: Path, task: str, args: dict) -> list[TextContent]:
    """Core ctx_build pipeline: index → plan → write. Used by both local and GitLab MR flows."""
    import time as _time

    _log_progress(project_path, f"Starting ctx_build on {project_path.name}")
    t_start = _time.time()

    config = load_config(str(project_path))
    provider = args.get("provider") or config.model_provider
    model = args.get("model") or config.model_name
    if not model:
        return [TextContent(type="text", text="Не указана модель. Установите CTX_BUILDER_DEFAULT_MODEL в .env или передайте параметр model")]
    if not provider:
        return [TextContent(type="text", text="Не указан провайдер. Установите CTX_BUILDER_DEFAULT_PROVIDER в .env или передайте параметр provider")]
    detected = [p.label for p in config.project_types]

    _log_progress(project_path, "Building index...")
    t1 = _time.time()
    index = ProjectIndex.load_or_build(config)
    t_index = _time.time() - t1
    _log_progress(project_path, f"Index done in {t_index:.0f}s")

    from src.cli import create_model
    from src.agent import CtxBuilderAgent
    from src.tools import ToolContext

    ctx = ToolContext(token_budget=config.agent_token_budget)
    llm = create_model(provider, model)
    tools = create_tools(index, ctx)
    agent = CtxBuilderAgent(model=llm, tools=tools, ctx=ctx)

    _log_progress(project_path, "Running LLM agent (planner + writer)...")
    t2 = _time.time()
    result = agent.run(task, token_budget=config.agent_token_budget)
    t_agent = _time.time() - t2
    _log_progress(project_path, f"Agent done in {t_agent:.0f}s")

    if not result:
        return [TextContent(type="text", text="Agent produced no output. The model may have returned empty content. Try a different model or provider.")]

    tokens = count_tokens(result)
    t_total = _time.time() - t_start
    _log_progress(project_path, f"Done — {tokens} tokens, {t_total:.0f}s total")

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
        f"Timing: index={t_index:.0f}s agent={t_agent:.0f}s total={t_total:.0f}s\n"
        f"Output: ~{tokens} tokens\n"
        f"{debug_line}\n\n"
    )

    return [TextContent(type="text", text=header + result)]


def _gitlab_setup_sync(gitlab_repo: str, project_path: Path, branch: str | None) -> tuple[Path, str]:
    """Clone or update a GitLab repo. Runs synchronously (called via asyncio.to_thread).
    Returns (repo_path, auto_generated_task).
    """
    import sys as _sys
    from src.gitlab import GitLabClient, GitLabError, parse_gitlab_url

    gitlab_url, gitlab_project_id, mr_iid = parse_gitlab_url(gitlab_repo)
    client = GitLabClient(gitlab_url)
    print(f"[ctx_build] GitLab: url={gitlab_url} project={gitlab_project_id} mr={mr_iid}", file=_sys.stderr, flush=True)

    if mr_iid is not None:
        mr = client.get_merge_request(gitlab_project_id, mr_iid)
        gitlab_project = client.get_project(gitlab_project_id)
        repo_path = client.setup_mr_repo(gitlab_project_id, mr_iid, str(project_path))
        auto_task = (
            f"Code Review: {mr.title}\n"
            f"MR: {gitlab_project.path_with_namespace}!{mr.iid}\n"
            f"Description: {mr.description[:500] if mr.description else 'N/A'}\n"
            f"Branch: {mr.source_branch} -> {mr.target_branch}\n"
            f"Author: {mr.author}\n"
            f"URL: {mr.web_url}"
        )
    else:
        print(f"[ctx_build] Cloning project (branch={branch}) to {project_path}...", file=_sys.stderr, flush=True)
        repo_path = client.setup_project_repo(gitlab_project_id, str(project_path), branch=branch)
        print(f"[ctx_build] Clone done: {repo_path}", file=_sys.stderr, flush=True)
        gitlab_project = client.get_project(gitlab_project_id)
        auto_task = (
            f"Code Review: Analyze {gitlab_project.path_with_namespace}\n"
            f"Description: {gitlab_project.description[:500] if gitlab_project.description else 'N/A'}\n"
            f"URL: {gitlab_project.web_url}"
        )

    return repo_path, auto_task


async def _handle_build(args: dict) -> list[TextContent]:
    import asyncio as _asyncio

    project = args["project"]
    task = args.get("task", "")
    gitlab_repo = args.get("gitlab_repo", "")

    project_path = Path(project)
    if not project_path.is_absolute():
        project_path = _project_root / project_path
    project_path = project_path.resolve()

    # GitLab mode: clone/fetch first, then run ctx_build
    if gitlab_repo:
        from src.gitlab import GitLabError

        try:
            branch = args.get("branch")
            project_path, new_task = await _asyncio.to_thread(
                _gitlab_setup_sync, gitlab_repo, project_path, branch)
            task = task or new_task
        except GitLabError as e:
            return [TextContent(type="text", text=f"GitLab error: {e}")]

    if not project_path.is_dir():
        return [TextContent(type="text", text=f"Project not found: {project_path}")]

    if not task:
        return [TextContent(type="text", text="Task is required. Provide a task description or use gitlab_repo for auto-generation.")]

    return await _run_ctx_build(project_path, task, args)


def main():
    import asyncio
    async def run():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())
    asyncio.run(run())


if __name__ == "__main__":
    main()
