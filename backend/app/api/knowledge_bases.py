from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase
from app.models.document import Document
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter()

class KnowledgeBaseCreate(BaseModel):
    name: str
    description: Optional[str] = None

class KnowledgeBaseUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class KnowledgeBaseResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    kb_id: str
    created_at: str
    updated_at: str
    document_count: int

    class Config:
        from_attributes = True

@router.get("/", response_model=List[KnowledgeBaseResponse])
async def list_knowledge_bases(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all knowledge bases for the current user. Admins see all knowledge bases."""
    from app.models.user import UserRole
    
    # Admins can see all knowledge bases, regular users only see their own
    if current_user.role == UserRole.ADMIN:
        kbs = db.query(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()).all()
    else:
        kbs = db.query(KnowledgeBase).filter(KnowledgeBase.owner_id == current_user.id).order_by(KnowledgeBase.created_at.desc()).all()
    
    result = []
    for kb in kbs:
        # Count documents with this KB tag
        # For admins, count all documents. For regular users, count only their own.
        if current_user.role == UserRole.ADMIN:
            doc_count = db.query(Document).filter(
                or_(
                    Document.tags.contains(kb.kb_id),
                    Document.tags.contains(kb.name.lower())
                )
            ).count()
        else:
            doc_count = db.query(Document).filter(
                Document.owner_id == current_user.id,
                or_(
                    Document.tags.contains(kb.kb_id),
                    Document.tags.contains(kb.name.lower())
                )
            ).count()
        
        result.append({
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "kb_id": kb.kb_id,
            "created_at": kb.created_at.isoformat(),
            "updated_at": kb.updated_at.isoformat(),
            "document_count": doc_count
        })
    
    return result

@router.post("/", response_model=KnowledgeBaseResponse)
async def create_knowledge_base(
    kb_data: KnowledgeBaseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new knowledge base - Admin only"""
    # Restrict knowledge base creation to admin only
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Knowledge base management is restricted to administrators only"
        )
    # Generate URL-friendly ID
    kb_id = kb_data.name.lower().replace(" ", "-").replace("_", "-")
    # Remove special characters
    kb_id = "".join(c for c in kb_id if c.isalnum() or c == "-")
    
    # Check if KB ID already exists
    existing = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
    if existing:
        # Append number if exists
        counter = 1
        while db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == f"{kb_id}-{counter}").first():
            counter += 1
        kb_id = f"{kb_id}-{counter}"
    
    kb = KnowledgeBase(
        name=kb_data.name,
        description=kb_data.description,
        kb_id=kb_id,
        owner_id=current_user.id
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    
    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "kb_id": kb.kb_id,
        "created_at": kb.created_at.isoformat(),
        "updated_at": kb.updated_at.isoformat(),
        "document_count": 0
    }

@router.put("/{kb_id}", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_id: str,
    kb_data: KnowledgeBaseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a knowledge base - Admin only"""
    # Restrict knowledge base updates to admin only
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Knowledge base management is restricted to administrators only"
        )
    # Admins can update any knowledge base, not just their own
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
    
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found"
        )
    
    old_kb_id = kb.kb_id
    old_name = kb.name
    
    # Update fields
    if kb_data.name is not None:
        kb.name = kb_data.name
        # Update KB ID if name changed
        new_kb_id = kb_data.name.lower().replace(" ", "-").replace("_", "-")
        new_kb_id = "".join(c for c in new_kb_id if c.isalnum() or c == "-")
        
        # Check if new ID exists
        existing = db.query(KnowledgeBase).filter(
            KnowledgeBase.kb_id == new_kb_id,
            KnowledgeBase.id != kb.id
        ).first()
        if existing:
            counter = 1
            while db.query(KnowledgeBase).filter(
                KnowledgeBase.kb_id == f"{new_kb_id}-{counter}",
                KnowledgeBase.id != kb.id
            ).first():
                counter += 1
            new_kb_id = f"{new_kb_id}-{counter}"
        
        kb.kb_id = new_kb_id
    
    if kb_data.description is not None:
        kb.description = kb_data.description
    
    # Update document tags if KB ID or name changed
    # For admins, update all documents. For regular users, only their own.
    if kb_data.name is not None and (old_kb_id != kb.kb_id or old_name != kb.name):
        if current_user.role == UserRole.ADMIN:
            documents = db.query(Document).filter(
                or_(
                    Document.tags.contains(old_kb_id),
                    Document.tags.contains(old_name.lower())
                )
            ).all()
        else:
            documents = db.query(Document).filter(
                Document.owner_id == current_user.id,
                or_(
                    Document.tags.contains(old_kb_id),
                    Document.tags.contains(old_name.lower())
                )
            ).all()
        
        for doc in documents:
            tags = doc.tags.split(",") if doc.tags else []
            # Remove old tags
            tags = [t.strip() for t in tags if t.strip() not in [old_kb_id, old_name.lower()]]
            # Add new tag
            tags.append(kb.kb_id)
            doc.tags = ",".join(tags)
    
    db.commit()
    db.refresh(kb)
    
    # For admins, count all documents. For regular users, count only their own.
    if current_user.role == UserRole.ADMIN:
        doc_count = db.query(Document).filter(
            or_(
                Document.tags.contains(kb.kb_id),
                Document.tags.contains(kb.name.lower())
            )
        ).count()
    else:
        doc_count = db.query(Document).filter(
            Document.owner_id == current_user.id,
            or_(
                Document.tags.contains(kb.kb_id),
                Document.tags.contains(kb.name.lower())
            )
        ).count()
    
    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "kb_id": kb.kb_id,
        "created_at": kb.created_at.isoformat(),
        "updated_at": kb.updated_at.isoformat(),
        "document_count": doc_count
    }

@router.delete("/{kb_id}")
async def delete_knowledge_base(
    kb_id: str,
    target_kb_id: Optional[str] = None,  # KB to move documents to
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a knowledge base - Admin only"""
    # Restrict knowledge base deletion to admin only
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Knowledge base management is restricted to administrators only"
        )
    # Admins can delete any knowledge base, not just their own
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
    
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found"
        )
    
    # Check if it's the last KB (check all KBs, not just user's)
    kb_count = db.query(KnowledgeBase).count()
    if kb_count <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the last knowledge base"
        )
    
    # Get documents with this KB tag (all documents for admins)
    documents = db.query(Document).filter(
        or_(
            Document.tags.contains(kb.kb_id),
            Document.tags.contains(kb.name.lower())
        )
    ).all()
    
    # Move documents to target KB if specified, otherwise first available KB
    if target_kb_id:
        target_kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == target_kb_id).first()
    else:
        target_kb = db.query(KnowledgeBase).filter(KnowledgeBase.id != kb.id).first()
    
    if target_kb and documents:
        for doc in documents:
            tags = doc.tags.split(",") if doc.tags else []
            # Remove old KB tags
            tags = [t.strip() for t in tags if t.strip() not in [kb.kb_id, kb.name.lower()]]
            # Add target KB tag
            if target_kb.kb_id not in tags:
                tags.append(target_kb.kb_id)
            doc.tags = ",".join(tags)
    
    # Delete the KB
    db.delete(kb)
    db.commit()
    
    return {"message": "Knowledge base deleted successfully"}

