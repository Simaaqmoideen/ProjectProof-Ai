"""Regression coverage for certificate hashing, privacy and rate-limit windows."""

import hashlib
import json
from datetime import UTC, datetime

import pytest

from app.core import rate_limit
from app.core.errors import RateLimitedError
from app.core.ids import compute_certificate_hash
from app.services.certificate import verification_display_name


@pytest.fixture
def limiter():
    rate_limit.reset_rate_limits()
    yield rate_limit
    rate_limit.reset_rate_limits()


def test_cleanup_preserves_long_window(limiter, monkeypatch):
    monkeypatch.setattr(limiter.time, "time", lambda: 1_000.0)
    limiter.check_rate_limit("long", max_requests=1, window_seconds=3600)
    for i in range(101):
        limiter.check_rate_limit(f"short-{i}", window_seconds=1)
    monkeypatch.setattr(limiter.time, "time", lambda: 1_120.0)
    limiter.check_rate_limit("short-new", window_seconds=1)
    with pytest.raises(RateLimitedError):
        limiter.check_rate_limit("long", max_requests=1, window_seconds=3600)
    assert "short-0" not in limiter._request_timestamps


def test_cleanup_runs_at_most_once_a_minute(limiter, monkeypatch):
    monkeypatch.setattr(limiter.time, "time", lambda: 1_000.0)
    limiter.check_rate_limit("expired", window_seconds=1)
    monkeypatch.setattr(limiter.time, "time", lambda: 1_059.0)
    limiter.check_rate_limit("other", window_seconds=1)
    assert "expired" in limiter._request_timestamps
    monkeypatch.setattr(limiter.time, "time", lambda: 1_060.0)
    limiter.check_rate_limit("other", window_seconds=1)
    assert "expired" not in limiter._request_timestamps


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-01-02T03:04:05Z",
        "2026-01-02T05:04:05+02:00",
        "2026-01-02T03:04:05",
        datetime(2026, 1, 2, 3, 4, 5),
        datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
    ],
)
def test_certificate_hash_normalizes_timestamp(timestamp):
    args = {
        "student_id": "student",
        "project_id": "project",
        "company_id": "company",
        "skills": ["Python"],
        "overall_score": 85,
    }
    assert compute_certificate_hash(completed_at=timestamp, **args) == compute_certificate_hash(
        completed_at=datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC), **args
    )


def test_certificate_hash_preserves_unparseable_timestamp():
    canonical = {
        "student_id": "student",
        "project_id": "project",
        "company_id": "company",
        "completed_at": "unknown",
        "skills": ["Python"],
        "overall_score": 85,
    }
    expected = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert compute_certificate_hash(**canonical) == expected


@pytest.mark.parametrize(
    ("name", "show_full", "first_only", "expected"),
    [
        ("Ananya Rao", True, False, "Ananya Rao"),
        ("Ananya Rao", False, False, "A. R."),
        ("Ananya", False, False, "A."),
        ("", False, False, "Student"),
        ("Ananya Rao", False, True, "A."),
        ("", False, True, "."),
    ],
)
def test_verification_display_name(name, show_full, first_only, expected):
    assert verification_display_name(name, show_full, first_initial_only=first_only) == expected
