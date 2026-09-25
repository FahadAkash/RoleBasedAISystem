"""User info tool — looks up user profiles from SQLite."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.database import User

logger = logging.getLogger(__name__)


def get_user_info(
    requester_id: int,
    requester_role: str,
    db: Session,
    target_username: Optional[str] = None,
    target_user_id: Optional[int] = None,
) -> dict:
    """
    Look up a user's profile.

    Access rules (enforced in code, Jev validates the *intent*):
      • Users can only see themselves.
      • Staff can see themselves + their assigned users.
      • Admins can see anyone.
    """
    # Determine target
    if target_username:
        target = db.query(User).filter(User.username == target_username).first()
    elif target_user_id:
        target = db.query(User).filter(User.id == target_user_id).first()
    else:
        # Default: own info
        target = db.query(User).filter(User.id == requester_id).first()

    if not target:
        return {"found": False, "message": "User not found."}

    # Hard access check
    if requester_role == "user" and target.id != requester_id:
        return {
            "found": False,
            "message": "You can only view your own information.",
            "access_denied": True,
        }

    if requester_role == "staff":
        is_own = target.id == requester_id
        is_assigned = target.assigned_staff_id == requester_id
        if not (is_own or is_assigned):
            return {
                "found": False,
                "message": "You can only view your own information or your assigned users.",
                "access_denied": True,
            }

    # Build response (admins always pass through)
    return {
        "found": True,
        "user": {
            "id": target.id,
            "username": target.username,
            "full_name": target.full_name,
            "email": target.email,
            "role": target.role,
            "department": target.department,
            "phone": target.phone,
            "is_active": target.is_active,
            "assigned_staff_id": target.assigned_staff_id,
        },
    }


def list_users_for_staff(staff_id: int, db: Session) -> dict:
    """Return all users assigned to a specific staff member."""
    users = db.query(User).filter(User.assigned_staff_id == staff_id).all()
    return {
        "count": len(users),
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "full_name": u.full_name,
                "email": u.email,
                "department": u.department,
            }
            for u in users
        ],
    }
