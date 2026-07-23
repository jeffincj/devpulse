"""
Thin wrapper around the GitHub REST API (v3).

Only read-only endpoints are used: pulls, pull request detail, pull request
reviews and commits. A personal access token raises the unauthenticated rate
limit from 60/hr to 5,000/hr and is required for private repos.
"""
import requests
from datetime import datetime
from django.conf import settings


class GitHubAPIError(Exception):
    pass


class GitHubClient:
    def __init__(self, token: str | None = None):
        self.token = token or settings.GITHUB_TOKEN
        self.base_url = settings.GITHUB_API_BASE_URL
        self.session = requests.Session()
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "DevPulse-Analytics-App",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        self.session.headers.update(headers)

    def _get(self, path, params=None):
        response = self.session.get(f"{self.base_url}{path}", params=params, timeout=15)
        if response.status_code == 404:
            raise GitHubAPIError(f"Not found: {path}")
        if response.status_code == 403:
            raise GitHubAPIError("GitHub API rate limit exceeded or access forbidden.")
        if not response.ok:
            raise GitHubAPIError(f"GitHub API error {response.status_code}: {response.text}")
        return response.json()

    def _get_paginated(self, path, params=None, max_pages=5):
        params = dict(params or {})
        params.setdefault("per_page", 100)
        results = []
        page = 1
        while page <= max_pages:
            params["page"] = page
            batch = self._get(path, params=params)
            if not batch:
                break
            results.extend(batch)
            if len(batch) < params["per_page"]:
                break
            page += 1
        return results
    def get_repository(self, full_name: str):
        """Repo-level metadata: owner, description, stars, created date."""
        return self._get(f"/repos/{full_name}")

    def list_pull_requests(self, full_name: str, state: str = "all"):
        """List PRs (open/closed/merged) for owner/repo. Basic fields only."""
        return self._get_paginated(f"/repos/{full_name}/pulls", params={"state": state})

    def get_pull_request(self, full_name: str, number: int):
        """Detail endpoint - includes additions/deletions/changed_files/merged_at."""
        return self._get(f"/repos/{full_name}/pulls/{number}")

    def list_pull_request_reviews(self, full_name: str, number: int):
        return self._get(f"/repos/{full_name}/pulls/{number}/reviews")

    def list_commits(self, full_name: str, since: datetime | None = None):
        params = {}
        if since:
            params["since"] = since.isoformat()
        return self._get_paginated(f"/repos/{full_name}/commits", params=params)

def get_repository(self, full_name: str):
        """Repo-level metadata: owner, description, stars, created date."""
        return self._get(f"/repos/{full_name}")

def _parse_dt(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def sync_repository(repository, max_prs: int = 20):
    """
    Pulls live PR + commit data from GitHub for a Repository and upserts it
    into our DB. Returns a small summary dict.

    This is intentionally synchronous/simple (management command or on-demand
    API call). For heavier repos, swap this for a Celery task without
    changing the calling code.
    """
    from .models import PullRequest, Commit  # local import avoids circulars

    client = GitHubClient()
    created_prs, updated_prs, created_commits = 0, 0, 0

    prs = client.list_pull_requests(repository.full_name, state="all")[:max_prs]
    for pr in prs:
        detail = client.get_pull_request(repository.full_name, pr["number"])

        state = "merged" if detail.get("merged_at") else detail["state"]

        first_review_at = None
        try:
            reviews = client.list_pull_request_reviews(repository.full_name, pr["number"])
            if reviews:
                first_review_at = min(_parse_dt(r["submitted_at"]) for r in reviews if r.get("submitted_at"))
        except GitHubAPIError:
            pass  # reviews endpoint failing shouldn't fail the whole sync

        obj, created = PullRequest.objects.update_or_create(
            repository=repository,
            number=detail["number"],
            defaults={
                "title": detail["title"],
                "author_username": detail["user"]["login"] if detail.get("user") else "",
                "state": state,
                "additions": detail.get("additions", 0),
                "deletions": detail.get("deletions", 0),
                "changed_files": detail.get("changed_files", 0),
                "created_at": _parse_dt(detail["created_at"]),
                "updated_at": _parse_dt(detail["updated_at"]),
                "merged_at": _parse_dt(detail.get("merged_at")),
                "first_review_at": first_review_at,
            },
        )
        created_prs += int(created)
        updated_prs += int(not created)

    commits = client.list_commits(repository.full_name)
    for c in commits:
        commit_info = c.get("commit", {})
        author_login = (c.get("author") or {}).get("login", "") or commit_info.get("author", {}).get("name", "")
        _, created = Commit.objects.update_or_create(
            repository=repository,
            sha=c["sha"],
            defaults={
                "author_username": author_login,
                "message": commit_info.get("message", "")[:2000],
                "authored_at": _parse_dt(commit_info.get("author", {}).get("date")),
            },
        )
        created_commits += int(created)

    repository.last_synced_at = datetime.utcnow()
    repository.save(update_fields=["last_synced_at"])

    return {
        "repository": repository.full_name,
        "prs_created": created_prs,
        "prs_updated": updated_prs,
        "commits_created": created_commits,
        "total_prs_fetched": len(prs),
        "total_commits_fetched": len(commits),
    }
