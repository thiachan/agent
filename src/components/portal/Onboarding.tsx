'use client'

import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { api } from '@/lib/api'
import {
  Check, ChevronDown, ExternalLink, FileText, Lightbulb, Link, Lock,
  MessageSquare, Paperclip, Pencil, Plus, Shield, Trophy, Users, X
} from 'lucide-react'

// ── Types ──────────────────────────────────────────────────────────────────────
interface LearnMoreItem {
  id: string
  type: 'link' | 'text'
  label: string
  url?: string
}

interface Task {
  id: string
  category: string
  module: string
  url?: string
  learnMore?: LearnMoreItem[]
  duration?: string
  deliverable?: string
  signOff?: string
}

interface Phase {
  id: string
  title: string
  objective: string
  rows: Task[]
}

interface EvidenceItem {
  id: number
  task_id: string
  evidence_type: 'remark' | 'url' | 'file'
  content: string | null
  file_name: string | null
  created_at: string
}

interface SignOff {
  id: number
  task_id: string
  signed_by_name: string
  signed_by_role: string
  notes: string | null
  signed_at: string
}

interface EngineerProgress {
  assignment_id: number
  engineer_id: number
  engineer_name: string
  engineer_email: string
  mentor_se_name: string | null
  checked_rows: Record<string, boolean>
  evidence: EvidenceItem[]
  signoffs: SignOff[]
}

interface AssignmentInfo {
  id: number
  manager: { id: number; name: string; email: string } | null
  mentor_se: { id: number; name: string } | null
}

// ── Helpers ────────────────────────────────────────────────────────────────────
const rnd = () => Math.random().toString(36).slice(2, 10)

const ACCENTS = [
  { pill: 'bg-cyan-500',    gradient: 'from-cyan-600 to-blue-700',     dot: 'bg-cyan-500',    dotGlow: 'shadow-cyan-500/50',    icon: '🥷' },
  { pill: 'bg-purple-500',  gradient: 'from-purple-600 to-indigo-700', dot: 'bg-purple-500',  dotGlow: 'shadow-purple-500/50',  icon: '⚔️' },
  { pill: 'bg-amber-500',   gradient: 'from-amber-500 to-orange-600',  dot: 'bg-amber-500',   dotGlow: 'shadow-amber-500/50',   icon: '🛡️' },
  { pill: 'bg-emerald-500', gradient: 'from-emerald-600 to-green-700', dot: 'bg-emerald-500', dotGlow: 'shadow-emerald-500/50', icon: '🎓' },
]

const DEFAULT_TIPS = [
  'Bookmark this page for easy access as you navigate throughout your SE onboarding journey.',
  'Check off items as you go to track your progress. Your progress is automatically saved to your account.',
  "Can't find what you need? Your assigned mentor or manager is ready to provide 1:1 support.",
]

function fmtDate(iso: string) {
  try { return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) }
  catch { return iso }
}

// Parse "[label](url)" markdown links into React nodes
function renderMarkdownLinks(text: string): React.ReactNode {
  const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g
  const parts: React.ReactNode[] = []
  let last = 0; let m: RegExpExecArray | null
  while ((m = linkRegex.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index))
    parts.push(
      <a key={m.index} href={m[2]} target="_blank" rel="noopener noreferrer"
         className="inline-flex items-center gap-0.5 text-blue-400 hover:text-blue-300 hover:underline transition-colors">
        <ExternalLink className="w-3 h-3 flex-shrink-0" />{m[1]}
      </a>
    )
    last = m.index + m[0].length
  }
  if (last < text.length) parts.push(text.slice(last))
  return parts.length === 0 ? null : parts.length === 1 ? parts[0] : <>{parts}</>
}

function renderDeliverable(raw: string): React.ReactNode {
  const lines = raw.split('\n').map(l => l.replace(/^-\s*/, '').trim()).filter(Boolean)
  if (lines.length === 0) return null
  return (
    <ul className="space-y-1">
      {lines.map((line, i) => {
        const content = renderMarkdownLinks(line)
        return (
          <li key={i} className="flex items-start gap-1.5 text-xs text-slate-300">
            <span className="text-slate-500 flex-shrink-0 mt-0.5">•</span>
            <span className="break-words">{content}</span>
          </li>
        )
      })}
    </ul>
  )
}

// ── Component ──────────────────────────────────────────────────────────────────
export function Onboarding({ simulateUser = false }: { simulateUser?: boolean }) {
  const user = useAuthStore(s => s.user)
  const isAdmin    = !simulateUser && user?.role === 'admin'
  const isManager  = !simulateUser && user?.role === 'manager'
  const isLeader   = !simulateUser && user?.role === 'leader'
  const isEngineer = !simulateUser && (user?.role === 'engineer' || user?.role === 'employee')
  const canEditPhases = isAdmin || isManager
  const canSignOff    = isManager || isLeader || isAdmin

  // ── Playbook data ──
  const [phases, setPhases] = useState<Phase[]>([])
  const [notAssigned, setNotAssigned] = useState(false)
  const [activeTab, setActiveTab] = useState(0)
  const [checked, setChecked] = useState<Record<string, boolean>>({})
  const [tips, setTips] = useState<string[]>(DEFAULT_TIPS)
  const [pageTitle, setPageTitle] = useState('Enterprise SE Onboarding Playbook')
  const [pageSub, setPageSub]   = useState('Industrial Model')

  // ── View mode (playbook vs team) ──
  const [viewMode, setViewMode] = useState<'playbook' | 'team'>('playbook')

  // ── Team view state ──
  const [teamData, setTeamData]           = useState<EngineerProgress[]>([])
  const [expandedEng, setExpandedEng]     = useState<number | null>(null)
  const [signoffForm, setSignoffForm]     = useState<{ assignmentId: number; taskId: string; notes: string } | null>(null)
  const [signingOff, setSigningOff]       = useState(false)
  // Assignment management
  const [showAssignForm, setShowAssignForm] = useState(false)
  const [availableUsers, setAvailableUsers] = useState<{ id: number; name: string; email: string; role: string }[]>([])
  const [assignEngineerId, setAssignEngineerId]   = useState<number | ''>('')
  const [assignMentorId,   setAssignMentorId]     = useState<number | ''>('')
  const [assigning, setAssigning] = useState(false)

  // ── Engineer evidence & sign-off state ──
  const [myAssignment,   setMyAssignment]   = useState<AssignmentInfo | null>(null)
  const [myEvidence,     setMyEvidence]     = useState<Record<string, EvidenceItem[]>>({})
  const [mySignoffs,     setMySignoffs]     = useState<Record<string, SignOff>>({})
  const [expandedEv,     setExpandedEv]     = useState<Set<string>>(new Set())
  const [evForm,         setEvForm]         = useState<{ taskId: string; type: 'remark' | 'url'; value: string } | null>(null)
  const [evSubmitting,   setEvSubmitting]   = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploadTaskId,   setUploadTaskId]   = useState<string | null>(null)

  // ── Inline edit state ──
  type TaskField = 'category' | 'module' | 'url' | 'deliverable'
  const [editTask,      setEditTask]      = useState<{ pId: string; tId: string; field: TaskField } | null>(null)
  const [editVal,       setEditVal]       = useState('')
  const [editPhase,     setEditPhase]     = useState<{ pId: string; field: 'title' | 'objective' } | null>(null)
  const [editPhaseVal,  setEditPhaseVal]  = useState('')
  const [editPageField, setEditPageField] = useState<'title' | 'sub' | null>(null)
  const [editPageVal,   setEditPageVal]   = useState('')
  const [editTipIdx,    setEditTipIdx]    = useState<number | null>(null)
  const [editTipVal,    setEditTipVal]    = useState('')

  // ── Learn More state ──
  const [expandedLM, setExpandedLM] = useState<Set<string>>(new Set())
  const [lmEdit,     setLmEdit]     = useState<{
    pId: string; taskId: string; itemId: string | null
    type: 'link' | 'text'; label: string; url: string
  } | null>(null)

  // ── Celebration state ──
  const [fireworks,    setFireworks]    = useState(false)
  const [unlockPopup,  setUnlockPopup]  = useState<number | null>(null)
  const prevChecked   = useRef<Record<string, boolean>>({})
  const prevAllDone   = useRef(false)

  // ── Data loading ──────────────────────────────────────────────────────────────
  useEffect(() => {
    const load = async () => {
      try {
        let phasesEndpoint = '/api/onboarding/phases'
        if (isManager)       phasesEndpoint = '/api/onboarding/playbook'
        else if (isLeader)   phasesEndpoint = '/api/onboarding/leader-playbook'
        else if (isEngineer) phasesEndpoint = '/api/onboarding/my-playbook'

        const [phasesRes, progressRes, settingsRes] = await Promise.all([
          (isEngineer || isLeader)
            ? api.get(phasesEndpoint).catch(() => { setNotAssigned(true); return { data: { phases: [], assigned: false } } })
            : api.get(phasesEndpoint),
          api.get('/api/onboarding/progress'),
          api.get('/api/onboarding/settings'),
        ])
        setPhases(phasesRes.data.phases || [])
        setChecked(progressRes.data.checkedRows || {})
        const s = settingsRes.data
        if (s.title) setPageTitle(s.title)
        if (s.subtitle) setPageSub(s.subtitle)
        if (s.tipCards?.length) setTips(s.tipCards)

        if (isManager || isLeader || isAdmin) {
          const teamRes = await api.get('/api/onboarding/team-progress')
          setTeamData(teamRes.data.engineers || [])
        }

        if (isEngineer) {
          const [assignRes, evidenceRes] = await Promise.allSettled([
            api.get('/api/onboarding/my-assignment'),
            api.get('/api/onboarding/evidence'),
          ])
          if (assignRes.status === 'fulfilled' && assignRes.value.data.assignment) {
            setMyAssignment(assignRes.value.data.assignment)
          }
          if (evidenceRes.status === 'fulfilled') {
            const evMap: Record<string, EvidenceItem[]> = {}
            for (const ev of evidenceRes.value.data.evidence || []) {
              if (!evMap[ev.task_id]) evMap[ev.task_id] = []
              evMap[ev.task_id].push(ev)
            }
            setMyEvidence(evMap)
            const soMap: Record<string, SignOff> = {}
            for (const so of evidenceRes.value.data.signoffs || []) soMap[so.task_id] = so
            setMySignoffs(soMap)
          }
        }
      } catch (e) {
        console.error('Onboarding load error:', e)
      }
    }
    load()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin, isManager, isLeader, isEngineer])

  // ── Save helpers ──────────────────────────────────────────────────────────────
  const savePhases = useCallback((updated: Phase[]) => {
    const endpoint = isManager ? '/api/onboarding/playbook' : '/api/onboarding/phases'
    api.put(endpoint, { phases: updated }).catch(console.error)
  }, [isManager])

  const saveSettings = useCallback((title: string, sub: string, tc: string[]) => {
    api.put('/api/onboarding/settings', {
      title, subtitle: sub, ladderLabels: [], ladderSubs: [], tipCards: tc,
    }).catch(console.error)
  }, [])

  const saveProgress = useCallback((next: Record<string, boolean>) => {
    api.put('/api/onboarding/progress', { checkedRows: next }).catch(console.error)
  }, [])

  // ── Phase lock ────────────────────────────────────────────────────────────────
  const isLocked = (idx: number) => {
    if (idx === 0 || canEditPhases) return false
    const prev = phases[idx - 1]
    if (!prev) return false
    return !prev.rows.every(r => checked[r.id])
  }

  // ── Toggle task completion ────────────────────────────────────────────────────
  const toggle = (rowId: string) => {
    const next = { ...checked, [rowId]: !checked[rowId] }
    setChecked(next)
    saveProgress(next)
  }

  // ── Celebration effects ───────────────────────────────────────────────────────
  useEffect(() => {
    if (!phases.length) return
    const allIds = phases.flatMap(p => p.rows.map(r => r.id))
    const allDone = allIds.every(id => checked[id])
    if (allDone && !prevAllDone.current && allIds.length > 0) setFireworks(true)
    prevAllDone.current = allDone

    phases.forEach((p, i) => {
      if (i === 0) return
      const allRowsDone = p.rows.every(r => checked[r.id])
      const wasDone = p.rows.every(r => prevChecked.current[r.id])
      if (allRowsDone && !wasDone) setTimeout(() => setUnlockPopup(i + 1 < phases.length ? i + 1 : null), 400)
    })
    prevChecked.current = checked
  }, [checked, phases])

  // ── Task edit helpers ─────────────────────────────────────────────────────────
  const startTaskEdit = (pId: string, tId: string, field: TaskField, val: string) => {
    setEditTask({ pId, tId, field }); setEditVal(val)
  }
  const commitTaskEdit = () => {
    if (!editTask) return
    const upd = phases.map(p =>
      p.id !== editTask.pId ? p : {
        ...p,
        rows: p.rows.map(r => r.id !== editTask.tId ? r : { ...r, [editTask.field]: editVal }),
      }
    )
    setPhases(upd); savePhases(upd); setEditTask(null)
  }

  const addTask = (pId: string, afterIdx?: number) => {
    const newTask: Task = {
      id: rnd(), category: 'New Task', module: 'Add description here.',
      url: '', learnMore: [], duration: '', deliverable: '', signOff: 'Manager',
    }
    const upd = phases.map(p => {
      if (p.id !== pId) return p
      const rows = [...p.rows]
      typeof afterIdx === 'number' ? rows.splice(afterIdx + 1, 0, newTask) : rows.push(newTask)
      return { ...p, rows }
    })
    setPhases(upd); savePhases(upd)
  }

  const deleteTask = (pId: string, tId: string) => {
    const upd = phases.map(p =>
      p.id !== pId ? p : { ...p, rows: p.rows.filter(r => r.id !== tId) }
    )
    setPhases(upd); savePhases(upd)
  }

  const commitPhaseEdit = () => {
    if (!editPhase) return
    const upd = phases.map(p =>
      p.id !== editPhase.pId ? p : { ...p, [editPhase.field]: editPhaseVal }
    )
    setPhases(upd); savePhases(upd); setEditPhase(null)
  }

  // ── Learn More helpers ────────────────────────────────────────────────────────
  const toggleLM = (taskId: string) => {
    setExpandedLM(s => { const n = new Set(s); n.has(taskId) ? n.delete(taskId) : n.add(taskId); return n })
  }
  const saveLMItems = (pId: string, tId: string, items: LearnMoreItem[]) => {
    const upd = phases.map(p =>
      p.id !== pId ? p : { ...p, rows: p.rows.map(r => r.id !== tId ? r : { ...r, learnMore: items }) }
    )
    setPhases(upd); savePhases(upd)
  }
  const commitLMEdit = (pId: string) => {
    if (!lmEdit) return
    const phase = phases.find(p => p.id === pId)
    if (!phase) return
    const task = phase.rows.find(r => r.id === lmEdit.taskId)
    if (!task) return
    const items = task.learnMore || []
    const newItem: LearnMoreItem = { id: lmEdit.itemId || rnd(), type: lmEdit.type, label: lmEdit.label, url: lmEdit.url || undefined }
    const updated = lmEdit.itemId ? items.map(i => i.id === lmEdit.itemId ? newItem : i) : [...items, newItem]
    saveLMItems(pId, lmEdit.taskId, updated)
    setLmEdit(null)
  }

  // ── Evidence helpers ──────────────────────────────────────────────────────────
  const toggleEv = (taskId: string) => {
    setExpandedEv(s => { const n = new Set(s); n.has(taskId) ? n.delete(taskId) : n.add(taskId); return n })
  }

  const submitEvidence = async () => {
    if (!evForm || !evForm.value.trim()) return
    setEvSubmitting(true)
    try {
      const res = await api.post('/api/onboarding/evidence', {
        task_id: evForm.taskId, evidence_type: evForm.type, content: evForm.value.trim(),
      })
      const item: EvidenceItem = res.data
      setMyEvidence(prev => ({ ...prev, [item.task_id]: [...(prev[item.task_id] || []), item] }))
      setEvForm(null)
    } catch (e) { console.error(e) }
    finally { setEvSubmitting(false) }
  }

  const deleteEvidence = async (item: EvidenceItem) => {
    try {
      await api.delete(`/api/onboarding/evidence/${item.id}`)
      setMyEvidence(prev => ({
        ...prev,
        [item.task_id]: (prev[item.task_id] || []).filter(e => e.id !== item.id),
      }))
    } catch (e) { console.error(e) }
  }

  const uploadFile = async (taskId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await api.post(`/api/onboarding/evidence/upload?task_id=${encodeURIComponent(taskId)}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      const item: EvidenceItem = res.data
      setMyEvidence(prev => ({ ...prev, [item.task_id]: [...(prev[item.task_id] || []), item] }))
    } catch (e) { console.error(e) }
  }

  // ── Sign-off helpers ──────────────────────────────────────────────────────────
  const submitSignOff = async (assignmentId: number, taskId: string, notes: string) => {
    setSigningOff(true)
    try {
      const res = await api.post('/api/onboarding/signoff', { assignment_id: assignmentId, task_id: taskId, notes: notes || null })
      const so: SignOff = res.data
      setTeamData(prev => prev.map(eng =>
        eng.assignment_id !== assignmentId ? eng : {
          ...eng,
          signoffs: [...eng.signoffs.filter(s => s.task_id !== taskId), so],
        }
      ))
      setSignoffForm(null)
    } catch (e) { console.error(e) }
    finally { setSigningOff(false) }
  }

  const revokeSignOff = async (assignmentId: number, signoffId: number) => {
    try {
      await api.delete(`/api/onboarding/signoff/${signoffId}`)
      setTeamData(prev => prev.map(eng =>
        eng.assignment_id !== assignmentId ? eng : {
          ...eng, signoffs: eng.signoffs.filter(s => s.id !== signoffId),
        }
      ))
    } catch (e) { console.error(e) }
  }

  // ── Assignment helpers ────────────────────────────────────────────────────────
  const loadUsers = async () => {
    try {
      const res = await api.get('/api/onboarding/users')
      setAvailableUsers(res.data.users || [])
    } catch (e) { console.error(e) }
  }

  const submitAssignment = async () => {
    if (!assignEngineerId) return
    setAssigning(true)
    try {
      await api.post('/api/onboarding/assignments', {
        engineer_id: assignEngineerId,
        mentor_se_id: assignMentorId || null,
      })
      const teamRes = await api.get('/api/onboarding/team-progress')
      setTeamData(teamRes.data.engineers || [])
      setShowAssignForm(false)
      setAssignEngineerId('')
      setAssignMentorId('')
    } catch (e) { console.error(e) }
    finally { setAssigning(false) }
  }

  const removeAssignment = async (assignmentId: number) => {
    try {
      await api.delete(`/api/onboarding/assignments/${assignmentId}`)
      setTeamData(prev => prev.filter(e => e.assignment_id !== assignmentId))
    } catch (e) { console.error(e) }
  }

  const phase = phases[activeTab]
  const acc   = ACCENTS[activeTab % ACCENTS.length]

  // ── TEAM VIEW RENDER ──────────────────────────────────────────────────────────
  const renderTeamView = () => (
    <div className="max-w-5xl mx-auto px-6 pt-6 pb-20">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white">My Team — Onboarding Progress</h2>
          <p className="text-sm text-slate-400 mt-1">{teamData.length} engineer{teamData.length !== 1 ? 's' : ''} assigned</p>
        </div>
        {isManager && (
          <button
            onClick={() => { setShowAssignForm(true); loadUsers() }}
            className="flex items-center gap-2 px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-semibold rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" /> Assign Engineer
          </button>
        )}
      </div>

      {/* Assignment form */}
      {showAssignForm && (
        <div className="bg-slate-800 border border-slate-600 rounded-xl p-5 mb-6">
          <h3 className="text-white font-semibold mb-4">Assign Engineer to Your Playbook</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Engineer *</label>
              <select
                value={assignEngineerId}
                onChange={e => setAssignEngineerId(Number(e.target.value) || '')}
                className="w-full bg-slate-700 text-white text-sm border border-slate-600 rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500"
              >
                <option value="">Select engineer…</option>
                {availableUsers
                  .filter(u => u.role === 'engineer' || u.role === 'employee')
                  .map(u => <option key={u.id} value={u.id}>{u.name} ({u.email})</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400 mb-1 block">Leader (optional)</label>
              <select
                value={assignMentorId}
                onChange={e => setAssignMentorId(Number(e.target.value) || '')}
                className="w-full bg-slate-700 text-white text-sm border border-slate-600 rounded-lg px-3 py-2 focus:outline-none focus:border-cyan-500"
              >
                <option value="">None</option>
                {availableUsers.filter(u => u.role === 'leader').map(u => (
                  <option key={u.id} value={u.id}>{u.name}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <button
              onClick={submitAssignment}
              disabled={!assignEngineerId || assigning}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-sm font-semibold rounded-lg transition-colors"
            >
              {assigning ? 'Assigning…' : 'Assign'}
            </button>
            <button onClick={() => setShowAssignForm(false)} className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white text-sm rounded-lg transition-colors">Cancel</button>
          </div>
        </div>
      )}

      {teamData.length === 0 ? (
        <div className="text-center py-20 text-slate-500">
          <Users className="w-12 h-12 mx-auto mb-4 opacity-30" />
          <p className="text-lg font-semibold text-slate-400">No engineers assigned yet</p>
          <p className="text-sm mt-1 opacity-60">Use "Assign Engineer" to add team members.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {teamData.map(eng => {
            const allTaskIds = phases.flatMap(p => p.rows.map(r => r.id))
            const doneCount   = allTaskIds.filter(id => eng.checked_rows[id]).length
            const totalCount  = allTaskIds.length
            const soMap       = Object.fromEntries(eng.signoffs.map(s => [s.task_id, s]))
            const evMap: Record<string, EvidenceItem[]> = {}
            for (const ev of eng.evidence) {
              if (!evMap[ev.task_id]) evMap[ev.task_id] = []
              evMap[ev.task_id].push(ev)
            }
            const isExpanded = expandedEng === eng.engineer_id

            return (
              <div key={eng.engineer_id} className="bg-slate-800/60 border border-slate-700/50 rounded-xl overflow-hidden">
                {/* Engineer header */}
                <div
                  className="flex items-center gap-4 p-4 cursor-pointer hover:bg-slate-700/40 transition-colors"
                  onClick={() => setExpandedEng(isExpanded ? null : eng.engineer_id)}
                >
                  <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center text-lg font-bold text-white">
                    {eng.engineer_name.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-white">{eng.engineer_name}</span>
                      {eng.mentor_se_name && (
                        <span className="text-xs bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded-full px-2 py-0.5">
                          Leader: {eng.mentor_se_name}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400">{eng.engineer_email}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-sm font-bold text-white">{doneCount}/{totalCount}</div>
                    <div className="text-xs text-slate-400">tasks done</div>
                  </div>
                  <div className="w-24 flex-shrink-0">
                    <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-cyan-500 rounded-full transition-all"
                        style={{ width: `${totalCount ? Math.round((doneCount / totalCount) * 100) : 0}%` }}
                      />
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5 text-right">
                      {totalCount ? Math.round((doneCount / totalCount) * 100) : 0}%
                    </div>
                  </div>
                  <ChevronDown className={`w-4 h-4 text-slate-400 flex-shrink-0 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                </div>

                {/* Expanded: phases + tasks */}
                {isExpanded && (
                  <div className="border-t border-slate-700/50 p-4 space-y-4">
                    {isManager && (
                      <div className="flex justify-end">
                        <button
                          onClick={() => removeAssignment(eng.assignment_id)}
                          className="text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10 px-3 py-1.5 rounded-lg transition-colors"
                        >
                          Remove from team
                        </button>
                      </div>
                    )}
                    {phases.map((p, pi) => {
                      const a = ACCENTS[pi % ACCENTS.length]
                      return (
                        <div key={p.id}>
                          <div className={`text-xs font-bold uppercase tracking-wider mb-2 bg-gradient-to-r ${a.gradient} bg-clip-text text-transparent`}>
                            {p.title}
                          </div>
                          <div className="space-y-1">
                            {p.rows.map(task => {
                              const isDone   = !!eng.checked_rows[task.id]
                              const signoff  = soMap[task.id]
                              const evidence = evMap[task.id] || []
                              const isSigning = signoffForm?.assignmentId === eng.assignment_id && signoffForm.taskId === task.id

                              return (
                                <div key={task.id} className={`rounded-lg border p-2.5 text-xs ${isDone ? 'border-green-500/20 bg-green-900/10' : 'border-slate-700/40 bg-slate-700/20'}`}>
                                  <div className="flex items-start gap-2">
                                    <div className={`w-4 h-4 rounded-full flex-shrink-0 mt-0.5 flex items-center justify-center ${isDone ? 'bg-green-600' : 'bg-slate-700'}`}>
                                      {isDone && <Check className="w-2.5 h-2.5 text-white" strokeWidth={3} />}
                                    </div>
                                    <div className="flex-1 min-w-0">
                                      <div className={`font-semibold ${isDone ? 'text-slate-400 line-through' : 'text-white'}`}>{task.category}</div>
                                      <div className="text-slate-500 mt-0.5">{task.deliverable || task.module}</div>

                                      {/* Evidence list */}
                                      {evidence.length > 0 && (
                                        <div className="mt-2 space-y-1">
                                          {evidence.map(ev => (
                                            <div key={ev.id} className="flex items-start gap-1.5 text-slate-400">
                                              {ev.evidence_type === 'url'    && <Link  className="w-3 h-3 flex-shrink-0 mt-0.5 text-blue-400" />}
                                              {ev.evidence_type === 'remark' && <MessageSquare className="w-3 h-3 flex-shrink-0 mt-0.5 text-amber-400" />}
                                              {ev.evidence_type === 'file'   && <Paperclip className="w-3 h-3 flex-shrink-0 mt-0.5 text-emerald-400" />}
                                              <span className="break-all">
                                                {ev.evidence_type === 'url' ? (
                                                  <a href={ev.content || '#'} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">{ev.content}</a>
                                                ) : ev.file_name || ev.content}
                                              </span>
                                            </div>
                                          ))}
                                        </div>
                                      )}
                                    </div>

                                    {/* Sign-off status + button */}
                                    <div className="flex-shrink-0 flex flex-col items-end gap-1">
                                      {signoff ? (
                                        <div className="flex items-center gap-1">
                                          <span className="bg-green-600/20 text-green-400 border border-green-500/30 rounded-full px-2 py-0.5 text-[10px] font-semibold">
                                            ✓ {signoff.signed_by_name}
                                          </span>
                                          {canSignOff && (
                                            <button
                                              onClick={() => revokeSignOff(eng.assignment_id, signoff.id)}
                                              className="text-red-400 hover:text-red-300 p-0.5 rounded"
                                              title="Revoke sign-off"
                                            >
                                              <X className="w-3 h-3" />
                                            </button>
                                          )}
                                        </div>
                                      ) : canSignOff && isDone ? (
                                        <button
                                          onClick={() => setSignoffForm({ assignmentId: eng.assignment_id, taskId: task.id, notes: '' })}
                                          className="bg-cyan-600/20 text-cyan-400 border border-cyan-500/30 rounded-full px-2 py-0.5 text-[10px] font-semibold hover:bg-cyan-600/40 transition-colors"
                                        >
                                          Sign Off
                                        </button>
                                      ) : null}
                                    </div>
                                  </div>

                                  {/* Sign-off form inline */}
                                  {isSigning && (
                                    <div className="mt-2 pt-2 border-t border-slate-700/50">
                                      <input
                                        autoFocus
                                        placeholder="Optional notes…"
                                        className="w-full bg-slate-700 text-white text-xs border border-cyan-400/50 rounded px-2 py-1 focus:outline-none mb-2"
                                        value={signoffForm.notes}
                                        onChange={e => setSignoffForm({ ...signoffForm, notes: e.target.value })}
                                        onKeyDown={e => { if (e.key === 'Escape') setSignoffForm(null) }}
                                      />
                                      <div className="flex gap-1">
                                        <button
                                          onClick={() => submitSignOff(signoffForm.assignmentId, signoffForm.taskId, signoffForm.notes)}
                                          disabled={signingOff}
                                          className="flex items-center gap-1 px-2 py-1 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white text-xs rounded-md transition-colors"
                                        >
                                          <Check className="w-3 h-3" /> Confirm Sign-Off
                                        </button>
                                        <button onClick={() => setSignoffForm(null)} className="px-2 py-1 bg-slate-700 text-white text-xs rounded-md hover:bg-slate-600 transition-colors">Cancel</button>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              )
                            })}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )

  // ── MAIN RENDER ───────────────────────────────────────────────────────────────
  return (
    <div className="h-full overflow-y-auto bg-slate-950 text-white">
      {/* Fireworks overlay */}
      {fireworks && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 cursor-pointer" onClick={() => setFireworks(false)}>
          <div className="text-center">
            <div className="text-8xl mb-6 animate-bounce">🎉</div>
            <h2 className="text-4xl font-bold text-yellow-300">All Missions Complete!</h2>
            <p className="text-white/60 mt-3 text-lg">You're fully onboarded. Welcome to the team!</p>
            <p className="text-xs text-white/30 mt-8">Click anywhere to dismiss</p>
          </div>
        </div>
      )}

      {/* Mission unlock popup */}
      {unlockPopup !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 cursor-pointer" onClick={() => setUnlockPopup(null)}>
          <div className="bg-slate-800 border border-white/10 rounded-2xl p-10 max-w-sm text-center shadow-2xl">
            <div className="text-6xl mb-4">{ACCENTS[unlockPopup % ACCENTS.length]?.icon}</div>
            <h3 className="text-2xl font-bold text-white mb-2">Mission {unlockPopup + 1} Unlocked!</h3>
            <p className="text-white/50 text-sm">{phases[unlockPopup]?.title}</p>
            <p className="text-xs text-white/30 mt-8">Click anywhere to continue</p>
          </div>
        </div>
      )}

      {/* File input (hidden) */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept=".pdf,.png,.jpg,.jpeg,.gif,.ppt,.pptx,.doc,.docx"
        onChange={e => {
          const f = e.target.files?.[0]
          if (f && uploadTaskId) uploadFile(uploadTaskId, f)
          e.target.value = ''
          setUploadTaskId(null)
        }}
      />

      {/* View mode toggle for managers / leaders */}
      {(isManager || isLeader || isAdmin) && (
        <div className="sticky top-0 z-10 bg-slate-900/95 backdrop-blur border-b border-slate-800 px-6 py-3 flex items-center gap-3">
          <button
            onClick={() => setViewMode('playbook')}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm font-semibold transition-all ${viewMode === 'playbook' ? 'bg-cyan-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
          >
            📋 {isManager ? 'My Playbook' : 'Playbook'}
          </button>
          <button
            onClick={() => setViewMode('team')}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full text-sm font-semibold transition-all ${viewMode === 'team' ? 'bg-cyan-600 text-white' : 'text-slate-400 hover:text-white hover:bg-slate-800'}`}
          >
            <Users className="w-3.5 h-3.5" /> {isLeader ? 'My Engineers' : 'My Team'} {teamData.length > 0 && <span className="ml-1 bg-white/20 rounded-full px-1.5 text-xs">{teamData.length}</span>}
          </button>
        </div>
      )}

      {/* Team view */}
      {viewMode === 'team' ? renderTeamView() : (
        <div className="max-w-5xl mx-auto px-6 pt-6 pb-20">

          {/* Not-assigned state for engineers and un-assigned leaders */}
          {(isEngineer || isLeader) && notAssigned && (
            <div className="flex flex-col items-center justify-center py-28 text-center">
              <Lock className="w-12 h-12 text-slate-600 mb-4" />
              <h2 className="text-xl font-bold text-slate-300 mb-2">
                {isLeader ? 'No Engineers Assigned Yet' : 'No Playbook Assigned Yet'}
              </h2>
              <p className="text-sm text-slate-500 max-w-sm">
                {isLeader
                  ? "You haven't been assigned to supervise any engineers yet. Contact a manager."
                  : "Your manager hasn't assigned you to an onboarding playbook yet. Check back soon or contact your manager."}
              </p>
            </div>
          )}

          {/* Assignment info banner for engineers (when assigned) */}
          {isEngineer && !notAssigned && myAssignment && (
            <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl px-4 py-3 mb-5 flex items-center gap-3 text-sm">
              <Shield className="w-4 h-4 text-cyan-400 flex-shrink-0" />
              <span className="text-slate-300">
                Playbook assigned by <span className="text-white font-semibold">{myAssignment.manager?.name || 'your manager'}</span>
                {myAssignment.mentor_se && (
                  <> · Leader: <span className="text-purple-300 font-semibold">{myAssignment.mentor_se.name}</span></>
                )}
              </span>
            </div>
          )}

          {/* Page header */}
          <div className="mb-6">
            {editPageField === 'title' ? (
              <div className="flex items-center gap-2">
                <input autoFocus className="text-3xl font-bold bg-transparent border-b-2 border-cyan-400 text-white focus:outline-none flex-1" value={editPageVal} onChange={e => setEditPageVal(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { setPageTitle(editPageVal); saveSettings(editPageVal, pageSub, tips); setEditPageField(null) } if (e.key === 'Escape') setEditPageField(null) }} />
                <button onClick={() => { setPageTitle(editPageVal); saveSettings(editPageVal, pageSub, tips); setEditPageField(null) }} className="p-1 text-green-400 hover:bg-green-500/20 rounded"><Check className="w-4 h-4" /></button>
                <button onClick={() => setEditPageField(null)} className="p-1 text-red-400 hover:bg-red-500/20 rounded"><X className="w-4 h-4" /></button>
              </div>
            ) : (
              <h1 className={`text-3xl font-bold text-white group ${isAdmin ? 'cursor-pointer hover:text-cyan-300 transition-colors' : ''}`} onClick={() => isAdmin && (setEditPageVal(pageTitle), setEditPageField('title'))}>
                {pageTitle}
                {isAdmin && <Pencil className="w-4 h-4 inline ml-2 opacity-0 group-hover:opacity-50 transition-opacity" />}
              </h1>
            )}
            {editPageField === 'sub' ? (
              <div className="flex items-center gap-2 mt-1">
                <input autoFocus className="text-sm bg-transparent border-b border-cyan-400 text-cyan-400 focus:outline-none" value={editPageVal} onChange={e => setEditPageVal(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { setPageSub(editPageVal); saveSettings(pageTitle, editPageVal, tips); setEditPageField(null) } if (e.key === 'Escape') setEditPageField(null) }} />
                <button onClick={() => { setPageSub(editPageVal); saveSettings(pageTitle, editPageVal, tips); setEditPageField(null) }} className="p-1 text-green-400 hover:bg-green-500/20 rounded"><Check className="w-3 h-3" /></button>
                <button onClick={() => setEditPageField(null)} className="p-1 text-red-400 hover:bg-red-500/20 rounded"><X className="w-3 h-3" /></button>
              </div>
            ) : (
              <p className={`text-sm text-cyan-400 font-medium mt-1 group ${isAdmin ? 'cursor-pointer hover:text-cyan-300' : ''}`} onClick={() => isAdmin && (setEditPageVal(pageSub), setEditPageField('sub'))}>
                {pageSub}
                {isAdmin && <Pencil className="w-3 h-3 inline ml-1 opacity-0 group-hover:opacity-50 transition-opacity" />}
              </p>
            )}
          </div>

          {/* Mission tab bar (hidden for unassigned engineers/leaders) */}
          {!((isEngineer || isLeader) && notAssigned) && <div className="flex gap-2 mb-6 overflow-x-auto pb-1 scrollbar-none">
            {phases.map((p, i) => {
              const a = ACCENTS[i % ACCENTS.length]
              const locked = isLocked(i)
              const done = p.rows.filter(r => checked[r.id]).length
              const total = p.rows.length
              return (
                <button key={p.id} onClick={() => !locked && setActiveTab(i)} className={`flex-shrink-0 flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold transition-all whitespace-nowrap ${activeTab === i ? `${a.pill} text-white shadow-lg` : locked ? 'bg-slate-800/40 text-slate-600 cursor-not-allowed' : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'}`}>
                  {p.title}
                  {locked && <Lock className="w-3 h-3 flex-shrink-0" />}
                  {!locked && done === total && total > 0 && <Trophy className="w-3 h-3 text-yellow-300 flex-shrink-0" />}
                  {!locked && done > 0 && done < total && <span className="text-[10px] opacity-60">{done}/{total}</span>}
                </button>
              )
            })}
          </div>}

          {/* Tip cards, hint bar and active phase — hidden for unassigned engineers/leaders */}
          {!((isEngineer || isLeader) && notAssigned) && <>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
            {tips.map((tip, i) => (
              <div key={i} className="relative group/tip bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 flex items-start gap-3">
                <Lightbulb className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                {isAdmin && editTipIdx === i ? (
                  <div className="flex-1">
                    <textarea autoFocus rows={3} className="w-full bg-slate-800 text-white text-sm border border-amber-400/40 rounded px-2 py-1 focus:outline-none resize-none" value={editTipVal} onChange={e => setEditTipVal(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); const upd = tips.map((t, j) => j === i ? editTipVal : t); setTips(upd); saveSettings(pageTitle, pageSub, upd); setEditTipIdx(null) } if (e.key === 'Escape') setEditTipIdx(null) }} />
                    <div className="flex gap-1 mt-1">
                      <button onClick={() => { const upd = tips.map((t, j) => j === i ? editTipVal : t); setTips(upd); saveSettings(pageTitle, pageSub, upd); setEditTipIdx(null) }} className="p-0.5 text-green-400 hover:bg-green-500/20 rounded"><Check className="w-3 h-3" /></button>
                      <button onClick={() => setEditTipIdx(null)} className="p-0.5 text-red-400 hover:bg-red-500/20 rounded"><X className="w-3 h-3" /></button>
                    </div>
                  </div>
                ) : (
                  <p className={`text-sm text-amber-200/80 leading-relaxed ${isAdmin ? 'cursor-pointer hover:text-amber-100' : ''}`} onClick={() => isAdmin && (setEditTipVal(tip), setEditTipIdx(i))}>{tip}</p>
                )}
                {isAdmin && editTipIdx !== i && (
                  <button onClick={() => { const upd = tips.filter((_, j) => j !== i); setTips(upd); saveSettings(pageTitle, pageSub, upd) }} className="absolute top-2 right-2 opacity-0 group-hover/tip:opacity-100 p-1 text-red-400 hover:bg-red-500/20 rounded transition-opacity"><X className="w-3 h-3" /></button>
                )}
              </div>
            ))}
            {isAdmin && (
              <button onClick={() => { const upd = [...tips, 'New tip — click to edit.']; setTips(upd); saveSettings(pageTitle, pageSub, upd) }} className="border border-dashed border-slate-700 rounded-xl p-4 flex items-center justify-center gap-2 text-slate-500 hover:text-white hover:border-slate-500 transition-all text-sm">
                <Plus className="w-4 h-4" /> Add tip
              </button>
            )}
          </div>

          {/* Admin/Manager hint bar */}
          {canEditPhases && (
            <div className="bg-slate-800/40 border border-slate-700/30 rounded-lg px-4 py-2 mb-6 text-xs text-slate-400">
              {isAdmin ? 'Admin mode' : 'Manager mode'} — click any card title or description to edit inline.{' '}
              Use <span className="text-green-400 font-bold">+</span> to add or <span className="text-red-400 font-bold">×</span> to remove tasks.
              {isManager && <span className="text-cyan-400 ml-2">Changes apply to your personal playbook and all assigned engineers.</span>}
            </div>
          )}

          {/* Active phase */}
          {phase && (() => {
            const locked = isLocked(activeTab)
            const total  = phase.rows.length
            const done   = phase.rows.filter(r => checked[r.id]).length
            const pct    = total === 0 ? 0 : Math.round((done / total) * 100)

            if (locked) return (
              <div className="flex flex-col items-center py-24 text-slate-500">
                <Lock className="w-12 h-12 mb-4 opacity-30" />
                <p className="text-lg font-semibold text-slate-400">Complete Mission {activeTab} First</p>
                <p className="text-sm mt-1 opacity-60">Finish all tasks in the previous phase to unlock this one.</p>
              </div>
            )

            return (
              <>
                {/* Mission header card */}
                <div className={`bg-gradient-to-r ${acc.gradient} rounded-xl p-6 mb-10 flex items-center gap-5`}>
                  <div className="w-14 h-14 rounded-full bg-black/25 flex items-center justify-center text-3xl flex-shrink-0 border border-white/20">{acc.icon}</div>
                  <div className="flex-1 min-w-0">
                    {canEditPhases && editPhase?.pId === phase.id && editPhase.field === 'title' ? (
                      <div className="flex items-center gap-2 mb-1">
                        <input autoFocus className="bg-white/20 text-white text-xl font-bold border border-white/40 rounded px-2 py-0.5 focus:outline-none flex-1" value={editPhaseVal} onChange={e => setEditPhaseVal(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') commitPhaseEdit(); if (e.key === 'Escape') setEditPhase(null) }} />
                        <button onClick={commitPhaseEdit} className="p-1 text-white/80 hover:bg-white/20 rounded"><Check className="w-4 h-4" /></button>
                        <button onClick={() => setEditPhase(null)} className="p-1 text-white/50 hover:bg-white/20 rounded"><X className="w-4 h-4" /></button>
                      </div>
                    ) : (
                      <h2 className={`text-xl font-bold text-white mb-1 group/pt ${canEditPhases ? 'cursor-pointer hover:text-white/80' : ''}`} onClick={() => canEditPhases && (setEditPhaseVal(phase.title), setEditPhase({ pId: phase.id, field: 'title' }))}>
                        {phase.title}
                        {canEditPhases && <Pencil className="w-3 h-3 inline ml-1.5 opacity-0 group-hover/pt:opacity-60" />}
                      </h2>
                    )}
                    {canEditPhases && editPhase?.pId === phase.id && editPhase.field === 'objective' ? (
                      <div className="flex items-center gap-2">
                        <input autoFocus className="bg-white/20 text-white/80 text-sm border border-white/40 rounded px-2 py-0.5 focus:outline-none flex-1" value={editPhaseVal} onChange={e => setEditPhaseVal(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') commitPhaseEdit(); if (e.key === 'Escape') setEditPhase(null) }} />
                        <button onClick={commitPhaseEdit} className="p-1 text-white/80 hover:bg-white/20 rounded"><Check className="w-3 h-3" /></button>
                        <button onClick={() => setEditPhase(null)} className="p-1 text-white/50 hover:bg-white/20 rounded"><X className="w-3 h-3" /></button>
                      </div>
                    ) : (
                      <p className={`text-white/70 text-sm group/po ${canEditPhases ? 'cursor-pointer hover:text-white/90' : ''}`} onClick={() => canEditPhases && (setEditPhaseVal(phase.objective), setEditPhase({ pId: phase.id, field: 'objective' }))}>
                        {phase.objective}
                        {canEditPhases && <Pencil className="w-3 h-3 inline ml-1 opacity-0 group-hover/po:opacity-60" />}
                      </p>
                    )}
                    <div className="mt-3">
                      <div className="flex justify-between text-xs text-white/60 mb-1.5">
                        <span>{done}/{total} complete</span>
                        <span className="font-bold text-white/80">{pct}%</span>
                      </div>
                      <div className="h-1.5 bg-white/20 rounded-full overflow-hidden">
                        <div className="h-full bg-white/80 rounded-full transition-all duration-700 ease-out" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Timeline */}
                <div className="relative">
                  <div className="hidden sm:block absolute left-1/2 top-4 bottom-4 -translate-x-1/2 w-px border-l-2 border-dashed border-slate-700/60" />
                  <div className="space-y-6">
                    {phase.rows.map((task, idx) => {
                      const isRight        = idx % 2 === 0
                      const isDone         = !!checked[task.id]
                      const isEditingTitle = editTask?.pId === phase.id && editTask.tId === task.id && editTask.field === 'category'
                      const isEditingDesc  = editTask?.pId === phase.id && editTask.tId === task.id && editTask.field === 'module'
                      const evItems        = myEvidence[task.id] || []
                      const signoff        = mySignoffs[task.id]
                      const evOpen         = expandedEv.has(task.id)

                      const card = (
                        <div className={`bg-slate-800/70 border rounded-xl p-4 transition-all duration-300 ${isDone ? 'border-green-500/30 bg-green-900/10' : 'border-slate-700/50 hover:border-slate-600/70'}`}>
                          {/* Title */}
                          {isEditingTitle ? (
                            <div className="flex items-center gap-1 mb-2">
                              <input autoFocus className="flex-1 bg-slate-700 text-white font-semibold text-sm border border-cyan-400/50 rounded px-2 py-1 focus:outline-none" value={editVal} onChange={e => setEditVal(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') commitTaskEdit(); if (e.key === 'Escape') setEditTask(null) }} />
                              <button onClick={commitTaskEdit} className="p-0.5 text-green-400 hover:bg-green-500/20 rounded"><Check className="w-3.5 h-3.5" /></button>
                              <button onClick={() => setEditTask(null)} className="p-0.5 text-red-400 hover:bg-red-500/20 rounded"><X className="w-3.5 h-3.5" /></button>
                            </div>
                          ) : (
                            <h3 className={`font-semibold text-sm mb-1 leading-snug ${isDone ? 'text-slate-400 line-through' : 'text-white'} ${canEditPhases ? 'cursor-pointer hover:text-cyan-300 transition-colors' : ''}`} onClick={() => canEditPhases && startTaskEdit(phase.id, task.id, 'category', task.category)}>
                              {task.category}
                              {canEditPhases && <Pencil className="w-3 h-3 inline ml-1 opacity-0 group-hover:opacity-50" />}
                            </h3>
                          )}

                          {/* Deliverable badge removed — shown inside Learn More */}

                          {/* Description */}
                          {isEditingDesc ? (
                            <div className="mb-3">
                              <textarea autoFocus rows={2} className="w-full bg-slate-700 text-slate-300 text-xs border border-cyan-400/50 rounded px-2 py-1 focus:outline-none resize-none" value={editVal} onChange={e => setEditVal(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); commitTaskEdit() } if (e.key === 'Escape') setEditTask(null) }} />
                              <div className="flex gap-1 mt-0.5">
                                <button onClick={commitTaskEdit} className="p-0.5 text-green-400 hover:bg-green-500/20 rounded"><Check className="w-3 h-3" /></button>
                                <button onClick={() => setEditTask(null)} className="p-0.5 text-red-400 hover:bg-red-500/20 rounded"><X className="w-3 h-3" /></button>
                              </div>
                            </div>
                          ) : (
                            <p className={`text-xs leading-relaxed mb-3 ${isDone ? 'text-slate-500' : 'text-slate-400'} ${canEditPhases ? 'cursor-pointer hover:text-slate-200 transition-colors' : ''}`} onClick={() => canEditPhases && startTaskEdit(phase.id, task.id, 'module', task.module)}>
                              {task.module}
                            </p>
                          )}

                          {/* Sign-off status (engineer view) */}
                          {isEngineer && signoff && (
                            <div className="flex items-center gap-1.5 mb-2 text-[10px] bg-green-600/10 border border-green-500/20 rounded-lg px-2 py-1">
                              <Check className="w-3 h-3 text-green-400" />
                              <span className="text-green-300 font-semibold">Signed off by {signoff.signed_by_name}</span>
                              <span className="text-slate-500 ml-auto">{fmtDate(signoff.signed_at)}</span>
                            </div>
                          )}

                          {/* Action row */}
                          <div className="flex items-center gap-2 flex-wrap">
                            {/* Learn More */}
                            {(() => {
                              const lmItems  = task.learnMore || []
                              const hasContent = lmItems.length > 0 || !!task.url || !!task.deliverable
                              const isOpen   = expandedLM.has(task.id)
                              if (!hasContent && !canEditPhases) return (
                                <span className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700/50 text-slate-500 text-xs font-semibold rounded-lg cursor-default border border-slate-700">Learn More</span>
                              )
                              return (
                                <button onClick={() => toggleLM(task.id)} className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors border ${isOpen ? 'bg-blue-600 text-white border-blue-500' : hasContent ? 'bg-blue-600/20 text-blue-300 border-blue-500/40 hover:bg-blue-600/40' : 'bg-blue-600/10 text-blue-400/60 border-dashed border-blue-500/30 hover:bg-blue-600/20 hover:text-blue-300'}`}>
                                  Learn More <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
                                </button>
                              )
                            })()}

                            <button onClick={() => toggle(task.id)} className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all border ${isDone ? 'bg-green-600/25 text-green-400 border-green-500/40 hover:bg-green-600/35' : 'bg-slate-700 text-slate-300 border-slate-600 hover:bg-slate-600 hover:text-white'}`}>
                              {isDone ? <><Check className="w-3 h-3" /> Completed</> : <>Mark Complete</>}
                            </button>

                            {/* Evidence button (engineers only, when assigned) */}
                            {isEngineer && myAssignment && (
                              <button
                                onClick={() => toggleEv(task.id)}
                                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors border ${evOpen ? 'bg-amber-600 text-white border-amber-500' : evItems.length > 0 ? 'bg-amber-600/20 text-amber-300 border-amber-500/40 hover:bg-amber-600/40' : 'bg-slate-700/50 text-slate-400 border-slate-600/50 hover:text-amber-300 hover:border-amber-500/40'}`}
                              >
                                <Paperclip className="w-3 h-3" />
                                Evidence {evItems.length > 0 && <span className="bg-white/20 rounded-full px-1 text-[10px]">{evItems.length}</span>}
                                <ChevronDown className={`w-3 h-3 transition-transform ${evOpen ? 'rotate-180' : ''}`} />
                              </button>
                            )}

                            {canEditPhases && (
                              <>
                                <button onClick={() => addTask(phase.id, idx)} className="p-1.5 text-slate-500 hover:text-green-400 hover:bg-green-500/10 rounded-lg transition-colors" title="Add task after this one"><Plus className="w-3.5 h-3.5" /></button>
                                <button onClick={() => deleteTask(phase.id, task.id)} className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors" title="Delete task"><X className="w-3.5 h-3.5" /></button>
                              </>
                            )}
                          </div>

                          {/* Evidence panel */}
                          {evOpen && isEngineer && myAssignment && (
                            <div className="mt-3 pt-3 border-t border-slate-700/50">
                              <p className="text-[10px] text-slate-500 uppercase tracking-wider mb-2 font-semibold">Evidence & Notes</p>

                              {/* Existing evidence */}
                              {evItems.length > 0 && (
                                <ul className="space-y-1.5 mb-3">
                                  {evItems.map(ev => (
                                    <li key={ev.id} className="flex items-start gap-2 group/evi">
                                      {ev.evidence_type === 'url'    && <Link className="w-3 h-3 text-blue-400 flex-shrink-0 mt-0.5" />}
                                      {ev.evidence_type === 'remark' && <MessageSquare className="w-3 h-3 text-amber-400 flex-shrink-0 mt-0.5" />}
                                      {ev.evidence_type === 'file'   && <Paperclip className="w-3 h-3 text-emerald-400 flex-shrink-0 mt-0.5" />}
                                      <span className="text-xs text-slate-300 break-all flex-1">
                                        {ev.evidence_type === 'url' ? (
                                          <a href={ev.content || '#'} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">{ev.content}</a>
                                        ) : ev.file_name || ev.content}
                                      </span>
                                      <button onClick={() => deleteEvidence(ev)} className="opacity-0 group-hover/evi:opacity-100 p-0.5 text-red-400 hover:bg-red-500/10 rounded transition-opacity flex-shrink-0"><X className="w-3 h-3" /></button>
                                    </li>
                                  ))}
                                </ul>
                              )}

                              {/* New evidence form */}
                              {evForm?.taskId === task.id ? (
                                <div className="bg-slate-700/50 rounded-lg p-2 mb-2">
                                  {evForm.type === 'remark' ? (
                                    <textarea autoFocus rows={2} placeholder="Add your notes here…" className="w-full bg-slate-700 text-white text-xs border border-amber-400/50 rounded px-2 py-1 focus:outline-none resize-none" value={evForm.value} onChange={e => setEvForm({ ...evForm, value: e.target.value })} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submitEvidence() } if (e.key === 'Escape') setEvForm(null) }} />
                                  ) : (
                                    <input autoFocus type="url" placeholder="https://…" className="w-full bg-slate-700 text-white text-xs border border-blue-400/50 rounded px-2 py-1 focus:outline-none" value={evForm.value} onChange={e => setEvForm({ ...evForm, value: e.target.value })} onKeyDown={e => { if (e.key === 'Enter') submitEvidence(); if (e.key === 'Escape') setEvForm(null) }} />
                                  )}
                                  <div className="flex gap-1 mt-1.5">
                                    <button onClick={submitEvidence} disabled={evSubmitting} className="flex items-center gap-1 px-2 py-1 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white text-xs rounded-md"><Check className="w-3 h-3" /> Save</button>
                                    <button onClick={() => setEvForm(null)} className="px-2 py-1 bg-slate-600 text-white text-xs rounded-md hover:bg-slate-500">Cancel</button>
                                  </div>
                                </div>
                              ) : (
                                <div className="flex gap-1.5 flex-wrap">
                                  <button onClick={() => setEvForm({ taskId: task.id, type: 'remark', value: '' })} className="flex items-center gap-1 px-2 py-1 text-xs text-slate-400 hover:text-amber-300 border border-dashed border-slate-600 hover:border-amber-500/50 rounded-lg transition-colors">
                                    <MessageSquare className="w-3 h-3" /> Add Note
                                  </button>
                                  <button onClick={() => setEvForm({ taskId: task.id, type: 'url', value: '' })} className="flex items-center gap-1 px-2 py-1 text-xs text-slate-400 hover:text-blue-300 border border-dashed border-slate-600 hover:border-blue-500/50 rounded-lg transition-colors">
                                    <Link className="w-3 h-3" /> Add URL
                                  </button>
                                  <button onClick={() => { setUploadTaskId(task.id); fileInputRef.current?.click() }} className="flex items-center gap-1 px-2 py-1 text-xs text-slate-400 hover:text-emerald-300 border border-dashed border-slate-600 hover:border-emerald-500/50 rounded-lg transition-colors">
                                    <Paperclip className="w-3 h-3" /> Upload File
                                  </button>
                                </div>
                              )}
                            </div>
                          )}

                          {/* Learn More expandable */}
                          {expandedLM.has(task.id) && (
                            <div className="mt-3 pt-3 border-t border-slate-700/50">
                              {/* Deliverable resources — rendered from markdown */}
                              {(task.deliverable || canEditPhases) && (
                                <div className="mb-3">
                                  <div className="flex items-center gap-1.5 mb-1.5">
                                    <p className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold flex items-center gap-1">
                                      <FileText className="w-3 h-3" /> Resources / Deliverables
                                    </p>
                                    {canEditPhases && !(
                                      editTask?.pId === phase.id && editTask.tId === task.id && editTask.field === 'deliverable'
                                    ) && (
                                      <div className="flex gap-0.5 ml-auto">
                                        <button
                                          onClick={() => startTaskEdit(phase.id, task.id, 'deliverable', task.deliverable || '')}
                                          className="p-0.5 text-slate-500 hover:text-cyan-400 hover:bg-cyan-500/10 rounded"
                                          title="Edit deliverable"
                                        ><Pencil className="w-3 h-3" /></button>
                                        {task.deliverable && (
                                          <button
                                            onClick={() => {
                                              const upd = phases.map(p =>
                                                p.id !== phase.id ? p : {
                                                  ...p,
                                                  rows: p.rows.map(r => r.id !== task.id ? r : { ...r, deliverable: '' }),
                                                }
                                              )
                                              setPhases(upd); savePhases(upd)
                                            }}
                                            className="p-0.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded"
                                            title="Clear deliverable"
                                          ><X className="w-3 h-3" /></button>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                  {editTask?.pId === phase.id && editTask.tId === task.id && editTask.field === 'deliverable' ? (
                                    <div className="mb-1">
                                      <textarea
                                        autoFocus
                                        rows={3}
                                        className="w-full bg-slate-700 text-slate-300 text-xs border border-cyan-400/50 rounded px-2 py-1 focus:outline-none resize-none"
                                        value={editVal}
                                        onChange={e => setEditVal(e.target.value)}
                                        onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); commitTaskEdit() } if (e.key === 'Escape') setEditTask(null) }}
                                      />
                                      <div className="flex gap-1 mt-0.5">
                                        <button onClick={commitTaskEdit} className="p-0.5 text-green-400 hover:bg-green-500/20 rounded"><Check className="w-3 h-3" /></button>
                                        <button onClick={() => setEditTask(null)} className="p-0.5 text-red-400 hover:bg-red-500/20 rounded"><X className="w-3 h-3" /></button>
                                      </div>
                                    </div>
                                  ) : task.deliverable ? (
                                    renderDeliverable(task.deliverable)
                                  ) : canEditPhases ? (
                                    <p className="text-xs text-slate-600 italic">No deliverable set — click pencil to add.</p>
                                  ) : null}
                                </div>
                              )}
                              <ul className="space-y-2 mb-2">
                                {(!task.learnMore || task.learnMore.length === 0) && task.url && (
                                  <li className="flex items-start gap-2">
                                    <a href={task.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors">
                                      <ExternalLink className="w-3 h-3 flex-shrink-0 mt-0.5" />
                                      <span className="break-words">{task.url}</span>
                                    </a>
                                  </li>
                                )}
                                {(task.learnMore || []).map(item => {
                                  const isEditingItem = lmEdit?.taskId === task.id && lmEdit.itemId === item.id
                                  if (isEditingItem) return (
                                    <li key={item.id} className="bg-slate-700/50 rounded-lg p-2">
                                      <div className="flex flex-col gap-1.5">
                                        <input autoFocus placeholder="Label / Text" className="w-full bg-slate-700 text-white text-xs border border-cyan-400/50 rounded px-2 py-1 focus:outline-none" value={lmEdit.label} onChange={e => setLmEdit({ ...lmEdit, label: e.target.value })} onKeyDown={e => { if (e.key === 'Escape') setLmEdit(null) }} />
                                        {lmEdit.type === 'link' && <input placeholder="https://..." className="w-full bg-slate-700 text-slate-300 text-xs border border-cyan-400/50 rounded px-2 py-1 focus:outline-none" value={lmEdit.url} onChange={e => setLmEdit({ ...lmEdit, url: e.target.value })} onKeyDown={e => { if (e.key === 'Enter') commitLMEdit(phase.id); if (e.key === 'Escape') setLmEdit(null) }} />}
                                        <div className="flex gap-1">
                                          <button onClick={() => commitLMEdit(phase.id)} className="p-0.5 text-green-400 hover:bg-green-500/20 rounded"><Check className="w-3 h-3" /></button>
                                          <button onClick={() => setLmEdit(null)} className="p-0.5 text-red-400 hover:bg-red-500/20 rounded"><X className="w-3 h-3" /></button>
                                        </div>
                                      </div>
                                    </li>
                                  )
                                  return (
                                    <li key={item.id} className="flex items-start gap-2 group/lmi">
                                      {item.type === 'link' && item.url ? (
                                        <a href={item.url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors flex-1 min-w-0">
                                          <ExternalLink className="w-3 h-3 flex-shrink-0 mt-0.5" />
                                          <span className="break-words">{item.label || item.url}</span>
                                        </a>
                                      ) : (
                                        <span className="flex items-start gap-1.5 text-xs text-slate-300 flex-1 min-w-0">
                                          <span className="text-slate-500 flex-shrink-0 mt-0.5">•</span>
                                          <span className="break-words">{item.label}</span>
                                        </span>
                                      )}
                                      {canEditPhases && (
                                        <div className="flex gap-0.5 opacity-0 group-hover/lmi:opacity-100 transition-opacity flex-shrink-0">
                                          <button onClick={() => setLmEdit({ pId: phase.id, taskId: task.id, itemId: item.id, type: item.type, label: item.label, url: item.url || '' })} className="p-0.5 text-slate-400 hover:text-cyan-400 hover:bg-cyan-500/10 rounded"><Pencil className="w-3 h-3" /></button>
                                          <button onClick={() => saveLMItems(phase.id, task.id, (task.learnMore || []).filter(i => i.id !== item.id))} className="p-0.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded"><X className="w-3 h-3" /></button>
                                        </div>
                                      )}
                                    </li>
                                  )
                                })}
                              </ul>
                              {canEditPhases && lmEdit?.taskId === task.id && lmEdit.itemId === null && (
                                <div className="bg-slate-700/50 rounded-lg p-2 mb-2">
                                  <div className="flex flex-col gap-1.5">
                                    <input autoFocus placeholder={lmEdit.type === 'link' ? 'Link label...' : 'Instruction text...'} className="w-full bg-slate-700 text-white text-xs border border-cyan-400/50 rounded px-2 py-1 focus:outline-none" value={lmEdit.label} onChange={e => setLmEdit({ ...lmEdit, label: e.target.value })} onKeyDown={e => { if (e.key === 'Escape') setLmEdit(null) }} />
                                    {lmEdit.type === 'link' && <input placeholder="https://..." className="w-full bg-slate-700 text-slate-300 text-xs border border-cyan-400/50 rounded px-2 py-1 focus:outline-none" value={lmEdit.url} onChange={e => setLmEdit({ ...lmEdit, url: e.target.value })} onKeyDown={e => { if (e.key === 'Enter') commitLMEdit(phase.id); if (e.key === 'Escape') setLmEdit(null) }} />}
                                    <div className="flex gap-1">
                                      <button onClick={() => commitLMEdit(phase.id)} className="p-0.5 text-green-400 hover:bg-green-500/20 rounded"><Check className="w-3 h-3" /></button>
                                      <button onClick={() => setLmEdit(null)} className="p-0.5 text-red-400 hover:bg-red-500/20 rounded"><X className="w-3 h-3" /></button>
                                    </div>
                                  </div>
                                </div>
                              )}
                              {canEditPhases && !(lmEdit?.taskId === task.id) && (
                                <div className="flex gap-1.5">
                                  <button onClick={() => setLmEdit({ pId: phase.id, taskId: task.id, itemId: null, type: 'text', label: '', url: '' })} className="flex items-center gap-1 px-2 py-1 text-xs text-slate-400 hover:text-white border border-dashed border-slate-600 hover:border-slate-400 rounded-lg transition-colors"><Plus className="w-3 h-3" /> Add Text</button>
                                  <button onClick={() => setLmEdit({ pId: phase.id, taskId: task.id, itemId: null, type: 'link', label: '', url: '' })} className="flex items-center gap-1 px-2 py-1 text-xs text-slate-400 hover:text-white border border-dashed border-slate-600 hover:border-slate-400 rounded-lg transition-colors"><ExternalLink className="w-3 h-3" /> Add Link</button>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )

                      return (
                        <div key={task.id} className="relative flex items-start sm:items-center">
                          <div className="hidden sm:block sm:w-[calc(50%-24px)] sm:pr-5">{!isRight && card}</div>
                          <div className="hidden sm:flex w-12 justify-center flex-shrink-0 z-10">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all duration-300 cursor-pointer ${isDone ? `${acc.dot} border-transparent text-white shadow-lg ${acc.dotGlow}` : 'bg-slate-900 border-slate-600 text-slate-400 hover:border-slate-400'}`} onClick={() => toggle(task.id)} title={isDone ? 'Mark incomplete' : 'Mark complete'}>
                              {isDone ? <Check className="w-4 h-4" strokeWidth={3} /> : idx + 1}
                            </div>
                          </div>
                          <div className="hidden sm:block sm:w-[calc(50%-24px)] sm:pl-5">{isRight && card}</div>
                          <div className="flex sm:hidden w-full gap-3">
                            <div className={`w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold border-2 transition-all mt-1 cursor-pointer ${isDone ? `${acc.dot} border-transparent text-white` : 'bg-slate-900 border-slate-600 text-slate-400'}`} onClick={() => toggle(task.id)}>
                              {isDone ? <Check className="w-3 h-3" strokeWidth={3} /> : idx + 1}
                            </div>
                            <div className="flex-1">{card}</div>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {/* Add task button */}
                {canEditPhases && (
                  <div className="flex justify-center mt-10">
                    <button onClick={() => addTask(phase.id)} className="flex items-center gap-2 px-5 py-2.5 border border-dashed border-slate-700 rounded-xl text-sm text-slate-500 hover:text-white hover:border-slate-500 transition-all">
                      <Plus className="w-4 h-4" /> Add task to {phase.title}
                    </button>
                  </div>
                )}
              </>
            )
          })()}
          </>}
        </div>
      )}
    </div>
  )
}
