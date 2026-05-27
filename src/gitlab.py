"""GitLab API integration — analyze merge requests, clone repos, fetch project info."""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GitLabProject:
    id: int
    name: str
    path_with_namespace: str
    web_url: str
    default_branch: str = "main"
    description: str = ""


@dataclass
class GitLabMR:
    id: int
    iid: int
    title: str
    description: str
    source_branch: str
    target_branch: str
    web_url: str
    author: str
    state: str  # opened, merged, closed
    changes: list[dict] = field(default_factory=list)


class GitLabClient:
    """Minimal GitLab REST API client for ctx-builder integration.

    Usage:
        client = GitLabClient("https://gitlab.com", token="glpat-xxx")
        projects = client.list_projects(search="my-project")
        mr = client.get_merge_request(project_id=123, mr_iid=1)
        context = client.build_mr_context(project_id=123, mr_iid=1)
    """

    def __init__(self, url: str = "https://gitlab.com", token: str | None = None):
        self.url = url.rstrip("/")
        self.token = token or os.environ.get("GITLAB_TOKEN", "")
        self._headers = {
            "PRIVATE-TOKEN": self.token,
            "Accept": "application/json",
            "User-Agent": "ctx-builder/0.1",
        }

    def _request(self, path: str, method: str = "GET", data: Any = None) -> dict | list:
        url = f"{self.url}/api/v4{path}"
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=self._headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode(errors="replace")
            raise GitLabError(f"GitLab API error {e.code}: {error_body}") from e
        except urllib.error.URLError as e:
            raise GitLabError(f"Cannot reach GitLab: {e.reason}") from e

    def list_projects(self, search: str = "", owned: bool = True,
                      per_page: int = 20) -> list[GitLabProject]:
        params = f"?owned={str(owned).lower()}&per_page={per_page}"
        if search:
            params += f"&search={search}"
        data = self._request(f"/projects{params}")
        if not isinstance(data, list):
            return []
        return [
            GitLabProject(
                id=p["id"], name=p["name"],
                path_with_namespace=p.get("path_with_namespace", ""),
                web_url=p.get("web_url", ""),
                default_branch=p.get("default_branch", "main"),
                description=p.get("description", ""),
            )
            for p in data
        ]

    def get_project(self, project_id: int | str) -> GitLabProject:
        p = self._request(f"/projects/{_encode(project_id)}")
        if not isinstance(p, dict):
            raise GitLabError(f"Project not found: {project_id}")
        return GitLabProject(
            id=p["id"], name=p["name"],
            path_with_namespace=p.get("path_with_namespace", ""),
            web_url=p.get("web_url", ""),
            default_branch=p.get("default_branch", "main"),
            description=p.get("description", ""),
        )

    def get_merge_request(self, project_id: int | str, mr_iid: int) -> GitLabMR:
        data = self._request(f"/projects/{_encode(project_id)}/merge_requests/{mr_iid}")
        if not isinstance(data, dict):
            raise GitLabError(f"MR not found: {project_id}!{mr_iid}")
        return GitLabMR(
            id=data["id"], iid=data["iid"],
            title=data.get("title", ""),
            description=data.get("description", ""),
            source_branch=data.get("source_branch", ""),
            target_branch=data.get("target_branch", ""),
            web_url=data.get("web_url", ""),
            author=data.get("author", {}).get("username", ""),
            state=data.get("state", "unknown"),
        )

    def get_mr_changes(self, project_id: int | str, mr_iid: int) -> list[dict]:
        """Get file changes for a merge request."""
        data = self._request(f"/projects/{_encode(project_id)}/merge_requests/{mr_iid}/changes")
        if isinstance(data, dict):
            return data.get("changes", [])
        return []

    def get_file_content(self, project_id: int | str, file_path: str,
                         ref: str = "main") -> str | None:
        """Get raw file content from a GitLab project."""
        try:
            data = self._request(
                f"/projects/{_encode(project_id)}/repository/files/{_encode(file_path)}/raw"
                f"?ref={ref}"
            )
            if isinstance(data, (dict, list)):
                return json.dumps(data)
            return str(data)
        except GitLabError:
            return None

    def build_mr_context(self, project_id: int | str, mr_iid: int,
                          include_diffs: bool = True) -> str:
        """Build a ctx-builder task description from a GitLab MR.

        Returns a task string ready for ctx-build --task.
        If include_diffs is True, embeds truncated diffs (max 200 lines/file, max 5 files).
        """
        mr = self.get_merge_request(project_id, mr_iid)
        project = self.get_project(project_id)
        changes = self.get_mr_changes(project_id, mr_iid)

        lines = [
            f"Code Review: Analyze merge request !{mr.iid} in {project.path_with_namespace}",
            f"MR Title: {mr.title}",
            f"Description: {mr.description[:300] if mr.description else 'N/A'}",
            f"Branch: {mr.source_branch} -> {mr.target_branch}",
            f"Author: {mr.author}",
            f"Changed files ({len(changes)}):",
        ]
        for c in changes:
            path = c.get("new_path", c.get("old_path", ""))
            flag = ""
            if c.get("new_file"):
                flag = " [new]"
            elif c.get("deleted_file"):
                flag = " [deleted]"
            elif c.get("renamed_file"):
                flag = f" [renamed from {c.get('old_path', '?')}]"
            lines.append(f"  {path}{flag}")

        if include_diffs and changes:
            lines.append("")
            lines.append("## Diffs")
            diff_count = 0
            MAX_DIFF_FILES = 5
            MAX_DIFF_LINES = 200
            for c in changes:
                if diff_count >= MAX_DIFF_FILES:
                    lines.append(f"... ({len(changes) - MAX_DIFF_FILES} more files)")
                    break
                diff = c.get("diff", "")
                path = c.get("new_path", c.get("old_path", ""))
                if not diff or diff.startswith("Binary files"):
                    continue
                diff_lines = diff.split("\n")
                if len(diff_lines) > MAX_DIFF_LINES:
                    diff = "\n".join(diff_lines[:MAX_DIFF_LINES])
                    diff += f"\n... [truncated, {len(diff_lines) - MAX_DIFF_LINES} more lines]"
                lines.append(f"### {path}")
                lines.append("```diff")
                lines.append(diff)
                lines.append("```")
                lines.append("")
                diff_count += 1

        return "\n".join(lines)

    def clone_project(self, project_id: int | str, target_dir: str | Path) -> Path:
        """Clone a GitLab project to a local directory using git.

        Requires git to be installed and the token to have read_repository access.
        Returns the path to the cloned directory.
        """
        import subprocess
        project = self.get_project(project_id)
        target = Path(target_dir).resolve()

        clone_url = f"{self.url}/{project.path_with_namespace}.git"
        # Inject token into URL for authentication
        if self.token:
            proto, rest = clone_url.split("://", 1)
            clone_url = f"{proto}://oauth2:{self.token}@{rest}"

        cmd = ["git", "clone", "--depth", "1", clone_url, str(target)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            raise GitLabError(f"Clone failed: {result.stderr[:300]}")

        return target

    def setup_mr_repo(self, project_id: int | str, mr_iid: int,
                      parent_dir: str | Path = "ctx_build_bench") -> Path:
        """Clone a GitLab project and check out the MR's source branch HEAD.

        Clones into ``parent_dir / namespace / project_name /``.
        If the repo already exists, fetches and checks out the MR ref
        instead of re-cloning.

        Uses GitLab's ``refs/merge-requests/<iid>/head`` ref to get the
        exact state proposed in the MR, regardless of whether the source
        branch lives in the same repo or a fork.
        """
        import subprocess

        project = self.get_project(project_id)
        target = Path(parent_dir).resolve() / project.path_with_namespace

        clone_url = f"{self.url}/{project.path_with_namespace}.git"
        if self.token:
            proto, rest = clone_url.split("://", 1)
            clone_url = f"{proto}://oauth2:{self.token}@{rest}"

        mr_ref = f"refs/merge-requests/{mr_iid}/head"

        if (target / ".git").is_dir():
            # Repo already cloned — fetch MR ref and checkout
            _run_git(["git", "-C", str(target), "fetch", "--depth=1",
                       "origin", mr_ref], timeout=120)
            _run_git(["git", "-C", str(target), "checkout", "FETCH_HEAD"], timeout=30)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            _run_git(["git", "clone", "--depth=1", clone_url, str(target)], timeout=300)
            _run_git(["git", "-C", str(target), "fetch", "--depth=1",
                       "origin", mr_ref], timeout=120)
            _run_git(["git", "-C", str(target), "checkout", "FETCH_HEAD"], timeout=30)

        return target


    def setup_project_repo(self, project_id: int | str,
                           parent_dir: str | Path = "ctx_build_bench",
                           branch: str | None = None) -> Path:
        """Ensure a local clone exists, is up to date, and on the right branch.

        1. If repo already exists locally → fetch + checkout branch + fast-forward
        2. If not → clone --depth=1

        Returns the path to the repo directory.
        """
        project = self.get_project(project_id)
        target = Path(parent_dir).resolve() / project.path_with_namespace
        target_branch = branch or project.default_branch

        clone_url = f"{self.url}/{project.path_with_namespace}.git"
        if self.token:
            proto, rest = clone_url.split("://", 1)
            clone_url = f"{proto}://oauth2:{self.token}@{rest}"

        if (target / ".git").is_dir():
            # Repo exists — fetch latest and checkout target branch
            import sys as _sys
            print(f"[gitlab] Fetching {target_branch} in {target}...", file=_sys.stderr, flush=True)
            _run_git(["git", "-C", str(target), "fetch", "--depth=1",
                       "origin", target_branch], timeout=120)
            _run_git(["git", "-C", str(target), "checkout", target_branch], timeout=30)
            _run_git(["git", "-C", str(target), "reset", "--hard",
                       f"origin/{target_branch}"], timeout=30)
            print(f"[gitlab] Checked out {target_branch} in {target}", file=_sys.stderr, flush=True)
        else:
            import sys as _sys
            print(f"[gitlab] Cloning {clone_url.replace(self.token, '***')} to {target}...", file=_sys.stderr, flush=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            _run_git(["git", "clone", "--depth=1", "--branch", target_branch,
                       clone_url, str(target)], timeout=300)
            print(f"[gitlab] Clone done: {target}", file=_sys.stderr, flush=True)

        return target


def _run_git(cmd: list[str], timeout: int = 300) -> None:
    """Run a git command, raise GitLabError on failure."""
    import subprocess

    env = {
        **__import__("os").environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_ASKPASS": "echo",
        "GCM_INTERACTIVE": "Never",
    }
    # Inject credential disable flags right after 'git'
    parts = list(cmd)
    parts.insert(1, "-c")
    parts.insert(2, "credential.helper=")
    result = subprocess.run(
        parts, capture_output=True, text=True, timeout=timeout,
        env=env, stdin=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise GitLabError(f"Git command failed: {' '.join(cmd)}\n{result.stderr[:300]}")


class GitLabError(Exception):
    pass


def _encode(value: str | int) -> str:
    """URL-encode a path segment."""
    return urllib.request.quote(str(value), safe="")


def parse_gitlab_url(url: str) -> tuple[str, str, int | None]:
    """Parse a GitLab URL into (gitlab_url, project_id, mr_iid_or_none).

    Supports:
    - MR URL: https://gitlab.com/group/project/-/merge_requests/123
    - Project URL: https://gitlab.com/group/project
    - Self-hosted: https://gitlab.example.com/group/sub/project/-/merge_requests/42
    - Short MR: project_id:mr_iid (e.g. '123:5' or 'group/project:5')
    - Short project: group/project

    Returns mr_iid=None for plain project URLs.

    Raises GitLabError if the URL can't be parsed.
    """
    url = url.strip()

    # Short form: project_id:mr_iid or group/project
    if "://" not in url:
        # MR short form: has a colon followed by digits at the end
        if ":" in url:
            parts = url.rsplit(":", 1)
            if len(parts) == 2 and parts[1].isdigit():
                return ("https://gitlab.com", parts[0], int(parts[1]))
        # Project short form: group/project (no colon+digits)
        if "/" in url and " " not in url:
            return ("https://gitlab.com", url, None)
        raise GitLabError(
            f"Cannot parse GitLab URL: {url}\n"
            "Expected: https://gitlab.com/group/project or\n"
            "https://gitlab.com/group/project/-/merge_requests/123 or\n"
            "project_id:mr_iid (e.g. '123:5')"
        )

    # Full URL: try MR pattern first, then project pattern
    import re as _re

    mr_match = _re.match(
        r"^(https?://[^/]+)/(.+)/-/merge_requests/(\d+)/?$",
        url
    )
    if mr_match:
        return (mr_match.group(1), mr_match.group(2).rstrip("/"), int(mr_match.group(3)))

    # Plain project URL: https://gitlab.com/group/project (with or without trailing slash)
    project_match = _re.match(
        r"^(https?://[^/]+)/([^/]+(?:/[^/]+)+)/?$",
        url
    )
    if project_match:
        return (project_match.group(1), project_match.group(2).rstrip("/"), None)

    raise GitLabError(
        f"Cannot parse GitLab URL: {url}\n"
        "Expected: https://gitlab.com/group/project or\n"
        "https://gitlab.com/group/project/-/merge_requests/123 or\n"
        "project_id:mr_iid (e.g. '123:5')"
    )


def parse_mr_url(url: str) -> tuple[str, str, int]:
    """Backwards-compatible wrapper. Use parse_gitlab_url instead.

    Raises GitLabError if the URL is not an MR URL (no mr_iid).
    """
    base, project, mr_iid = parse_gitlab_url(url)
    if mr_iid is None:
        raise GitLabError(f"Not a merge request URL: {url}\nExpected MR URL format: .../-/merge_requests/123 or project_id:mr_iid")
    return (base, project, mr_iid)


# ── Convenience ──────────────────────────────────────────────────────

def list_my_projects(url: str = "https://gitlab.com", token: str | None = None) -> list[GitLabProject]:
    """Quick helper to list your GitLab projects."""
    return GitLabClient(url, token).list_projects()


def analyze_mr(url: str, project_id: int | str, mr_iid: int,
               token: str | None = None) -> str:
    """Analyze a GitLab MR and return an AI-ready context task."""
    client = GitLabClient(url, token)
    return client.build_mr_context(project_id, mr_iid)
