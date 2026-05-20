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
                 max_output_tokens: int = 16000) -> BaseChatModel:
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
@click.option("--project", "-p", default=".", type=click.Path(exists=True),
              help="Project root directory")
@click.option("--task", "-t", help="Task description for the agent")
@click.option("--provider", default="openai",
              type=click.Choice(["openai", "deepseek", "anthropic", "local"]),
              help="LLM provider (local = OpenAI-compatible, e.g. Ollama, LM Studio)")
@click.option("--model", "-m", default="gpt-4o", help="Model name")
@click.option("--output", "-o", default=None, help="Output file (stdout if not set)")
@click.option("--gitlab-mr", default=None,
              help="GitLab MR in format 'PROJECT_ID:MR_IID' (e.g. '123:5'). Requires GITLAB_TOKEN env var.")
@click.option("--gitlab-url", default="https://gitlab.com",
              help="GitLab instance URL (default: https://gitlab.com)")
def main(project: str, task: str | None, provider: str, model: str,
         output: str | None, gitlab_mr: str | None, gitlab_url: str) -> None:
    """ctx-builder — collect AI-ready context from a codebase."""
    # GitLab MR mode: build task from merge request
    if gitlab_mr:
        from src.gitlab import GitLabClient
        parts = gitlab_mr.split(":")
        if len(parts) != 2:
            raise click.UsageError("--gitlab-mr format: PROJECT_ID:MR_IID (e.g. '123:5')")
        pid, mr_iid = parts[0], int(parts[1])
        client = GitLabClient(gitlab_url)
        task = client.build_mr_context(pid, mr_iid)
        click.echo(f"GitLab MR: {pid}!{mr_iid}")

    if not task:
        raise click.UsageError("Missing option '--task' / '-t' or '--gitlab-mr'.")

    config = load_config(project)
    index = ProjectIndex.load_or_build(config)
    tools = create_tools(index)

    click.echo(f"Project: {config.project_path}")
    click.echo(f"Detected: {[p.label for p in config.project_types]}")
    click.echo(f"Provider: {provider}, Model: {model}")
    click.echo(f"Task: {task[:120]}{'...' if len(task) > 120 else ''}")
    click.echo()

    # CLI overrides config defaults
    actual_provider = provider or config.model_provider or "openai"
    actual_model = model or config.model_name or "gpt-4o"

    llm = create_model(actual_provider, actual_model)

    agent = CtxBuilderAgent(model=llm, tools=tools)
    result = agent.run(task)

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