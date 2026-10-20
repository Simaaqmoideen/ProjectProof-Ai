"""Notifications service (in-app notifications).
See docs/01 and docs/05.
"""
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session


def create_notification(
    db: Session,
    user_id: uuid.UUID,
    type: str,
    title: str,
    body: str | None = None,
    link: str | None = None,
) -> uuid.UUID:
    """Insert an in-app notification row for a user."""
    notif_id = uuid.uuid4()
    db.execute(
        text("""
            INSERT INTO notifications (id, user_id, type, title, body, link, created_at)
            VALUES (:id, :user_id, :type, :title, :body, :link, now())
        """),
        {
            "id": notif_id,
            "user_id": user_id,
            "type": type,
            "title": title,
            "body": body,
            "link": link,
        },
    )
    return notif_id
