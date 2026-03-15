import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any, List
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.onboarding import OnboardingContent, OnboardingProgress

router = APIRouter()

PHASES_KEY = "phases"
SETTINGS_KEY = "settings"

DEFAULT_SETTINGS = {
    "title": "Enterprise SE Onboarding Playbook",
    "subtitle": "Industrial Model",
    "ladderLabels": ["Systems Operator", "Story Architect", "Customer Strategist", "Field-Ready SE"],
    "ladderSubs": ["Phase 1 \u00b7 0\u201330 Days", "Phase 2 \u00b7 31\u201360 Days", "Phase 3 \u00b7 61\u201390 Days", "Phase 4 \u00b7 91\u2013120 Days"],
    "tipCards": [
        "Bookmark this page for easy access as you navigate throughout your SE onboarding journey.",
        "Check off items as you go to track your progress. Your progress is automatically saved to your account.",
        "Can\u2019t find what you need? Your assigned mentor or manager is ready to provide 1:1 support.",
    ],
}

# ── Default seed data (mirrors initialPhases in the frontend) ─────────────────
DEFAULT_PHASES = [
    {
        "id": "phase1",
        "title": "Phase 1: 0\u201330 Days",
        "objective": "Technical Independence + Platform Narrative",
        "rows": [
            {"id": "p1r1", "category": "Environment & Tools", "module": "Lab + demo environment fully operational", "duration": "3\u20135 days", "deliverable": "Live demo run-through without assistance", "signOff": "Mentor SE"},
            {"id": "p1r2", "category": "Platform Narrative", "module": "5\u20137 min platform story (security outcomes + architecture)", "duration": "1 week (parallel)", "deliverable": "Recorded narrative delivery", "signOff": "Manager"},
            {"id": "p1r3", "category": "Domain Selection", "module": "Choose primary domain (FW / ZTA / SSE / etc.)", "duration": "Week 1", "deliverable": "Domain declaration + learning plan", "signOff": "Manager"},
            {"id": "p1r4", "category": "Hands-on Repetition", "module": "Daily lab reps tied to 2\u20133 top use cases", "duration": "Ongoing (15\u201330 min daily)", "deliverable": "Reproducible demo baseline", "signOff": "Mentor SE"},
            {"id": "p1r5", "category": "Sales Motion Basics", "module": "Shadow 2\u20133 calls (discovery + technical)", "duration": "2 weeks", "deliverable": "Written observation summary", "signOff": "Manager"},
        ],
    },
    {
        "id": "phase2",
        "title": "Phase 2: 31\u201360 Days",
        "objective": "Controlled Customer Engagement",
        "rows": [
            {"id": "p2r1", "category": "Demo Craft", "module": "Build Minimum Viable Demo (MVD)", "duration": "1\u20132 weeks", "deliverable": "Structured demo flow (Intro \u2192 Use Case \u2192 Differentiation \u2192 Close)", "signOff": "Domain Lead"},
            {"id": "p2r2", "category": "Discovery Skills", "module": "Co-lead 1 discovery call", "duration": "Within 30 days", "deliverable": "Discovery notes + pain mapping", "signOff": "Manager"},
            {"id": "p2r3", "category": "Competitive Readiness", "module": "Top 2 competitors + 10 objection responses", "duration": "1 week", "deliverable": "Competitive positioning sheet", "signOff": "Domain Lead"},
            {"id": "p2r4", "category": "Scoping & Licensing", "module": "Basic sizing + licensing fundamentals", "duration": "1 week", "deliverable": "Sample sizing + BOM scenario", "signOff": "Senior SE"},
            {"id": "p2r5", "category": "Enterprise Exposure", "module": "Participate in 1 RFP / questionnaire", "duration": "Within 60 days", "deliverable": "Edited submission section", "signOff": "Manager"},
        ],
    },
    {
        "id": "phase3",
        "title": "Phase 3: 61\u201390 Days",
        "objective": "Partial Ownership",
        "rows": [
            {"id": "p3r1", "category": "Discovery Leadership", "module": "Lead 1 discovery session", "duration": "Within 30 days", "deliverable": "Customer pain summary + next-step doc", "signOff": "Manager"},
            {"id": "p3r2", "category": "POV Mechanics", "module": "Write a POV plan (success criteria, scope, risks)", "duration": "1 week", "deliverable": "POV document draft", "signOff": "Senior SE"},
            {"id": "p3r3", "category": "Technical Escalation Literacy", "module": "Observe 1 real escalation / TAC path", "duration": "Ongoing", "deliverable": "Lessons learned summary", "signOff": "Mentor"},
            {"id": "p3r4", "category": "Demo Scaling", "module": "Deliver demo to real customer (controlled)", "duration": "1\u20132 opportunities", "deliverable": "Customer feedback", "signOff": "Manager"},
            {"id": "p3r5", "category": "Domain Certification", "module": "Internal domain assessment (formal or informal exam)", "duration": "By Day 90", "deliverable": "Pass result", "signOff": "Domain Lead"},
        ],
    },
    {
        "id": "phase4",
        "title": "Phase 4: 91\u2013120 Days",
        "objective": "Field Ownership & Enterprise Competency",
        "rows": [
            {"id": "p4r1", "category": "POV Ownership", "module": "Lead controlled POV", "duration": "2\u20134 weeks", "deliverable": "POV execution + success report", "signOff": "Manager"},
            {"id": "p4r2", "category": "Commercial Integration", "module": "Lead sizing + licensing discussion", "duration": "1 deal cycle", "deliverable": "Approved BOM + pricing alignment", "signOff": "Account Team"},
            {"id": "p4r3", "category": "Executive Positioning", "module": "Deliver executive-level summary (10 min)", "duration": "1 opportunity", "deliverable": "Exec recap slide", "signOff": "Manager"},
            {"id": "p4r4", "category": "Complex Objection Handling", "module": "Handle competitive pushback live", "duration": "As encountered", "deliverable": "Manager feedback", "signOff": "Manager"},
            {"id": "p4r5", "category": "Knowledge Contribution", "module": "Contribute artifact (demo doc / battlecard / RFP response template)", "duration": "By Day 120", "deliverable": "Reusable asset", "signOff": "Domain Lead"},
        ],
    },
]


def _get_or_create_record(db: Session) -> OnboardingContent:
    """Return the phases row, seeding with defaults if not yet present."""
    record = db.query(OnboardingContent).filter_by(key=PHASES_KEY).first()
    if record is None:
        record = OnboardingContent(key=PHASES_KEY, data=json.dumps(DEFAULT_PHASES))
        db.add(record)
        db.commit()
        db.refresh(record)
    return record


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.get("/phases")
async def get_phases(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = _get_or_create_record(db)
    return {"phases": json.loads(record.data)}


class PhasesPayload(BaseModel):
    phases: List[Any]


@router.put("/phases")
async def update_phases(
    payload: PhasesPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    record = _get_or_create_record(db)
    record.data = json.dumps(payload.phases)
    db.commit()
    return {"ok": True}


# ── Per-user progress ──────────────────────────────────────────────────────────

@router.get("/progress")
async def get_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(OnboardingProgress).filter_by(user_id=current_user.id).first()
    return {"checkedRows": json.loads(row.data) if row else {}}


class ProgressPayload(BaseModel):
    checkedRows: dict


@router.put("/progress")
async def update_progress(
    payload: ProgressPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.query(OnboardingProgress).filter_by(user_id=current_user.id).first()
    if row is None:
        row = OnboardingProgress(user_id=current_user.id, data=json.dumps(payload.checkedRows))
        db.add(row)
    else:
        row.data = json.dumps(payload.checkedRows)
    db.commit()
    return {"ok": True}


# ── Page settings (title, subtitle, ladder labels) ─────────────────────────────

@router.get("/settings")
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(OnboardingContent).filter_by(key=SETTINGS_KEY).first()
    if record is None:
        return DEFAULT_SETTINGS
    data = json.loads(record.data)
    # Merge with defaults to ensure all keys exist
    return {**DEFAULT_SETTINGS, **data}


class SettingsPayload(BaseModel):
    title: str
    subtitle: str
    ladderLabels: List[str]
    ladderSubs: List[str] = ["Phase 1 \u00b7 0\u201330 Days", "Phase 2 \u00b7 31\u201360 Days", "Phase 3 \u00b7 61\u201390 Days", "Phase 4 \u00b7 91\u2013120 Days"]


@router.put("/settings")
async def update_settings(
    payload: SettingsPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    record = db.query(OnboardingContent).filter_by(key=SETTINGS_KEY).first()
    data = {"title": payload.title, "subtitle": payload.subtitle, "ladderLabels": payload.ladderLabels, "ladderSubs": payload.ladderSubs}
    if record is None:
        record = OnboardingContent(key=SETTINGS_KEY, data=json.dumps(data))
        db.add(record)
    else:
        record.data = json.dumps(data)
    db.commit()
    return {"ok": True}
