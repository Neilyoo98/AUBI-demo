"""GitHub issue and repository helpers for the AUBI demo.

The functions in this module intentionally avoid third-party dependencies so
the demo can run in a minimal Python environment. They use GitHub's REST API
and require ``GITHUB_TOKEN`` for operations that need private data or writes.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request

from backend.config import load_local_env


DEFAULT_GITHUB_API_URL = "https://api.github.com"


class GitHubError(RuntimeError):
    """Raised when GitHub returns an error response."""


@dataclass(frozen=True)
class IssueRef:
    repo: str
    number: int


def parse_issue_ref(issue_ref: str) -> IssueRef:
    """Parse ``owner/repo#123`` or a GitHub issue URL into an issue ref."""
    issue_ref = issue_ref.strip()
    if not issue_ref:
        raise ValueError("issue_ref must not be empty")

    if issue_ref.startswith(("http://", "https://")):
        parsed = parse.urlparse(issue_ref)
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 4 and parts[2] == "issues":
            return IssueRef(repo=f"{parts[0]}/{parts[1]}", number=_parse_issue_number(parts[3]))
        raise ValueError(f"unsupported GitHub issue URL: {issue_ref}")

    if "#" not in issue_ref:
        raise ValueError("issue_ref must look like 'owner/repo#123'")

    repo, number = issue_ref.rsplit("#", 1)
    repo = repo.strip()
    if len(repo.split("/")) != 2:
        raise ValueError("repo must look like 'owner/repo'")
    return IssueRef(repo=repo, number=_parse_issue_number(number))


def read_issue(issue_ref: str) -> dict[str, Any]:
    """Read a GitHub issue.

    Args:
        issue_ref: ``owner/repo#123`` or a full GitHub issue URL.

    Returns:
        A compact issue dictionary suitable for feeding into the AUBI graph.
    """
    ref = parse_issue_ref(issue_ref)
    issue = _github_json("GET", f"/repos/{ref.repo}/issues/{ref.number}")
    return {
        "repo": ref.repo,
        "number": issue["number"],
        "title": issue.get("title") or "",
        "body": issue.get("body") or "",
        "state": issue.get("state") or "",
        "user": (issue.get("user") or {}).get("login"),
        "labels": [label.get("name") for label in issue.get("labels", []) if label.get("name")],
        "html_url": issue.get("html_url"),
        "created_at": issue.get("created_at"),
        "updated_at": issue.get("updated_at"),
    }


def read_repo_files(repo: str, paths: list[str]) -> dict[str, str]:
    """Read one or more text files from a GitHub repository's default branch."""
    repo = _normalize_repo(repo)
    if not paths:
        return {}

    files: dict[str, str] = {}
    for path in paths:
        normalized_path = _normalize_repo_path(path)
        encoded_path = parse.quote(normalized_path, safe="")
        item = _github_json("GET", f"/repos/{repo}/contents/{encoded_path}")
        if isinstance(item, list) or item.get("type") != "file":
            raise GitHubError(f"{normalized_path} is not a file")
        if item.get("encoding") != "base64":
            raise GitHubError(f"unsupported encoding for {normalized_path}: {item.get('encoding')}")
        files[normalized_path] = _decode_content(item.get("content") or "")
    return files


def get_latest_open_issue(repo: str) -> dict[str, Any] | None:
    """Return the newest open issue in a repository, or ``None`` if there is none."""
    repo = _normalize_repo(repo)
    issues = _github_json(
        "GET",
        f"/repos/{repo}/issues?state=open&sort=created&direction=desc&per_page=10",
    )
    for issue in issues:
        if "pull_request" in issue:
            continue
        return {
            "repo": repo,
            "number": issue["number"],
            "title": issue.get("title") or "",
            "body": issue.get("body") or "",
            "state": issue.get("state") or "",
            "user": (issue.get("user") or {}).get("login"),
            "labels": [label.get("name") for label in issue.get("labels", []) if label.get("name")],
            "html_url": issue.get("html_url"),
            "created_at": issue.get("created_at"),
            "updated_at": issue.get("updated_at"),
        }
    return None


def create_fix_pr(
    repo: str,
    branch_name: str,
    file_changes: dict[str, str],
    title: str,
    body: str,
    *,
    base: str = "main",
) -> dict[str, Any]:
    """Create or update a branch with file changes, then open a pull request.

    ``file_changes`` maps repository-relative paths to complete new file
    contents. Existing files are updated; missing files are created.
    """
    repo = _normalize_repo(repo)
    branch_name = _normalize_branch(branch_name)
    if not file_changes:
        raise ValueError("file_changes must contain at least one file")
    if not title.strip():
        raise ValueError("title must not be empty")

    base_ref = _github_json("GET", f"/repos/{repo}/git/ref/heads/{parse.quote(base, safe='')}")
    base_sha = base_ref["object"]["sha"]
    _ensure_branch(repo, branch_name, base_sha)

    changed_paths: list[str] = []
    for path, content in file_changes.items():
        normalized_path = _normalize_repo_path(path)
        if not isinstance(content, str):
            raise TypeError(f"content for {normalized_path} must be a string")
        if _put_file(repo, branch_name, normalized_path, content):
            changed_paths.append(normalized_path)

    if not changed_paths:
        raise GitHubError("all requested file changes were no-ops")

    pr = _create_or_find_pr(repo, branch_name, base, title.strip(), body)
    return {
        "repo": repo,
        "branch": branch_name,
        "base": base,
        "changed_paths": changed_paths,
        "number": pr["number"],
        "html_url": pr["html_url"],
        "state": pr["state"],
    }


def _ensure_branch(repo: str, branch_name: str, base_sha: str) -> None:
    encoded_branch = parse.quote(branch_name, safe="")
    try:
        _github_json("GET", f"/repos/{repo}/git/ref/heads/{encoded_branch}")
    except GitHubError as exc:
        if "404" not in str(exc):
            raise
        _github_json(
            "POST",
            f"/repos/{repo}/git/refs",
            {"ref": f"refs/heads/{branch_name}", "sha": base_sha},
        )


def _put_file(repo: str, branch_name: str, path: str, content: str) -> bool:
    encoded_path = parse.quote(path, safe="")
    current_sha: str | None = None
    try:
        current = _github_json(
            "GET",
            f"/repos/{repo}/contents/{encoded_path}?ref={parse.quote(branch_name, safe='')}",
        )
        if current.get("type") != "file":
            raise GitHubError(f"{path} exists but is not a file")
        current_sha = current.get("sha")
        if current.get("encoding") == "base64" and _decode_content(current.get("content") or "") == content:
            return False
    except GitHubError as exc:
        if "404" not in str(exc):
            raise

    payload: dict[str, Any] = {
        "message": f"Update {path}",
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch_name,
    }
    if current_sha:
        payload["sha"] = current_sha

    _github_json("PUT", f"/repos/{repo}/contents/{encoded_path}", payload)
    return True


def _create_or_find_pr(repo: str, branch_name: str, base: str, title: str, body: str) -> dict[str, Any]:
    open_prs = _github_json(
        "GET",
        f"/repos/{repo}/pulls?head={parse.quote(repo.split('/')[0] + ':' + branch_name, safe='')}"
        f"&base={parse.quote(base, safe='')}&state=open",
    )
    if open_prs:
        return open_prs[0]

    return _github_json(
        "POST",
        f"/repos/{repo}/pulls",
        {"title": title, "head": branch_name, "base": base, "body": body},
    )


def _github_json(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    load_local_env()
    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "aubi-demo",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    api_url = os.getenv("GITHUB_API_URL", DEFAULT_GITHUB_API_URL).rstrip("/")
    req = request.Request(f"{api_url}{path}", data=data, headers=headers, method=method.upper())
    try:
        with request.urlopen(req, timeout=20) as response:
            body = response.read()
            if not body:
                return None
            return json.loads(body.decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GitHubError(f"GitHub API {method} {path} failed with {exc.code}: {detail}") from exc
    except error.URLError as exc:
        raise GitHubError(f"GitHub API {method} {path} failed: {exc.reason}") from exc


def _decode_content(content: str) -> str:
    compact = "".join(content.splitlines())
    return base64.b64decode(compact).decode("utf-8")


def _normalize_repo(repo: str) -> str:
    repo = repo.strip().strip("/")
    if len(repo.split("/")) != 2:
        raise ValueError("repo must look like 'owner/repo'")
    return repo


def _normalize_repo_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip().lstrip("/")
    if not normalized or normalized == ".":
        raise ValueError("file paths must not be empty")
    if any(part in {"", ".", ".."} for part in normalized.split("/")):
        raise ValueError(f"unsafe repo path: {path}")
    return normalized


def _normalize_branch(branch_name: str) -> str:
    branch_name = branch_name.strip().strip("/")
    if not branch_name or branch_name.startswith("-") or ".." in branch_name:
        raise ValueError(f"unsafe branch name: {branch_name}")
    return branch_name


def _parse_issue_number(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError(f"invalid issue number: {value}") from exc
    if number <= 0:
        raise ValueError("issue number must be positive")
    return number
