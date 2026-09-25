"""Admin management tool — admin-only operations."""

import logging

from sqlalchemy.orm import Session

from backend.database import AuditLog, User

logger = logging.getLogger(__name__)


def list_all_users(db: Session) -> dict:
    """List all users in the system."""
    users = db.query(User).all()
    return {
        "count": len(users),
        "users": [
            {
                "id": u.id,
                "username": u.username,
                "full_name": u.full_name,
                "email": u.email,
                "role": u.role,
                "department": u.department,
                "phone": u.phone,
                "is_active": u.is_active,
                "created_at": u.created_at,
                "assigned_staff_id": u.assigned_staff_id,
            }
            for u in users
        ],
    }


def assign_staff_to_user(user_id: int, staff_id: int, db: Session) -> dict:
    """Assign a staff member to a user."""
    user = db.query(User).filter(User.id == user_id).first()
    staff = db.query(User).filter(User.id == staff_id, User.role == "staff").first()

    if not user:
        return {"success": False, "message": f"User with ID {user_id} not found."}
    if not staff:
        return {"success": False, "message": f"Staff with ID {staff_id} not found."}

    user.assigned_staff_id = staff_id
    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": f"Staff '{staff.full_name}' assigned to user '{user.full_name}'.",
    }


def update_user(user_id: int, updates: dict, db: Session) -> dict:
    """Update a user's profile fields."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"success": False, "message": f"User with ID {user_id} not found."}

    allowed_fields = {"full_name", "email", "department", "phone", "role", "is_active"}
    applied = {}
    for key, value in updates.items():
        if key in allowed_fields and value is not None:
            setattr(user, key, value)
            applied[key] = value

    if applied:
        db.commit()
        db.refresh(user)

    return {
        "success": True,
        "message": f"Updated user '{user.username}'.",
        "changes": applied,
    }


def get_audit_logs(db: Session, limit: int = 50) -> dict:
    """Retrieve recent audit log entries."""
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "count": len(logs),
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "action": log.action,
                "resource": log.resource,
                "decision": log.decision,
                "jev_probability": log.jev_probability,
                "reason": log.reason,
                "created_at": str(log.created_at) if log.created_at else None,
            }
            for log in logs
        ],
    }


def get_system_stats(db: Session) -> dict:
    """Get system-wide statistics."""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    admins = db.query(User).filter(User.role == "admin").count()
    staff = db.query(User).filter(User.role == "staff").count()
    regular_users = db.query(User).filter(User.role == "user").count()
    total_audits = db.query(AuditLog).count()
    denied_audits = db.query(AuditLog).filter(AuditLog.decision == "denied").count()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "admins": admins,
        "staff": staff,
        "regular_users": regular_users,
        "total_audit_entries": total_audits,
        "denied_access_attempts": denied_audits,
    }
