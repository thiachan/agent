from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base


class OnboardingContent(Base):
    __tablename__ = "onboarding_content"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)   # e.g. "phases"
    data = Column(Text, nullable=False)             # JSON blob
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OnboardingProgress(Base):
    """Per-user progress — stores the checkedRows JSON keyed by user id."""
    __tablename__ = "onboarding_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    data = Column(Text, nullable=False, default="{}")   # JSON: { "rowId": true, ... }
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
