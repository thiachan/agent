from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.document import Document
from typing import Optional

router = APIRouter()

@router.get("/{document_id}")
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Check permissions
    has_access = (
        document.is_public or
        document.owner_id == current_user.id or
        (document.allowed_roles and current_user.role.value in document.allowed_roles.split(","))
    )
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this document"
        )
    
    return {
        "id": document.id,
        "filename": document.filename,
        "title": document.title,
        "description": document.description,
        "file_type": document.file_type.value,
        "status": document.status.value,
        "file_size": document.file_size,
        "tags": document.tags.split(",") if document.tags else [],
        "created_at": document.created_at.isoformat(),
        "owner": {
            "id": document.owner.id,
            "full_name": document.owner.full_name
        }
    }

