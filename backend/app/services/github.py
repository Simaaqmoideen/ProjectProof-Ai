"""GitHub integration service.

AGENTS.md rule 12: Only this file calls GitHub.
- Uses server-built URL from validated username only.
- GitHub data is labelled "self-linked, not verified".
- GitHub data never affects XP, badges, match experience or the verification page.

FR-STU-8: Link a GitHub username; read public profile and repositories.
"""

import re
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import AppError, BadRequestError

# Allowed GitHub username pattern: 1-39 alphanumeric or hyphens, no leading/trailing hyphens, no slashes
_GITHUB_USERNAME_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,37}[a-zA-Z0-9])?$")

_GITHUB_API_BASE = "https://api.github.com"
_TIMEOUT = 8.0  # seconds
_LABEL = "self-linked, not verified"


def validate_github_username(username: str) -> str:
    """FR-STU-8 / T-STU-04: Reject usernames with slashes, spaces, or >39 chars.
    No request leaves the server for invalid inputs.
    """
    username = username.strip()
    if not username or len(username) > 39:
        raise BadRequestError("GitHub username must be 1-39 characters.")
    if "/" in username or " " in username:
        raise BadRequestError("GitHub username may not contain slashes or spaces.")
    if not _GITHUB_USERNAME_RE.match(username):
        raise BadRequestError(
            "GitHub username may only contain alphanumeric characters and hyphens, "
            "and may not start or end with a hyphen."
        )
    return username


def _build_github_url(path: str) -> str:
    """Always build the URL server-side from path — never from user input."""
    return f"{_GITHUB_API_BASE}{path}"


def fetch_github_summary(username: str, github_token: str | None = None) -> dict[str, Any]:
    """Fetch public profile and repositories from GitHub.

    Returns a summary dict labelled 'self-linked, not verified'.
    Raises AppError with code 'github_unavailable' on timeout or HTTP error.

    AGENTS.md rule 12: URL is built server-side from validated username only.
    """
    username = validate_github_username(username)
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    user_url = _build_github_url(f"/users/{username}")
    repos_url = _build_github_url(f"/users/{username}/repos")

    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            user_resp = client.get(user_url, headers=headers)
            repos_resp = client.get(
                repos_url, headers=headers, params={"sort": "updated", "per_page": 30}
            )
    except httpx.TimeoutException as exc:
        raise AppError(
            code="github_unavailable", message="GitHub API timed out.", status_code=503
        ) from exc
    except httpx.HTTPError as exc:
        raise AppError(
            code="github_unavailable", message="GitHub API is unreachable.", status_code=503
        ) from exc

    if user_resp.status_code == 404:
        raise BadRequestError(f"GitHub username '{username}' not found.")
    if user_resp.status_code == 429:
        raise AppError(
            code="github_unavailable", message="GitHub rate limit hit. Try later.", status_code=503
        )
    if user_resp.status_code != 200:
        raise AppError(
            code="github_unavailable",
            message=f"GitHub API returned {user_resp.status_code}.",
            status_code=503,
        )

    user_data = user_resp.json()

    # Aggregate languages from repos
    languages: dict[str, int] = {}
    if repos_resp.status_code == 200:
        repos = repos_resp.json()
        for repo in repos:
            lang = repo.get("language")
            if lang:
                languages[lang] = languages.get(lang, 0) + 1

    top_languages = sorted(languages, key=lambda k: -languages[k])[:5]

    summary = {
        "label": _LABEL,
        "username": username,
        "public_repos": user_data.get("public_repos", 0),
        "followers": user_data.get("followers", 0),
        "following": user_data.get("following", 0),
        "bio": user_data.get("bio"),
        "company": user_data.get("company"),
        "blog": user_data.get("blog"),
        "location": user_data.get("location"),
        "top_languages": top_languages,
        "fetched_at": datetime.now(UTC).isoformat(),
    }
    return summary


def fetch_github_repos(username: str, github_token: str | None = None) -> list[dict[str, Any]]:
    """Fetch repos list for github analysis.

    AGENTS.md Rule 12: Only services/github.py calls GitHub with server-built URLs.
    """
    username = validate_github_username(username)
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
    repos_url = _build_github_url(f"/users/{username}/repos")
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            repos_resp = client.get(
                repos_url, headers=headers, params={"sort": "updated", "per_page": 30}
            )
    except httpx.TimeoutException as exc:
        raise AppError(
            code="github_unavailable", message="GitHub API timed out.", status_code=503
        ) from exc
    except httpx.HTTPError as exc:
        raise AppError(
            code="github_unavailable", message="GitHub API is unreachable.", status_code=503
        ) from exc
    if repos_resp.status_code == 404:
        raise BadRequestError(f"GitHub username '{username}' not found.")
    if repos_resp.status_code != 200:
        raise AppError(
            code="github_unavailable",
            message=f"GitHub API returned {repos_resp.status_code}.",
            status_code=503,
        )
    return repos_resp.json()


def link_github(
    db: Session, student_user_id: uuid.UUID, username: str, github_token: str | None = None
) -> dict[str, Any]:
    """FR-STU-8: Validate username, fetch summary, store username + summary.
    Summary stored in student_profiles; never affects XP/badges/verification.
    """
    username = validate_github_username(username)
    summary = fetch_github_summary(username, github_token=github_token)

    db.execute(
        text("""
            UPDATE student_profiles
               SET github_username = :username,
                   github_summary  = CAST(:summary AS jsonb),
                   github_analyzed_at = now(),
                   updated_at = now()
             WHERE user_id = :user_id
        """),
        {
            "username": username,
            "summary": __import__("json").dumps(summary),
            "user_id": student_user_id,
        },
    )
    return summary


def get_github_summary(db: Session, student_user_id: uuid.UUID) -> dict[str, Any] | None:
    """Return stored GitHub summary for a student, or None if not linked."""
    row = db.execute(
        text(
            "SELECT github_username, github_summary, github_analyzed_at FROM student_profiles WHERE user_id = :uid"
        ),
        {"uid": student_user_id},
    ).fetchone()
    if not row or not row[0]:
        return None
    return {
        "username": row[0],
        "summary": row[1] or {},
        "analyzed_at": row[2].isoformat() if row[2] else None,
        "label": _LABEL,
    }


def unlink_github(db: Session, student_user_id: uuid.UUID) -> None:
    """DELETE /students/me/github: remove stored username and summary."""
    db.execute(
        text("""
            UPDATE student_profiles
               SET github_username = NULL,
                   github_summary  = NULL,
                   github_analyzed_at = NULL,
                   updated_at = now()
             WHERE user_id = :uid
        """),
        {"uid": student_user_id},
    )
