"""Platform statistics service.

FR-ANA-3: Platform-wide admin statistics from v_platform_stats view.
"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_platform_stats(db: Session) -> dict[str, Any]:
    """Read the v_platform_stats view (one row) and return as a dict."""
    result = db.execute(text("SELECT * FROM v_platform_stats")).mappings().first()
    if not result:
        return {}
    keys = [
        "active_students",
        "approved_companies",
        "approved_recruiters",
        "open_projects",
        "removed_projects",
        "active_applications",
        "completed_applications",
        "certificates_issued",
        "certificates_revoked",
        "open_flags",
        "open_appeals",
        "lookups_30d",
    ]
    return {k: int(result.get(k) or 0) for k in keys}
