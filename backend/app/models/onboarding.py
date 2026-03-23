from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
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


class ManagerPlaybook(Base):
    """Per-manager copy of the onboarding playbook, derived from the global template."""
    __tablename__ = "manager_playbooks"

    id = Column(Integer, primary_key=True, index=True)
    manager_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    name = Column(String, nullable=False, default="My Playbook")
    data = Column(Text, nullable=False)   # JSON phases array
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlaybookAssignment(Base):
    """Assigns an engineer to a manager's playbook, optionally with a mentor SE."""
    __tablename__ = "playbook_assignments"

    id = Column(Integer, primary_key=True, index=True)
    playbook_id = Column(Integer, ForeignKey("manager_playbooks.id", ondelete="CASCADE"), index=True)
    engineer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    mentor_se_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_at = Column(DateTime, default=datetime.utcnow)


class TaskEvidence(Base):
    """Evidence submitted by an engineer proving completion of a task."""
    __tablename__ = "task_evidence"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("playbook_assignments.id", ondelete="CASCADE"), index=True)
    task_id = Column(String, nullable=False, index=True)      # e.g. "p1r1"
    evidence_type = Column(String, nullable=False)            # "remark", "url", "file"
    content = Column(Text, nullable=True)                     # text remark or URL
    file_name = Column(String, nullable=True)                 # original filename for uploads
    file_path = Column(String, nullable=True)                 # server path for file uploads
    created_by = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    created_at = Column(DateTime, default=datetime.utcnow)


class TaskSignOff(Base):
    """Manager or Mentor SE approval of an engineer's completed task."""
    __tablename__ = "task_signoffs"

    id = Column(Integer, primary_key=True, index=True)
    assignment_id = Column(Integer, ForeignKey("playbook_assignments.id", ondelete="CASCADE"), index=True)
    task_id = Column(String, nullable=False)
    signed_by_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    notes = Column(Text, nullable=True)
    signed_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("assignment_id", "task_id", name="uq_signoff_task"),)
