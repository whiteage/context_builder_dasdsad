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

    def build_mr_context(self, project_id: int | str, mr_iid: int) -> str:
        """Build a ctx-builder task description from a GitLab MR.

        Returns a task string ready for ctx-build --task.
        """
        mr = self.get_merge_request(project_id, mr_iid)
        project = self.get_project(project_id)
        changes = self.get_mr_changes(project_id, mr_iid)

        changed_files = [c.get("new_path", c.get("old_path", "")) for c in changes]

        lines = [
            f"Code Review: Analyze merge request !{mr.iid} in {project.path_with_namespace}",
            f"MR Title: {mr.title}",
            f"Description: {mr.description[:300] if mr.description else 'N/A'}",
            f"Branch: {mr.source_branch} -> {mr.target_branch}",
            f"Author: {mr.author}",
            f"Changed files ({len(changed_files)}):",
        ]
        for f in changed_files[:30]:
            lines.append(f"  {f}")
        if len(changed_files) > 30:
            lines.append(f"  ... ({len(changed_files) - 30} more)")

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


class GitLabError(Exception):
    pass


def _encode(value: str | int) -> str:
    """URL-encode a path segment."""
    return urllib.request.quote(str(value), safe="")


# ── Convenience ──────────────────────────────────────────────────────

def list_my_projects(url: str = "https://gitlab.com", token: str | None = None) -> list[GitLabProject]:
    """Quick helper to list your GitLab projects."""
    return GitLabClient(url, token).list_projects()


def analyze_mr(url: str, project_id: int | str, mr_iid: int,
               token: str | None = None) -> str:
    """Analyze a GitLab MR and return an AI-ready context task."""
    client = GitLabClient(url, token)
    return client.build_mr_context(project_id, mr_iid)
