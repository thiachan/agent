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

# ── Default seed data ─────────────────────────────────────────────────────────
DEFAULT_PHASES = [
    {
        "id": "phase1",
        "title": "Mission 1: Ninja (Day 0 - 30)",
        "objective": "Build foundational knowledge, complete all system setup, and understand how the SE role supports the Cisco sales process",
        "rows": [
            {"id": "p1r1", "category": "Manager Alignment", "module": "Define territory coverage, account strategy, 90-day success plan", "url": "", "duration": "Week 1", "deliverable": "90-day plan document", "signOff": "Manager"},
            {"id": "p1r2", "category": "Access & Tools", "module": "Complete all required sales and SE system access setup (Salesforce, CCW, dCloud)", "url": "", "duration": "Week 1", "deliverable": "All systems accessible and verified", "signOff": "Manager"},
            {"id": "p1r3", "category": "One Cisco Story", "module": "Learn, align and present the One Cisco Story framework", "url": "", "duration": "Week 2", "deliverable": "Recorded narrative delivery", "signOff": "Mentor SE"},
            {"id": "p1r4", "category": "Portfolio Familiarization", "module": "Develop foundational knowledge across focused domains and competitive landscape", "url": "", "duration": "Weeks 2-3", "deliverable": "Domain declaration + learning plan", "signOff": "Manager"},
            {"id": "p1r5", "category": "Labs and Demo Environment", "module": "Complete focused labs and walk-thru Instant Demo", "url": "", "duration": "Weeks 3-4", "deliverable": "Live demo run-through without assistance", "signOff": "Mentor SE"},
        ],
    },
    {
        "id": "phase2",
        "title": "Mission 2: Samurai (Day 31 - 60)",
        "objective": "Participate in customer engagements, support discovery and demos, and understand how opportunities progress through the sales cycle",
        "rows": [
            {"id": "p2r1", "category": "Sales Engagement & Build Rapport", "module": "Conduct introductory partner / customer meeting with mentor SE support", "url": "", "duration": "Week 5", "deliverable": "Meeting notes + follow-up summary", "signOff": "Manager"},
            {"id": "p2r2", "category": "Discovery Skills", "module": "Co-lead a discovery call and map customer pain points to Cisco solutions", "url": "", "duration": "Weeks 5-6", "deliverable": "Discovery notes + pain mapping doc", "signOff": "Manager"},
            {"id": "p2r3", "category": "Demo Craft", "module": "Build and deliver your Minimum Viable Demo (MVD) with a structured flow", "url": "", "duration": "Weeks 6-7", "deliverable": "Recorded MVD: Intro \u2192 Use Case \u2192 Differentiation \u2192 Close", "signOff": "Domain Lead"},
            {"id": "p2r4", "category": "Competitive Readiness", "module": "Research top 2 competitors and develop 10 objection handling responses", "url": "", "duration": "Week 7", "deliverable": "Competitive positioning sheet", "signOff": "Domain Lead"},
            {"id": "p2r5", "category": "Scoping & Licensing Basics", "module": "Learn basic sizing, licensing, and participate in an RFP or questionnaire", "url": "", "duration": "Weeks 7-8", "deliverable": "Sample BOM + edited RFP section", "signOff": "Senior SE"},
        ],
    },
    {
        "id": "phase3",
        "title": "Mission 3: Daimyo (Day 61 - 90)",
        "objective": "Lead customer engagements independently, own technical win strategy, and demonstrate domain expertise",
        "rows": [
            {"id": "p3r1", "category": "Discovery Leadership", "module": "Lead a full discovery session independently and deliver customer pain summary", "url": "", "duration": "Weeks 9-10", "deliverable": "Customer pain summary + next-step doc", "signOff": "Manager"},
            {"id": "p3r2", "category": "POV Planning", "module": "Write a complete POV plan with success criteria, scope, timeline, and risk assessment", "url": "", "duration": "Week 10", "deliverable": "POV document draft approved by manager", "signOff": "Senior SE"},
            {"id": "p3r3", "category": "Customer Demo Delivery", "module": "Deliver a full demo to a real customer opportunity (controlled environment)", "url": "", "duration": "Weeks 10-12", "deliverable": "Customer feedback score + manager debrief", "signOff": "Manager"},
            {"id": "p3r4", "category": "Technical Escalation Literacy", "module": "Shadow or participate in a real TAC escalation or complex technical issue resolution", "url": "", "duration": "Ongoing", "deliverable": "Lessons learned summary", "signOff": "Mentor SE"},
            {"id": "p3r5", "category": "Domain Certification", "module": "Complete internal domain assessment or certification exam for primary Cisco portfolio area", "url": "", "duration": "By Day 90", "deliverable": "Pass result / certification badge", "signOff": "Domain Lead"},
        ],
    },
    {
        "id": "phase4",
        "title": "Mission 4: Sensei (Day 91 - 120)",
        "objective": "Operate as a fully independent SE — own deals, lead POVs, contribute knowledge, and be recognized as a trusted advisor",
        "rows": [
            {"id": "p4r1", "category": "POV Ownership", "module": "Lead a controlled POV from kickoff through execution to final success report", "url": "", "duration": "Weeks 13-16", "deliverable": "POV execution plan + success report", "signOff": "Manager"},
            {"id": "p4r2", "category": "Commercial Integration", "module": "Own the full sizing and licensing discussion within an active deal cycle", "url": "", "duration": "1 deal cycle", "deliverable": "Approved BOM + pricing alignment with account team", "signOff": "Account Team"},
            {"id": "p4r3", "category": "Executive Positioning", "module": "Deliver a 10-minute executive-level summary to a C-level or VP stakeholder", "url": "", "duration": "1 opportunity", "deliverable": "Exec recap slide + manager debrief", "signOff": "Manager"},
            {"id": "p4r4", "category": "Complex Objection Handling", "module": "Handle live competitive pushback or technical objections without manager assistance", "url": "", "duration": "As encountered", "deliverable": "Manager observation feedback", "signOff": "Manager"},
            {"id": "p4r5", "category": "Knowledge Contribution", "module": "Contribute a reusable artifact: demo guide, battlecard, or RFP response template", "url": "", "duration": "By Day 120", "deliverable": "Published artifact shared with the SE team", "signOff": "Domain Lead"},
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
    tipCards: List[str] = []


@router.put("/settings")
async def update_settings(
    payload: SettingsPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    record = db.query(OnboardingContent).filter_by(key=SETTINGS_KEY).first()
    data = {"title": payload.title, "subtitle": payload.subtitle, "ladderLabels": payload.ladderLabels, "ladderSubs": payload.ladderSubs, "tipCards": payload.tipCards}
    if record is None:
        record = OnboardingContent(key=SETTINGS_KEY, data=json.dumps(data))
        db.add(record)
    else:
        record.data = json.dumps(data)
    db.commit()
    return {"ok": True}
