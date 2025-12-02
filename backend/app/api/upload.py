from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.document import Document, DocumentType, DocumentStatus
from app.services.document_processor import document_processor
from app.services.rag_service import rag_service
from app.core.config import settings
import os
import aiofiles
from pathlib import Path
from typing import Optional

router = APIRouter()

def get_file_type(filename: str) -> Optional[DocumentType]:
    """Get document type from filename extension"""
    ext = Path(filename).suffix.lower().lstrip(".")
    try:
        return DocumentType(ext)
    except ValueError:
        return None

def process_document_background(document_id: int, file_path: str, file_type: str):
    """Background task to process document and add to RAG (synchronous function)"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Create a new database session for the background task
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        logger.info(f"Starting to process document {document_id}: {file_path}")
        
        # Update status to processing
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.warning(f"Document {document_id} not found in database")
            return
        
        document.status = DocumentStatus.PROCESSING
        db.commit()
        logger.info(f"Document {document_id} status set to PROCESSING")
        
        # Extract text
        logger.info(f"Extracting text from {file_type} file...")
        text = document_processor.extract_text(file_path, file_type)
        logger.info(f"Extracted {len(text)} characters from document")
        
        if not text or len(text.strip()) == 0:
            logger.warning(f"No text extracted from document {document_id}")
            text = " "  # Empty text, use space to avoid errors
        
        # Extract tags from document if available
        tags = document.tags or ""
        # Also try to extract tags from document content (if TAGS: line exists)
        if "TAGS:" in text:
            import re
            tag_match = re.search(r'TAGS:\s*(.+)', text, re.IGNORECASE)
            if tag_match:
                content_tags = tag_match.group(1).strip()
                # Combine with existing tags
                if tags:
                    tags = f"{tags}, {content_tags}"
                else:
                    tags = content_tags
        
        # Extract title from document if available
        title = document.title
        if not title:
            # Try to extract from first line or filename
            lines = text.split('\n')
            for line in lines[:5]:
                if line.strip() and len(line.strip()) < 200:
                    # Check if it looks like a title (not a section header)
                    if not line.isupper() or len(line.split()) <= 5:
                        title = line.strip()
                        break
            if not title:
                # Use filename as fallback
                title = document.filename.rsplit('.', 1)[0].replace('_', ' ')
        
        # Add to vector store
        logger.info(f"Adding document to vector store...")
        metadata = {
            "document_id": document_id,
            "filename": document.filename,
            "title": title,  # Include title in metadata
            "tags": tags,  # Include tags in metadata
            "file_type": file_type,
            "is_public": document.is_public,
            "allowed_roles": document.allowed_roles or "",
            "owner_id": document.owner_id,
        }
        chunk_ids = rag_service.add_document(text, metadata)
        logger.info(f"Added {len(chunk_ids)} chunks to vector store")
        
        # Update document status
        document.status = DocumentStatus.PROCESSED
        document.processed_chunks = len(chunk_ids)
        db.commit()
        logger.info(f"Document {document_id} processing completed successfully")
        
    except Exception as e:
        # Update status to failed
        logger.error(f"Error processing document {document_id}: {e}", exc_info=True)
        
        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = DocumentStatus.FAILED
                document.error_message = str(e)[:500]  # Limit error message length
                db.commit()
                logger.info(f"Document {document_id} status set to FAILED")
        except Exception as db_error:
            logger.error(f"Error updating document status: {db_error}")
    finally:
        db.close()
        logger.info(f"Closed database session for document {document_id}")

@router.post("/")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    is_public: bool = Form(False),
    allowed_roles: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Restrict uploads to admin only
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document upload is restricted to administrators only"
        )
    # Validate file type
    file_type = get_file_type(file.filename)
    if not file_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size
    file_content = await file.read()
    file_size = len(file_content)
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    
    # Create upload directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Save file
    file_path = os.path.join(settings.UPLOAD_DIR, f"{current_user.id}_{file.filename}")
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(file_content)
    
    # Create document record
    document = Document(
        filename=file.filename,
        original_filename=file.filename,
        file_type=file_type,
        file_path=file_path,
        file_size=file_size,
        status=DocumentStatus.UPLOADING,
        title=title or file.filename,
        description=description,
        tags=tags,
        owner_id=current_user.id,
        is_public=is_public,
        allowed_roles=allowed_roles
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Process document in background (don't pass db session - it will be closed)
    # Note: FastAPI background tasks run in a thread pool, so we use a regular function, not async
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Scheduling background task for document {document.id}: {file.filename}")
    
    background_tasks.add_task(
        process_document_background,
        document.id,
        file_path,
        file_type.value
    )
    
    return {
        "id": document.id,
        "filename": document.filename,
        "file_type": document.file_type.value,
        "status": document.status.value,
        "created_at": document.created_at.isoformat()
    }

@router.get("/")
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,  # Increased limit to show more documents
    file_type: Optional[str] = None  # Filter by file type (e.g., "pptx" for templates)
):
    """List documents accessible to current user. Admins see all documents."""
    import logging
    from app.models.user import UserRole
    logger = logging.getLogger(__name__)
    
    # Admins can see all documents, regular users see their own and public ones
    if current_user.role == UserRole.ADMIN:
        query = db.query(Document)
    else:
        # Filter by permissions - show user's own documents and public ones
        query = db.query(Document).filter(
            (Document.is_public == True) | 
            (Document.owner_id == current_user.id)
        )
        
        # Also include documents where user's role is in allowed_roles
        # Note: This uses a simple contains check - may need refinement for comma-separated values
        if current_user.role:
            role_filter = Document.allowed_roles.contains(current_user.role.value)
            query = query.filter(
                (Document.is_public == True) | 
                (Document.owner_id == current_user.id) |
                role_filter
            )
    
    # Filter by file type if provided
    if file_type:
        try:
            doc_type = DocumentType(file_type.lower())
            query = query.filter(Document.file_type == doc_type)
        except ValueError:
            pass  # Invalid file type, ignore filter
    
    total = query.count()
    documents = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
    
    logger.info(f"User {current_user.id} ({current_user.role.value}): Found {total} total documents, returning {len(documents)}")
    
    return {
        "total": total,
        "items": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "title": doc.title,
                "file_type": doc.file_type.value,
                "status": doc.status.value,
                "file_size": doc.file_size,
                "tags": doc.tags,
                "created_at": doc.created_at.isoformat(),
                "owner": {
                    "id": doc.owner.id,
                    "full_name": doc.owner.full_name
                }
            }
            for doc in documents
        ]
    }

@router.get("/templates")
async def list_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List PowerPoint templates (PPTX files) accessible to current user"""
    # Filter by permissions and file type
    query = db.query(Document).filter(
        Document.file_type.in_([DocumentType.PPT, DocumentType.PPTX]),
        (
            (Document.is_public == True) | 
            (Document.owner_id == current_user.id) |
            (Document.allowed_roles.contains(current_user.role.value))
        )
    )
    
    documents = query.order_by(Document.created_at.desc()).all()
    
    return {
        "templates": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "title": doc.title or doc.filename,
                "file_type": doc.file_type.value,
                "file_size": doc.file_size,
                "created_at": doc.created_at.isoformat(),
                "owner": {
                    "id": doc.owner.id,
                    "full_name": doc.owner.full_name
                }
            }
            for doc in documents
        ]
    }

@router.delete("/{document_id}")
async def delete_document(
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
    
    # Restrict document deletion to admin only
    from app.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Document deletion is restricted to administrators only"
        )
    
    # Delete from vector store
    rag_service.delete_document(document_id)
    
    # Delete file
    if os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    # Delete from database
    db.delete(document)
    db.commit()
    
    return {"message": "Document deleted successfully"}

