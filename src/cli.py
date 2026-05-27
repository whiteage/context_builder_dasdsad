import os
import sys
from pathlib import Path

import click

# Fix Unicode output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.agent import CtxBuilderAgent
from src.config import load_config
from src.index import ProjectIndex, count_tokens
from src.tools import create_tools

load_dotenv()
def create_model(provider: str, model_name: str,
                 max_output_tokens: int = 32000) -> BaseChatModel:
    if provider == "openai":
        return ChatOpenAI(model=model_name, temperature=0,
                          max_tokens=max_output_tokens)
    if provider == "deepseek":
        return ChatOpenAI(model=model_name,
                          base_url="https://api.deepseek.com/v1",
                          api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
                          temperature=0,
                          max_tokens=max_output_tokens,
                          extra_body={"thinking": {"type": "disabled"}}
                          )
    if provider == "anthropic":
        return ChatAnthropic(model=model_name, temperature=0,
                             max_tokens=max_output_tokens)
    if provider == "local":
        base_url = os.environ.get("LOCAL_LLM_URL", "http://localhost:11434/v1")
        api_key = os.environ.get("LOCAL_LLM_API_KEY", "not-needed")
        return ChatOpenAI(model=model_name,
                          base_url=base_url,
                          api_key=api_key,
                          temperature=0,
                          max_tokens=max_output_tokens)
    raise ValueError(f"Unknown provider {provider}")


@click.command()
@click.option("--project", "-p", default=".", type=click.Path(),
              help="Project root directory. For GitLab MRs: parent directory where the repo will be cloned.")
@click.option("--task", "-t", help="Task description (auto-generated for GitLab MRs)")
@click.option("--provider", default=None,
              type=click.Choice(["openai", "deepseek", "anthropic", "local"]),
              help="LLM provider (defaults to CTX_BUILDER_DEFAULT_PROVIDER env var)")
@click.option("--model", "-m", default=None, help="Model name (defaults to CTX_BUILDER_DEFAULT_MODEL env var)")
@click.option("--output", "-o", default=None, help="Output file (stdout if not set)")
@click.option("--gitlab-repo", default=None,
              help="GitLab project or MR URL. Project: https://gitlab.com/group/project. MR: https://gitlab.com/group/project/-/merge_requests/123. Short: group/project or group/project:123. Reuses local clone if exists. Requires GITLAB_TOKEN env var.")
@click.option("--branch", "-b", default=None,
              help="Branch to checkout (project mode only, ignored for MRs).")
def main(project: str, task: str | None, provider: str, model: str,
         output: str | None, gitlab_repo: str | None, branch: str | None) -> None:
    """ctx-builder — collect AI-ready context from a codebase."""
    project_path = Path(project).resolve()

    # GitLab mode: ensure local repo + up to date, then run ctx_build
    if gitlab_repo:
        from src.gitlab import GitLabClient, GitLabError, parse_gitlab_url

        try:
            gitlab_url, gitlab_project_id, mr_iid = parse_gitlab_url(gitlab_repo)
            client = GitLabClient(gitlab_url)
            gitlab_project = client.get_project(gitlab_project_id)

            if mr_iid is not None:
                mr = client.get_merge_request(gitlab_project_id, mr_iid)
                project_path = client.setup_mr_repo(gitlab_project_id, mr_iid, str(project_path))
                click.echo(f"GitLab MR: {gitlab_project.path_with_namespace}!{mr.iid}")
                click.echo(f"Title: {mr.title}")
                click.echo(f"Author: {mr.author}")
                click.echo(f"Checked out MR HEAD at: {project_path}")
                task = task or (
                    f"Code Review: {mr.title}\n"
                    f"MR: {gitlab_project.path_with_namespace}!{mr.iid}\n"
                    f"Description: {mr.description[:500] if mr.description else 'N/A'}\n"
                    f"Branch: {mr.source_branch} -> {mr.target_branch}\n"
                    f"Author: {mr.author}\n"
                    f"URL: {mr.web_url}"
                )
            else:
                project_path = client.setup_project_repo(
                    gitlab_project_id, str(project_path), branch=branch)
                click.echo(f"GitLab project: {gitlab_project.path_with_namespace}")
                click.echo(f"Branch: {branch or gitlab_project.default_branch}")
                click.echo(f"Path: {project_path}")
                task = task or (
                    f"Code Review: Analyze {gitlab_project.path_with_namespace}\n"
                    f"Description: {gitlab_project.description[:500] if gitlab_project.description else 'N/A'}\n"
                    f"URL: {gitlab_project.web_url}"
                )
        except GitLabError as e:
            raise click.ClickException(f"GitLab error: {e}")

    if not project_path.is_dir():
        raise click.ClickException(f"Project not found: {project_path}")

    if not task:
        raise click.UsageError("Missing option '--task' / '-t' or '--gitlab-repo'.")

    config = load_config(str(project_path))

    # CLI overrides config defaults
    actual_provider = provider or config.model_provider
    actual_model = model or config.model_name
    if not actual_model:
        raise click.UsageError("Не указана модель. Установите CTX_BUILDER_DEFAULT_MODEL в .env или передайте --model")
    if not actual_provider:
        raise click.UsageError("Не указан провайдер. Установите CTX_BUILDER_DEFAULT_PROVIDER в .env или передайте --provider")

    index = ProjectIndex.load_or_build(config)

    from src.tools import ToolContext
    ctx = ToolContext(token_budget=config.agent_token_budget)
    tools = create_tools(index, ctx)

    click.echo(f"Project: {config.project_path}")
    click.echo(f"Detected: {[p.label for p in config.project_types]}")
    click.echo(f"Provider: {actual_provider}, Model: {actual_model}")
    click.echo(f"Task: {task[:120]}{'...' if len(task) > 120 else ''}")
    click.echo()

    llm = create_model(actual_provider, actual_model)

    agent = CtxBuilderAgent(model=llm, tools=tools, ctx=ctx)
    result = agent.run(task, token_budget=config.agent_token_budget)

    tokens = count_tokens(result)
    max_tokens = config.max_tokens
    click.echo(f"\n[Output: ~{tokens} tokens", nl=False)
    if tokens > max_tokens:
        click.echo(f" — exceeds limit of {max_tokens} tokens]")
    else:
        click.echo(f" — limit is {max_tokens} tokens]")

    if output:
        Path(output).write_text(result, encoding="utf-8")
        click.echo(f"Saved to {output}")
    else:
        click.echo(result)