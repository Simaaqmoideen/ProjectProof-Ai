"""Notifications API router.

FR-NTF-1: GET /notifications, POST /notifications/{id}/read,
           POST /notifications/read-all, GET /notifications/unread-count.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.student import NotificationResponse, PaginatedNotifications

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/unread-count")
def unread_count(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the number of unread notifications for the current user."""
    count = (
        db.execute(
            text("SELECT count(*) FROM notifications WHERE user_id = :uid AND read_at IS NULL"),
            {"uid": user.id},
        ).scalar()
        or 0
    )
    return {"unread_count": int(count)}


@router.get("", response_model=PaginatedNotifications)
def list_notifications(
    # Support both page/page_size (legacy) and limit/offset (frontend)
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    # Legacy page-based params kept for backward compat
    page: int = Query(None, ge=1),
    page_size: int = Query(None, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Own notifications, newest first."""
    # Resolve offset/limit from either param style
    if page is not None and page_size is not None:
        effective_limit = page_size
        effective_offset = (page - 1) * page_size
    else:
        effective_limit = limit
        effective_offset = offset

    rows = db.execute(
        text("""
            SELECT id, type, title, body, link, read_at, created_at
              FROM notifications
             WHERE user_id = :uid
             ORDER BY created_at DESC
             LIMIT :lim OFFSET :off
        """),
        {"uid": user.id, "lim": effective_limit, "off": effective_offset},
    ).fetchall()

    total = (
        db.execute(
            text("SELECT count(*) FROM notifications WHERE user_id = :uid"),
            {"uid": user.id},
        ).scalar()
        or 0
    )

    items = [NotificationResponse.from_row(r) for r in rows]

    has_more = (effective_offset + len(items)) < int(total)
    return PaginatedNotifications(
        items=items,
        page=page or (effective_offset // effective_limit + 1),
        page_size=effective_limit,
        total=int(total),
        has_more=has_more,
    )


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a single notification as read."""
    result = db.execute(
        text("""
            UPDATE notifications
               SET read_at = now()
             WHERE id = :nid AND user_id = :uid AND read_at IS NULL
        """),
        {"nid": notification_id, "uid": user.id},
    )
    db.commit()
    return {"marked": result.rowcount}


@router.post("/read-all")
def mark_all_read(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all unread notifications as read."""
    result = db.execute(
        text("""
            UPDATE notifications
               SET read_at = now()
             WHERE user_id = :uid AND read_at IS NULL
        """),
        {"uid": user.id},
    )
    db.commit()
    return {"marked": result.rowcount}
