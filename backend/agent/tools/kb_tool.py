"""Knowledge base browsing tool — lists available documents."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.database import Document

logger = logging.getLogger(__name__)


def list_documents(
    user_role: str,
    db: Session,
    category: Optional[str] = None,
) -> dict:
    """List available documents, filtered by role access level."""
    access_levels = ["all"]
    if user_role in ("staff", "admin"):
        access_levels.append("staff")
    if user_role == "admin":
        access_levels.append("admin")

    query = db.query(Document).filter(Document.access_level.in_(access_levels))
    if category:
        query = query.filter(Document.category == category)

    docs = query.all()

    return {
        "count": len(docs),
        "documents": [
            {
                "id": d.id,
                "title": d.title,
                "category": d.category,
                "access_level": d.access_level,
                "created_at": str(d.created_at) if d.created_at else None,
            }
            for d in docs
        ],
        "categories": list({d.category for d in docs}),
    }


def get_document_content(
    doc_id: int,
    user_role: str,
    db: Session,
) -> dict:
    """Get a specific document's content."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        return {"found": False, "message": "Document not found."}

    # Check access level
    access_map = {"all": 0, "staff": 1, "admin": 2}
    role_map = {"user": 0, "staff": 1, "admin": 2}
    if role_map.get(user_role, 0) < access_map.get(doc.access_level, 0):
        return {
            "found": False,
            "message": "You don't have permission to view this document.",
            "access_denied": True,
        }

    return {
        "found": True,
        "document": {
            "id": doc.id,
            "title": doc.title,
            "content": doc.content,
            "category": doc.category,
            "access_level": doc.access_level,
        },
    }
