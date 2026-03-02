from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import asc, desc
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.bookmark import Bookmark, BookmarkCategory
from datetime import datetime

router = APIRouter()


# ─── Pydantic Schemas ────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None


class CategoryOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class BookmarkCreate(BaseModel):
    name: str
    description: Optional[str] = None
    url: str
    category_id: Optional[int] = None


class BookmarkUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    category_id: Optional[int] = None


class BookmarkOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    url: str
    category_id: Optional[int]
    category: Optional[CategoryOut]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Helper ──────────────────────────────────────────────────────────────────

def require_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


# ─── Category Endpoints ───────────────────────────────────────────────────────

@router.get("/categories", response_model=List[CategoryOut])
async def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all bookmark categories."""
    return db.query(BookmarkCategory).order_by(asc(BookmarkCategory.name)).all()


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new bookmark category (admin only)."""
    existing = db.query(BookmarkCategory).filter(BookmarkCategory.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category '{data.name}' already exists"
        )
    category = BookmarkCategory(name=data.name, description=data.description)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    data: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Rename / update a category (admin only)."""
    category = db.query(BookmarkCategory).filter(BookmarkCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    clash = db.query(BookmarkCategory).filter(
        BookmarkCategory.name == data.name, BookmarkCategory.id != category_id
    ).first()
    if clash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Category '{data.name}' already exists")
    category.name = data.name
    category.description = data.description
    db.commit()
    db.refresh(category)
    return category


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete a category (admin only). Bookmarks inside will have category set to null."""
    category = db.query(BookmarkCategory).filter(BookmarkCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    db.delete(category)
    db.commit()


# ─── Bookmark Endpoints ───────────────────────────────────────────────────────

@router.get("", response_model=List[BookmarkOut])
async def list_bookmarks(
    sort: str = Query("date_desc", description="Sort order: name_asc, name_desc, category, date_asc, date_desc"),
    category_id: Optional[int] = Query(None, description="Filter by category id"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all bookmarks with optional sort and category filter."""
    query = db.query(Bookmark).options(joinedload(Bookmark.category))

    if category_id is not None:
        query = query.filter(Bookmark.category_id == category_id)

    sort_map = {
        "name_asc": asc(Bookmark.name),
        "name_desc": desc(Bookmark.name),
        "date_asc": asc(Bookmark.created_at),
        "date_desc": desc(Bookmark.created_at),
    }

    if sort == "category":
        # Join category name for sorting
        query = query.outerjoin(BookmarkCategory, Bookmark.category_id == BookmarkCategory.id)
        query = query.order_by(asc(BookmarkCategory.name), asc(Bookmark.name))
    elif sort in sort_map:
        query = query.order_by(sort_map[sort])
    else:
        query = query.order_by(desc(Bookmark.created_at))

    return query.all()


@router.post("", response_model=BookmarkOut, status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    data: BookmarkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new bookmark entry (admin only)."""
    if data.category_id:
        cat = db.query(BookmarkCategory).filter(BookmarkCategory.id == data.category_id).first()
        if not cat:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found")

    bookmark = Bookmark(
        name=data.name,
        description=data.description,
        url=data.url,
        category_id=data.category_id,
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)

    # Reload with category relationship
    return db.query(Bookmark).options(joinedload(Bookmark.category)).filter(Bookmark.id == bookmark.id).first()


@router.put("/{bookmark_id}", response_model=BookmarkOut)
async def update_bookmark(
    bookmark_id: int,
    data: BookmarkUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Update an existing bookmark (admin only)."""
    bookmark = db.query(Bookmark).filter(Bookmark.id == bookmark_id).first()
    if not bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")

    if data.name is not None:
        bookmark.name = data.name
    if data.description is not None:
        bookmark.description = data.description
    if data.url is not None:
        bookmark.url = data.url
    if data.category_id is not None:
        cat = db.query(BookmarkCategory).filter(BookmarkCategory.id == data.category_id).first()
        if not cat:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found")
        bookmark.category_id = data.category_id

    bookmark.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(bookmark)

    return db.query(Bookmark).options(joinedload(Bookmark.category)).filter(Bookmark.id == bookmark_id).first()


@router.delete("/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    bookmark_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Delete a bookmark (admin only)."""
    bookmark = db.query(Bookmark).filter(Bookmark.id == bookmark_id).first()
    if not bookmark:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found")
    db.delete(bookmark)
    db.commit()
