import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

import httpx

from lib.schemas import CommitSignal, MilestoneSignal, ReleaseSignal

GITHUB_API = "https://api.github.com"
_GITHUB_REMOTE_RE = re.compile(
    r"github\.com[:/](?P<owner>[^/]+)/(?P<name>[^/]+?)(?:\.git)?$"
)


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def parse_github_remote(url: str) -> tuple[str, str] | None:
    match = _GITHUB_REMOTE_RE.search(url.strip())
    if not match:
        return None
    return match.group("owner"), match.group("name")


def resolve_repo(
    owner: str,
    name: str,
    local_path: str | Path,
) -> tuple[str, str, Path]:
    repo_path = Path(local_path)
    if not repo_path.is_absolute():
        repo_path = Path(__file__).resolve().parent.parent.parent / repo_path

    resolved_owner, resolved_name = owner, name
    if not resolved_owner or not resolved_name:
        detected = detect_github_repo(repo_path)
        if detected:
            resolved_owner = resolved_owner or detected[0]
            resolved_name = resolved_name or detected[1]

    return resolved_owner, resolved_name, repo_path


def detect_github_repo(repo_path: Path) -> tuple[str, str] | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return parse_github_remote(result.stdout.strip())


def is_git_repo(repo_path: Path) -> bool:
    git_dir = repo_path / ".git"
    return git_dir.exists()


def collect_local_commits(repo_path: Path, since: datetime) -> list[CommitSignal]:
    if not is_git_repo(repo_path):
        return []

    since_arg = since.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "log",
                f"--since={since_arg}",
                "--no-merges",
                "--pretty=format:COMMIT %H|%s|%an|%aI",
                "--numstat",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []

    commits: list[CommitSignal] = []
    current: dict[str, str] | None = None
    files_changed = 0
    insertions = 0
    deletions = 0

    def flush() -> None:
        nonlocal current, files_changed, insertions, deletions
        if not current:
            return
        commits.append(
            CommitSignal(
                sha=current["sha"],
                subject=current["subject"],
                author=current["author"],
                committed_at=datetime.fromisoformat(current["committed_at"]),
                files_changed=files_changed,
                insertions=insertions,
                deletions=deletions,
            )
        )
        current = None
        files_changed = 0
        insertions = 0
        deletions = 0

    for line in result.stdout.splitlines():
        if line.startswith("COMMIT "):
            flush()
            _, payload = line.split(" ", 1)
            sha, subject, author, committed_at = payload.split("|", 3)
            current = {
                "sha": sha,
                "subject": subject,
                "author": author,
                "committed_at": committed_at,
            }
            continue
        if not current or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, _path = parts
        if added == "-" or deleted == "-":
            continue
        files_changed += 1
        insertions += int(added)
        deletions += int(deleted)

    flush()
    return commits


def fetch_github_commits(
    owner: str,
    repo: str,
    since: datetime,
) -> list[CommitSignal]:
    if not owner or not repo:
        return []

    commits: list[CommitSignal] = []
    page = 1
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        with httpx.Client(timeout=30.0) as client:
            while page <= 5:
                response = client.get(
                    f"{GITHUB_API}/repos/{owner}/{repo}/commits",
                    params={"since": since_iso, "per_page": 100, "page": page},
                    headers=_headers(),
                )
                response.raise_for_status()
                items = response.json()
                if not items:
                    break

                for item in items:
                    commit = item.get("commit") or {}
                    author_info = commit.get("author") or {}
                    date_str = author_info.get("date")
                    if not date_str:
                        continue
                    committed_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    if committed_at.replace(tzinfo=None) < since.replace(tzinfo=None):
                        continue
                    sha = item.get("sha") or ""
                    commits.append(
                        CommitSignal(
                            sha=sha,
                            subject=(commit.get("message") or "").split("\n")[0],
                            body=commit.get("message"),
                            author=(author_info.get("name") or "unknown"),
                            committed_at=committed_at,
                            url=item.get("html_url"),
                        )
                    )
                page += 1
    except httpx.HTTPError:
        return commits

    return commits


def fetch_github_releases(owner: str, repo: str, since: datetime) -> list[ReleaseSignal]:
    if not owner or not repo:
        return []

    releases: list[ReleaseSignal] = []
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/releases",
                params={"per_page": 20},
                headers=_headers(),
            )
            response.raise_for_status()
            items = response.json()
    except httpx.HTTPError:
        return releases

    for item in items:
        published_raw = item.get("published_at")
        if not published_raw:
            continue
        published_at = datetime.fromisoformat(published_raw.replace("Z", "+00:00"))
        if published_at.replace(tzinfo=None) < since.replace(tzinfo=None):
            continue
        releases.append(
            ReleaseSignal(
                tag=item.get("tag_name") or "",
                name=item.get("name"),
                body=item.get("body"),
                published_at=published_at,
                url=item.get("html_url"),
                prerelease=bool(item.get("prerelease")),
            )
        )
    return releases


def fetch_github_milestones(owner: str, repo: str) -> list[MilestoneSignal]:
    if not owner or not repo:
        return []

    milestones: list[MilestoneSignal] = []
    for state in ("open", "closed"):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{GITHUB_API}/repos/{owner}/{repo}/milestones",
                    params={"state": state, "per_page": 30},
                    headers=_headers(),
                )
                response.raise_for_status()
                items = response.json()
        except httpx.HTTPError:
            continue

        for item in items:
            due_on = None
            if item.get("due_on"):
                due_on = datetime.fromisoformat(item["due_on"].replace("Z", "+00:00")).date()
            closed_at = None
            if item.get("closed_at"):
                closed_at = datetime.fromisoformat(item["closed_at"].replace("Z", "+00:00"))
            milestones.append(
                MilestoneSignal(
                    title=item.get("title") or "Untitled",
                    description=item.get("description"),
                    state=item.get("state") or state,
                    open_issues=int(item.get("open_issues") or 0),
                    closed_issues=int(item.get("closed_issues") or 0),
                    due_on=due_on,
                    closed_at=closed_at,
                    url=item.get("html_url"),
                    source="github",
                )
            )
    return milestones


def collect_commits(
    owner: str,
    repo: str,
    repo_path: Path,
    since: datetime,
    *,
    prefer_local_git: bool = True,
    use_github_api: bool = True,
) -> list[CommitSignal]:
    if prefer_local_git and is_git_repo(repo_path):
        local = collect_local_commits(repo_path, since)
        if local:
            return local
    if use_github_api:
        return fetch_github_commits(owner, repo, since)
    return collect_local_commits(repo_path, since)
