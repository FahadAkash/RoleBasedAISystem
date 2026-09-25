"""Staff info tool — looks up staff members and their assigned users."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.database import User

logger = logging.getLogger(__name__)


def get_staff_info(
    requester_id: int,
    requester_role: str,
    db: Session,
    target_staff_id: Optional[int] = None,
    target_staff_username: Optional[str] = None,
) -> dict:
    """
    Look up staff member info.

    Access rules:
      • Staff can only see their own info.
      • Admins can see any staff member.
      • Users cannot use this tool at all (blocked by hard RBAC).
    """
    if target_staff_username:
        staff = (
            db.query(User)
            .filter(User.username == target_staff_username, User.role == "staff")
            .first()
        )
    elif target_staff_id:
        staff = (
            db.query(User)
            .filter(User.id == target_staff_id, User.role == "staff")
            .first()
        )
    else:
        # Default: own info (if staff)
        staff = db.query(User).filter(User.id == requester_id).first()

    if not staff:
        return {"found": False, "message": "Staff member not found."}

    # Staff can only see themselves
    if requester_role == "staff" and staff.id != requester_id:
        return {
            "found": False,
            "message": "You can only view your own staff information.",
            "access_denied": True,
        }

    # Get assigned users
    assigned = db.query(User).filter(User.assigned_staff_id == staff.id).all()

    return {
        "found": True,
        "staff": {
            "id": staff.id,
            "username": staff.username,
            "full_name": staff.full_name,
            "email": staff.email,
            "department": staff.department,
            "phone": staff.phone,
        },
        "assigned_users": [
            {
                "id": u.id,
                "username": u.username,
                "full_name": u.full_name,
                "department": u.department,
            }
            for u in assigned
        ],
        "assigned_count": len(assigned),
    }


def list_all_staff(db: Session) -> dict:
    """Admin-only: list all staff members."""
    staff_members = db.query(User).filter(User.role == "staff").all()
    result = []
    for s in staff_members:
        assigned_count = (
            db.query(User).filter(User.assigned_staff_id == s.id).count()
        )
        result.append(
            {
                "id": s.id,
                "username": s.username,
                "full_name": s.full_name,
                "department": s.department,
                "assigned_user_count": assigned_count,
            }
        )
    return {"count": len(result), "staff": result}
