"""Admin router — admin-only management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.agent.tools.admin_tool import (
    assign_staff_to_user,
    get_audit_logs,
    get_system_stats,
    list_all_users,
    update_user,
)
from backend.agent.tools.kb_tool import list_documents
from backend.auth import require_role
from backend.database import Document, User, get_db
from backend.models import AssignStaff, DocumentUpload, UserProfile, UserUpdate
from backend.rag.document_loader import load_and_index_text

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserProfile])
def get_all_users(
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """List all users in the system."""
    result = list_all_users(db)
    return result["users"]


@router.post("/assign-staff")
def assign_staff(
    data: AssignStaff,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Assign a staff member to a user."""
    return assign_staff_to_user(data.user_id, data.staff_id, db)


@router.put("/users/{user_id}")
def update_user_profile(
    user_id: int,
    data: UserUpdate,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Update a user's profile."""
    return update_user(user_id, data.model_dump(exclude_unset=True), db)


@router.get("/audit-logs")
def get_logs(
    limit: int = 50,
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Get audit logs."""
    return get_audit_logs(db, limit=limit)


@router.get("/stats")
def get_stats(
    _admin: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """Get system statistics."""
    return get_system_stats(db)


@router.post("/documents")
def upload_document(
    data: DocumentUpload,
    admin: User = Depends(require_role("admin", "staff")),
    db: Session = Depends(get_db),
):
    """Upload a document to the knowledge base and index it for RAG."""
    # Save to database
    doc = Document(
        title=data.title,
        filename=f"{data.title.replace(' ', '_').lower()}.txt",
        content=data.content,
        category=data.category,
        access_level=data.access_level,
        uploaded_by=admin.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Index for RAG
    chunk_count = load_and_index_text(
        title=data.title,
        content=data.content,
        access_level=data.access_level,
        category=data.category,
        source_filename=doc.filename,
    )

    return {
        "success": True,
        "document_id": doc.id,
        "chunks_indexed": chunk_count,
        "message": f"Document '{data.title}' uploaded and indexed ({chunk_count} chunks).",
    }


@router.get("/documents")
def get_documents(
    admin: User = Depends(require_role("admin", "staff")),
    db: Session = Depends(get_db),
):
    """List all documents."""
    return list_documents(user_role=admin.role, db=db)
