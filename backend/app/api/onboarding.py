import json
import os
import shutil
from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.onboarding import (
    ManagerPlaybook,
    OnboardingContent,
    OnboardingProgress,
    PlaybookAssignment,
    TaskEvidence,
    TaskSignOff,
)
from app.models.user import User, UserRole

router = APIRouter()

# LEADER is the new name for what was previously MENTOR_SE.
# LEADER can supervise progress but cannot customize playbooks (manager-only).

PHASES_KEY = "phases"
SETTINGS_KEY = "settings"

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "evidence")

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
        "objective": "Operate as a fully independent SE \u2014 own deals, lead POVs, contribute knowledge, and be recognized as a trusted advisor",
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
    record = db.query(OnboardingContent).filter_by(key=PHASES_KEY).first()
    if record is None:
        record = OnboardingContent(key=PHASES_KEY, data=json.dumps(DEFAULT_PHASES))
        db.add(record)
        db.commit()
        db.refresh(record)
    return record


def _get_or_create_manager_playbook(db: Session, manager_id: int) -> ManagerPlaybook:
    playbook = db.query(ManagerPlaybook).filter_by(manager_id=manager_id).first()
    if playbook is None:
        template = _get_or_create_record(db)
        playbook = ManagerPlaybook(
            manager_id=manager_id,
            name="My Playbook",
            data=template.data,
        )
        db.add(playbook)
        db.commit()
        db.refresh(playbook)
    return playbook


def _serialize_evidence(e: TaskEvidence) -> dict:
    return {
        "id": e.id,
        "task_id": e.task_id,
        "evidence_type": e.evidence_type,
        "content": e.content,
        "file_name": e.file_name,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _serialize_signoff(s: TaskSignOff, db: Session) -> dict:
    signer = db.query(User).filter_by(id=s.signed_by_id).first()
    return {
        "id": s.id,
        "task_id": s.task_id,
        "signed_by_name": signer.full_name if signer else "Unknown",
        "signed_by_role": signer.role.value if signer else "",
        "notes": s.notes,
        "signed_at": s.signed_at.isoformat() if s.signed_at else None,
    }


# ── Global template routes (admin only write) ─────────────────────────────────

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


# ── Page settings ──────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(OnboardingContent).filter_by(key=SETTINGS_KEY).first()
    if record is None:
        return DEFAULT_SETTINGS
    data = json.loads(record.data)
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
    data = {
        "title": payload.title,
        "subtitle": payload.subtitle,
        "ladderLabels": payload.ladderLabels,
        "ladderSubs": payload.ladderSubs,
        "tipCards": payload.tipCards,
    }
    if record is None:
        record = OnboardingContent(key=SETTINGS_KEY, data=json.dumps(data))
        db.add(record)
    else:
        record.data = json.dumps(data)
    db.commit()
    return {"ok": True}


# ── Manager playbook ───────────────────────────────────────────────────────────

@router.get("/playbook")
async def get_manager_playbook(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.MANAGER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Manager only")
    playbook = _get_or_create_manager_playbook(db, current_user.id)
    return {"phases": json.loads(playbook.data), "name": playbook.name}


@router.put("/playbook")
async def update_manager_playbook(
    payload: PhasesPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.MANAGER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Manager only")
    playbook = _get_or_create_manager_playbook(db, current_user.id)
    playbook.data = json.dumps(payload.phases)
    db.commit()
    return {"ok": True}


# ── Assignments ────────────────────────────────────────────────────────────────

@router.get("/assignments")
async def get_assignments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.MANAGER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Manager only")
    if current_user.role == UserRole.ADMIN:
        # Admin sees assignments across all playbooks
        assignments_all = db.query(PlaybookAssignment).all()
        result = []
        for a in assignments_all:
            eng = db.query(User).filter_by(id=a.engineer_id).first()
            leader = db.query(User).filter_by(id=a.mentor_se_id).first() if a.mentor_se_id else None
            result.append({
                "id": a.id,
                "engineer_id": a.engineer_id,
                "engineer_name": eng.full_name if eng else "Unknown",
                "engineer_email": eng.email if eng else "",
                "mentor_se_id": a.mentor_se_id,
                "mentor_se_name": leader.full_name if leader else None,
                "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
            })
        return {"assignments": result}
    playbook = db.query(ManagerPlaybook).filter_by(manager_id=current_user.id).first()
    if not playbook:
        return {"assignments": []}
    assignments = db.query(PlaybookAssignment).filter_by(playbook_id=playbook.id).all()
    result = []
    for a in assignments:
        eng = db.query(User).filter_by(id=a.engineer_id).first()
        mentor = db.query(User).filter_by(id=a.mentor_se_id).first() if a.mentor_se_id else None
        result.append({
            "id": a.id,
            "engineer_id": a.engineer_id,
            "engineer_name": eng.full_name if eng else "Unknown",
            "engineer_email": eng.email if eng else "",
            "mentor_se_id": a.mentor_se_id,
            "mentor_se_name": mentor.full_name if mentor else None,
            "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
        })
    return {"assignments": result}


class AssignmentPayload(BaseModel):
    engineer_id: int
    mentor_se_id: Optional[int] = None


@router.post("/assignments")
async def create_assignment(
    payload: AssignmentPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.MANAGER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Manager only")
    eng = db.query(User).filter_by(id=payload.engineer_id).first()
    if not eng:
        raise HTTPException(status_code=404, detail="Engineer not found")
    if payload.mentor_se_id:
        mentor = db.query(User).filter_by(id=payload.mentor_se_id).first()
        if not mentor:
            raise HTTPException(status_code=404, detail="Leader not found")
        if mentor.role not in (UserRole.LEADER, UserRole.ADMIN, UserRole.MANAGER):
            raise HTTPException(status_code=400, detail="Assigned leader must have the Leader role")
    playbook = _get_or_create_manager_playbook(db, current_user.id)
    existing = db.query(PlaybookAssignment).filter_by(engineer_id=payload.engineer_id).first()
    if existing:
        existing.playbook_id = playbook.id
        existing.mentor_se_id = payload.mentor_se_id
    else:
        existing = PlaybookAssignment(
            playbook_id=playbook.id,
            engineer_id=payload.engineer_id,
            mentor_se_id=payload.mentor_se_id,
        )
        db.add(existing)
    db.commit()
    return {"ok": True}


@router.delete("/assignments/{assignment_id}")
async def delete_assignment(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.MANAGER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Manager only")
    assignment = db.query(PlaybookAssignment).filter_by(id=assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    playbook = db.query(ManagerPlaybook).filter_by(id=assignment.playbook_id).first()
    if not playbook or playbook.manager_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your assignment")
    db.delete(assignment)
    db.commit()
    return {"ok": True}


# ── Engineer routes ────────────────────────────────────────────────────────────

@router.get("/leader-playbook")
async def get_leader_playbook(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the playbook phases that a leader is supervising (from their first assignment)."""
    if current_user.role not in (UserRole.LEADER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Leader only")
    assignment = db.query(PlaybookAssignment).filter_by(mentor_se_id=current_user.id).first()
    if not assignment:
        raise HTTPException(status_code=403, detail="You have not been assigned to supervise any engineers yet")
    playbook = db.query(ManagerPlaybook).filter_by(id=assignment.playbook_id).first()
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return {"phases": json.loads(playbook.data), "assigned": True}


@router.get("/my-playbook")
async def get_engineer_playbook(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assignment = db.query(PlaybookAssignment).filter_by(engineer_id=current_user.id).first()
    if not assignment:
        # Only assigned engineers can see a playbook
        raise HTTPException(status_code=403, detail="You have not been assigned to a playbook yet")
    playbook = db.query(ManagerPlaybook).filter_by(id=assignment.playbook_id).first()
    if not playbook:
        raise HTTPException(status_code=404, detail="Playbook not found")
    return {"phases": json.loads(playbook.data), "assigned": True}


@router.get("/my-assignment")
async def get_my_assignment(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assignment = db.query(PlaybookAssignment).filter_by(engineer_id=current_user.id).first()
    if not assignment:
        return {"assignment": None}
    playbook = db.query(ManagerPlaybook).filter_by(id=assignment.playbook_id).first()
    manager = db.query(User).filter_by(id=playbook.manager_id).first() if playbook else None
    mentor = db.query(User).filter_by(id=assignment.mentor_se_id).first() if assignment.mentor_se_id else None
    return {
        "assignment": {
            "id": assignment.id,
            "manager": {"id": manager.id, "name": manager.full_name, "email": manager.email} if manager else None,
            "mentor_se": {"id": mentor.id, "name": mentor.full_name} if mentor else None,
        }
    }


# ── Evidence ───────────────────────────────────────────────────────────────────

@router.get("/evidence")
async def get_evidence(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assignment = db.query(PlaybookAssignment).filter_by(engineer_id=current_user.id).first()
    if not assignment:
        return {"evidence": [], "signoffs": []}
    evidence = (
        db.query(TaskEvidence)
        .filter_by(assignment_id=assignment.id)
        .order_by(TaskEvidence.created_at)
        .all()
    )
    signoffs = db.query(TaskSignOff).filter_by(assignment_id=assignment.id).all()
    return {
        "evidence": [_serialize_evidence(e) for e in evidence],
        "signoffs": [_serialize_signoff(s, db) for s in signoffs],
    }


class EvidencePayload(BaseModel):
    task_id: str
    evidence_type: str
    content: str


@router.post("/evidence")
async def submit_evidence(
    payload: EvidencePayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assignment = db.query(PlaybookAssignment).filter_by(engineer_id=current_user.id).first()
    if not assignment:
        raise HTTPException(status_code=400, detail="You are not assigned to a playbook")
    if payload.evidence_type not in ("remark", "url"):
        raise HTTPException(status_code=400, detail="evidence_type must be 'remark' or 'url'")
    ev = TaskEvidence(
        assignment_id=assignment.id,
        task_id=payload.task_id,
        evidence_type=payload.evidence_type,
        content=payload.content,
        created_by=current_user.id,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return _serialize_evidence(ev)


@router.post("/evidence/upload")
async def upload_evidence_file(
    task_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assignment = db.query(PlaybookAssignment).filter_by(engineer_id=current_user.id).first()
    if not assignment:
        raise HTTPException(status_code=400, detail="You are not assigned to a playbook")
    allowed_types = {
        "application/pdf", "image/png", "image/jpeg", "image/gif",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    # Sanitize filename to prevent path traversal
    safe_name = f"{assignment.id}_{task_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{os.path.basename(file.filename or 'file')}"
    safe_name = safe_name.replace("..", "").replace("/", "_").replace("\\", "_")
    dest = os.path.join(UPLOAD_DIR, safe_name)
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    ev = TaskEvidence(
        assignment_id=assignment.id,
        task_id=task_id,
        evidence_type="file",
        file_name=file.filename,
        file_path=safe_name,
        created_by=current_user.id,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return _serialize_evidence(ev)


@router.delete("/evidence/{evidence_id}")
async def delete_evidence(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ev = db.query(TaskEvidence).filter_by(id=evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    if ev.created_by != current_user.id and current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(status_code=403, detail="Not authorized")
    if ev.file_path:
        try:
            os.remove(os.path.join(UPLOAD_DIR, ev.file_path))
        except OSError:
            pass
    db.delete(ev)
    db.commit()
    return {"ok": True}


# ── Sign-offs ──────────────────────────────────────────────────────────────────

class SignOffPayload(BaseModel):
    assignment_id: int
    task_id: str
    notes: Optional[str] = None


@router.post("/signoff")
async def sign_off_task(
    payload: SignOffPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.MANAGER, UserRole.LEADER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Manager or Leader only")
    assignment = db.query(PlaybookAssignment).filter_by(id=payload.assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if current_user.role == UserRole.MANAGER:
        playbook = db.query(ManagerPlaybook).filter_by(id=assignment.playbook_id).first()
        if not playbook or playbook.manager_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not your assignment")
    elif current_user.role == UserRole.LEADER:
        if assignment.mentor_se_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not your assignment")
    existing = (
        db.query(TaskSignOff)
        .filter_by(assignment_id=payload.assignment_id, task_id=payload.task_id)
        .first()
    )
    if existing:
        existing.signed_by_id = current_user.id
        existing.notes = payload.notes
        existing.signed_at = datetime.utcnow()
        so = existing
    else:
        so = TaskSignOff(
            assignment_id=payload.assignment_id,
            task_id=payload.task_id,
            signed_by_id=current_user.id,
            notes=payload.notes,
        )
        db.add(so)
    db.commit()
    db.refresh(so)
    return _serialize_signoff(so, db)


@router.delete("/signoff/{signoff_id}")
async def revoke_signoff(
    signoff_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.MANAGER, UserRole.LEADER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Manager or Leader only")
    so = db.query(TaskSignOff).filter_by(id=signoff_id).first()
    if not so:
        raise HTTPException(status_code=404, detail="Sign-off not found")
    db.delete(so)
    db.commit()
    return {"ok": True}


# ── Team progress ──────────────────────────────────────────────────────────────

@router.get("/team-progress")
async def get_team_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.MANAGER, UserRole.LEADER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Manager or Leader only")
    if current_user.role == UserRole.MANAGER:
        playbook = db.query(ManagerPlaybook).filter_by(manager_id=current_user.id).first()
        if not playbook:
            return {"engineers": []}
        assignments = db.query(PlaybookAssignment).filter_by(playbook_id=playbook.id).all()
    elif current_user.role == UserRole.LEADER:
        assignments = db.query(PlaybookAssignment).filter_by(mentor_se_id=current_user.id).all()
    else:
        assignments = db.query(PlaybookAssignment).all()

    engineers = []
    for a in assignments:
        eng = db.query(User).filter_by(id=a.engineer_id).first()
        mentor = db.query(User).filter_by(id=a.mentor_se_id).first() if a.mentor_se_id else None
        progress_row = db.query(OnboardingProgress).filter_by(user_id=a.engineer_id).first()
        checked_rows = json.loads(progress_row.data) if progress_row else {}
        evidence = (
            db.query(TaskEvidence)
            .filter_by(assignment_id=a.id)
            .order_by(TaskEvidence.created_at)
            .all()
        )
        signoffs = db.query(TaskSignOff).filter_by(assignment_id=a.id).all()
        engineers.append({
            "assignment_id": a.id,
            "engineer_id": eng.id if eng else a.engineer_id,
            "engineer_name": eng.full_name if eng else "Unknown",
            "engineer_email": eng.email if eng else "",
            "mentor_se_name": mentor.full_name if mentor else None,
            "checked_rows": checked_rows,
            "evidence": [_serialize_evidence(e) for e in evidence],
            "signoffs": [_serialize_signoff(s, db) for s in signoffs],
        })
    return {"engineers": engineers}


# ── User listing for assignment picker ─────────────────────────────────────────

@router.get("/users")
async def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.MANAGER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Manager or Admin only")
    users = db.query(User).filter(User.is_active == True).all()
    return {
        "users": [
            {"id": u.id, "name": u.full_name, "email": u.email, "role": u.role.value}
            for u in users
        ]
    }

