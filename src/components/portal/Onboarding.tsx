'use client'

import React, { useState, useEffect, useMemo, useRef } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { api } from '@/lib/api'
import { Plus, Trash2, Pencil, Check, X, Trophy, ChevronDown, ChevronUp, ArrowUp, ArrowDown, Lock } from 'lucide-react'

interface TableRow {
  id: string
  category: string
  module: string
  duration: string
  deliverable: string
  signOff: string
}

interface Phase {
  id: string
  title: string
  objective: string
  rows: TableRow[]
}

const initialPhases: Phase[] = [
  {
    id: 'phase1',
    title: 'Phase 1: 0–30 Days',
    objective: 'Technical Independence + Platform Narrative',
    rows: [
      { id: 'p1r1', category: 'Environment & Tools', module: 'Lab + demo environment fully operational', duration: '3–5 days', deliverable: 'Live demo run-through without assistance', signOff: 'Mentor SE' },
      { id: 'p1r2', category: 'Platform Narrative', module: '5–7 min platform story (security outcomes + architecture)', duration: '1 week (parallel)', deliverable: 'Recorded narrative delivery', signOff: 'Manager' },
      { id: 'p1r3', category: 'Domain Selection', module: 'Choose primary domain (FW / ZTA / SSE / etc.)', duration: 'Week 1', deliverable: 'Domain declaration + learning plan', signOff: 'Manager' },
      { id: 'p1r4', category: 'Hands-on Repetition', module: 'Daily lab reps tied to 2–3 top use cases', duration: 'Ongoing (15–30 min daily)', deliverable: 'Reproducible demo baseline', signOff: 'Mentor SE' },
      { id: 'p1r5', category: 'Sales Motion Basics', module: 'Shadow 2–3 calls (discovery + technical)', duration: '2 weeks', deliverable: 'Written observation summary', signOff: 'Manager' },
    ],
  },
  {
    id: 'phase2',
    title: 'Phase 2: 31–60 Days',
    objective: 'Controlled Customer Engagement',
    rows: [
      { id: 'p2r1', category: 'Demo Craft', module: 'Build Minimum Viable Demo (MVD)', duration: '1–2 weeks', deliverable: 'Structured demo flow (Intro → Use Case → Differentiation → Close)', signOff: 'Domain Lead' },
      { id: 'p2r2', category: 'Discovery Skills', module: 'Co-lead 1 discovery call', duration: 'Within 30 days', deliverable: 'Discovery notes + pain mapping', signOff: 'Manager' },
      { id: 'p2r3', category: 'Competitive Readiness', module: 'Top 2 competitors + 10 objection responses', duration: '1 week', deliverable: 'Competitive positioning sheet', signOff: 'Domain Lead' },
      { id: 'p2r4', category: 'Scoping & Licensing', module: 'Basic sizing + licensing fundamentals', duration: '1 week', deliverable: 'Sample sizing + BOM scenario', signOff: 'Senior SE' },
      { id: 'p2r5', category: 'Enterprise Exposure', module: 'Participate in 1 RFP / questionnaire', duration: 'Within 60 days', deliverable: 'Edited submission section', signOff: 'Manager' },
    ],
  },
  {
    id: 'phase3',
    title: 'Phase 3: 61–90 Days',
    objective: 'Partial Ownership',
    rows: [
      { id: 'p3r1', category: 'Discovery Leadership', module: 'Lead 1 discovery session', duration: 'Within 30 days', deliverable: 'Customer pain summary + next-step doc', signOff: 'Manager' },
      { id: 'p3r2', category: 'POV Mechanics', module: 'Write a POV plan (success criteria, scope, risks)', duration: '1 week', deliverable: 'POV document draft', signOff: 'Senior SE' },
      { id: 'p3r3', category: 'Technical Escalation Literacy', module: 'Observe 1 real escalation / TAC path', duration: 'Ongoing', deliverable: 'Lessons learned summary', signOff: 'Mentor' },
      { id: 'p3r4', category: 'Demo Scaling', module: 'Deliver demo to real customer (controlled)', duration: '1–2 opportunities', deliverable: 'Customer feedback', signOff: 'Manager' },
      { id: 'p3r5', category: 'Domain Certification', module: 'Internal domain assessment (formal or informal exam)', duration: 'By Day 90', deliverable: 'Pass result', signOff: 'Domain Lead' },
    ],
  },
  {
    id: 'phase4',
    title: 'Phase 4: 91–120 Days',
    objective: 'Field Ownership & Enterprise Competency',
    rows: [
      { id: 'p4r1', category: 'POV Ownership', module: 'Lead controlled POV', duration: '2–4 weeks', deliverable: 'POV execution + success report', signOff: 'Manager' },
      { id: 'p4r2', category: 'Commercial Integration', module: 'Lead sizing + licensing discussion', duration: '1 deal cycle', deliverable: 'Approved BOM + pricing alignment', signOff: 'Account Team' },
      { id: 'p4r3', category: 'Executive Positioning', module: 'Deliver executive-level summary (10 min)', duration: '1 opportunity', deliverable: 'Exec recap slide', signOff: 'Manager' },
      { id: 'p4r4', category: 'Complex Objection Handling', module: 'Handle competitive pushback live', duration: 'As encountered', deliverable: 'Manager feedback', signOff: 'Manager' },
      { id: 'p4r5', category: 'Knowledge Contribution', module: 'Contribute artifact (demo doc / battlecard / RFP response template)', duration: 'By Day 120', deliverable: 'Reusable asset', signOff: 'Domain Lead' },
    ],
  },
]

const COLUMNS: { key: keyof Omit<TableRow, 'id'>; label: string }[] = [
  { key: 'category', label: 'Category' },
  { key: 'module', label: 'Module' },
  { key: 'duration', label: 'Duration' },
  { key: 'deliverable', label: 'Deliverable' },
  { key: 'signOff', label: 'Sign-Off' },
]

function generateId() {
  return Math.random().toString(36).slice(2, 10)
}

const LADDER_STAGES = [
  { emoji: '🥷', label: 'Ninja',   sub: 'Phase 1 · 0–30 Days',    color: 'from-cyan-400 to-blue-500',     border: 'border-cyan-400',    glow: 'shadow-cyan-500/70',    text: 'text-cyan-400',    bg: 'bg-cyan-500/10' },
  { emoji: '⚔️', label: 'Samurai', sub: 'Phase 2 · 31–60 Days',   color: 'from-blue-400 to-indigo-500',   border: 'border-blue-400',    glow: 'shadow-blue-500/70',    text: 'text-blue-400',    bg: 'bg-blue-500/10' },
  { emoji: '🛡️', label: 'Daimyo',  sub: 'Phase 3 · 61–90 Days',   color: 'from-indigo-400 to-purple-500', border: 'border-indigo-400',  glow: 'shadow-indigo-500/70',  text: 'text-indigo-400',  bg: 'bg-indigo-500/10' },
  { emoji: '🎓', label: 'Sensei',  sub: 'Phase 4 · 91–120 Days',  color: 'from-purple-400 to-pink-500',   border: 'border-purple-400',  glow: 'shadow-purple-500/70',  text: 'text-purple-400',  bg: 'bg-purple-500/10' },
]

const FIREWORK_COLORS = ['#22d3ee','#60a5fa','#a78bfa','#f472b6','#34d399','#fbbf24','#fb923c','#ffffff']

const MISSION_POPUPS: Record<number, { title: string; intro: string; items: string[]; ready: string }> = {
  1: {
    title: '🎉 Mission 1 Completed',
    intro: 'Good job! You are now able to:',
    items: [
      'Understand the SE role and core responsibilities',
      'Navigate essential tools and processes',
      'Communicate foundational messaging',
      'Operate with basic technical and sales awareness',
    ],
    ready: 'You are ready to begin participating in customer engagements.',
  },
  2: {
    title: '🎉 Mission 2 Completed',
    intro: 'Great progress! You are now able to:',
    items: [
      'Contribute to customer engagements with structure',
      'Support discovery and demo activities',
      'Collaborate effectively with internal stakeholders',
      'Understand how opportunities progress',
    ],
    ready: 'You are ready to take on greater responsibility in live deals.',
  },
  3: {
    title: '🎉 Mission 3 Completed',
    intro: 'Well done! You are now able to:',
    items: [
      'Lead key parts of customer engagements',
      'Own technical discussions with guidance',
      'Advance opportunities with confidence',
      'Operate with growing independence',
    ],
    ready: 'You are ready to take primary ownership of selected engagements.',
  },
}

interface EditingCell {
  phaseId: string
  rowId: string
  field: keyof Omit<TableRow, 'id'>
}

// Render cell content: supports [text](url) links and - / 1. list formatting
function renderCellContent(text: string, isChecked: boolean): React.ReactNode {
  if (!text) return <span className="text-gray-600 italic text-xs">empty</span>

  const strikeClass = isChecked ? 'line-through decoration-gray-500/60' : ''

  // Parse inline segments: text mixed with [label](url) links
  function parseInline(str: string): React.ReactNode[] {
    const parts: React.ReactNode[] = []
    const linkRe = /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g
    let last = 0, m: RegExpExecArray | null
    while ((m = linkRe.exec(str)) !== null) {
      if (m.index > last) parts.push(str.slice(last, m.index))
      parts.push(
        <a key={m.index} href={m[2]} target="_blank" rel="noopener noreferrer"
          className="text-cyan-400 underline underline-offset-2 hover:text-cyan-300 transition-colors"
          onClick={e => e.stopPropagation()}>
          {m[1]}
        </a>
      )
      last = m.index + m[0].length
    }
    if (last < str.length) parts.push(str.slice(last))
    return parts
  }

  const lines = text.split('\n')
  const nonEmpty = lines.filter(l => l.trim())
  const isBullet = nonEmpty.length > 0 && nonEmpty.every(l => /^- /.test(l.trim()))
  const isNumbered = nonEmpty.length > 0 && nonEmpty.every(l => /^\d+\.\s/.test(l.trim()))

  if ((isBullet || isNumbered) && nonEmpty.length > 1) {
    const Tag = isBullet ? 'ul' : 'ol'
    const listClass = isBullet
      ? 'list-disc list-inside space-y-0.5 text-sm'
      : 'list-decimal list-inside space-y-0.5 text-sm'
    return (
      <Tag className={`${listClass} ${strikeClass}`}>
        {nonEmpty.map((line, idx) => {
          const content = isBullet ? line.trim().replace(/^- /, '') : line.trim().replace(/^\d+\.\s/, '')
          return <li key={idx}>{parseInline(content)}</li>
        })}
      </Tag>
    )
  }

  // Plain / inline — render each line, joining with <br>
  return (
    <span className={strikeClass}>
      {lines.map((line, idx) => (
        <span key={idx}>{parseInline(line)}{idx < lines.length - 1 && <br />}</span>
      ))}
    </span>
  )
}

export function Onboarding({ simulateUser = false }: { simulateUser?: boolean } = {}) {
  const { user } = useAuthStore()
  const isAdmin = simulateUser ? false : user?.role === 'admin'

  const [phases, setPhases] = useState<Phase[]>(initialPhases)
  const [checkedRows, setCheckedRows] = useState<Record<string, boolean>>({})
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({ phase1: true, phase2: true, phase3: true, phase4: true })
  const [showCelebration, setShowCelebration] = useState(false)
  const [celebrationDismissed, setCelebrationDismissed] = useState(false)
  const [showMissionPopup, setShowMissionPopup] = useState<number | null>(null)
  const [dismissedMissionPopups, setDismissedMissionPopups] = useState<Set<number>>(new Set())

  const phaseRefs = useRef<Record<string, HTMLDivElement | null>>({})
  const prevPhaseComplete = useRef<boolean[]>([])

  const isPhaseLockedForUser = (phaseIdx: number) => !isAdmin && phaseIdx > 0 && !phaseComplete[phaseIdx - 1]

  const scrollToPhase = (phaseId: string) => {
    const idx = phases.findIndex(p => p.id === phaseId)
    if (isPhaseLockedForUser(idx)) return
    setCollapsed(prev => ({ ...prev, [phaseId]: false }))
    setTimeout(() => {
      phaseRefs.current[phaseId]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 50)
  }

  // Compute per-phase completion
  const phaseComplete = useMemo(() =>
    phases.map(p => p.rows.length > 0 && p.rows.every(r => checkedRows[r.id]))
  , [phases, checkedRows])

  const allComplete = phaseComplete.every(Boolean) && phases.length === 4

  // Auto-collapse finished phase and expand the next one
  useEffect(() => {
    if (isAdmin) { prevPhaseComplete.current = [...phaseComplete]; return }
    const prev = prevPhaseComplete.current
    const justCompleted = phaseComplete.findIndex((c, i) => c && prev[i] === false)
    prevPhaseComplete.current = [...phaseComplete]
    if (justCompleted === -1) return
    // Show mission popup for phases 1–3 (indices 0–2)
    const missionNum = justCompleted + 1
    if (missionNum <= 3 && !dismissedMissionPopups.has(missionNum)) {
      setShowMissionPopup(missionNum)
      return // popup handles navigation on dismiss
    }
    if (justCompleted >= phases.length - 1) return
    const nextPhaseId = phases[justCompleted + 1]?.id
    if (!nextPhaseId) return
    setCollapsed(curr => {
      const updated = { ...curr }
      phases.forEach((p, i) => { if (phaseComplete[i]) updated[p.id] = true })
      updated[nextPhaseId] = false
      return updated
    })
    setTimeout(() => {
      phaseRefs.current[nextPhaseId]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 350)
  }, [phaseComplete])

  const dismissMissionPopup = () => {
    if (showMissionPopup === null) return
    const missionNum = showMissionPopup
    setDismissedMissionPopups(prev => new Set([...prev, missionNum]))
    setShowMissionPopup(null)
    // Now navigate to the next phase
    const justCompleted = missionNum - 1 // phase index
    if (justCompleted >= phases.length - 1) return
    const nextPhaseId = phases[justCompleted + 1]?.id
    if (!nextPhaseId) return
    setCollapsed(curr => {
      const updated = { ...curr }
      phases.forEach((p, i) => { if (phaseComplete[i]) updated[p.id] = true })
      updated[nextPhaseId] = false
      return updated
    })
    setTimeout(() => {
      phaseRefs.current[nextPhaseId]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 350)
  }

  const particles = useMemo(() =>
    Array.from({ length: 120 }, (_, i) => ({
      id: i,
      left: `${Math.random() * 100}%`,
      top: `${Math.random() * 60}%`,
      dx: ((Math.random() - 0.5) * 300).toFixed(0),
      dy: ((Math.random() - 0.5) * 300).toFixed(0),
      color: FIREWORK_COLORS[Math.floor(Math.random() * FIREWORK_COLORS.length)],
      size: (Math.random() * 7 + 3).toFixed(1),
      delay: (Math.random() * 1.8).toFixed(2),
      dur: (Math.random() * 1.2 + 0.8).toFixed(2),
      shape: Math.random() > 0.5 ? '50%' : '2px',
    }))
  , [])

  // ── Persist phases (server) + checkedRows (per-user server) ────────────────

  // Fetch latest phases from backend on mount (shared across all users)
  useEffect(() => {
    api.get('/api/onboarding/phases')
      .then(res => setPhases(res.data.phases))
      .catch(() => { /* keep initialPhases as fallback */ })
  }, [])

  // Fetch this user's progress on mount
  useEffect(() => {
    api.get('/api/onboarding/progress')
      .then(res => {
        const rows: Record<string, boolean> = res.data.checkedRows ?? {}
        setCheckedRows(rows)
        if (!isAdmin) {
          // Open only the first incomplete phase on load
          setPhases(current => {
            const completedIdx = current.map(p => p.rows.length > 0 && p.rows.every(r => rows[r.id]))
            const activeIdx = completedIdx.findIndex(c => !c)
            const next: Record<string, boolean> = {}
            current.forEach((p, i) => { next[p.id] = i !== (activeIdx === -1 ? current.length - 1 : activeIdx) })
            setCollapsed(next)
            prevPhaseComplete.current = completedIdx
            return current
          })
        }
      })
      .catch(() => {})
  }, [])

  // Save phases to backend after every admin mutation
  const savePhases = (newPhases: Phase[]) => {
    api.put('/api/onboarding/phases', { phases: newPhases }).catch(console.error)
  }

  // Fetch page settings from backend on mount
  useEffect(() => {
    api.get('/api/onboarding/settings')
      .then(res => {
        if (res.data.title) setPageTitle(res.data.title)
        if (res.data.subtitle) setPageSubtitle(res.data.subtitle)
        if (res.data.ladderLabels) setLadderLabels(res.data.ladderLabels)
        if (res.data.ladderSubs) setLadderSubs(res.data.ladderSubs)
      })
      .catch(() => {})
  }, [])

  const saveSettings = (title: string, subtitle: string, labels: string[], subs: string[]) => {
    api.put('/api/onboarding/settings', { title, subtitle, ladderLabels: labels, ladderSubs: subs }).catch(console.error)
  }

  // Save this user's progress to backend (debounced 500 ms)
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const saveProgress = (rows: Record<string, boolean>) => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      api.put('/api/onboarding/progress', { checkedRows: rows }).catch(console.error)
    }, 500)
  }

  useEffect(() => {
    if (allComplete && !celebrationDismissed) {
      const t = setTimeout(() => setShowCelebration(true), 400)
      return () => clearTimeout(t)
    }
  }, [allComplete, celebrationDismissed])
  const [editingCell, setEditingCell] = useState<EditingCell | null>(null)
  const [cellDraft, setCellDraft] = useState('')
  const [editingPhaseHeader, setEditingPhaseHeader] = useState<{ phaseId: string; field: 'title' | 'objective' } | null>(null)
  const [headerDraft, setHeaderDraft] = useState('')

  // Page title / subtitle / ladder label editing
  const [pageTitle, setPageTitle] = useState('Enterprise SE Onboarding Playbook')
  const [pageSubtitle, setPageSubtitle] = useState('Industrial Model')
  const [ladderLabels, setLadderLabels] = useState(['Systems Operator', 'Story Architect', 'Customer Strategist', 'Field-Ready SE'])
  const [ladderSubs, setLadderSubs] = useState(['Phase 1 · 0–30 Days', 'Phase 2 · 31–60 Days', 'Phase 3 · 61–90 Days', 'Phase 4 · 91–120 Days'])
  const [editingTitle, setEditingTitle] = useState(false)
  const [editingSubtitle, setEditingSubtitle] = useState(false)
  const [editingLadderIdx, setEditingLadderIdx] = useState<number | null>(null)
  const [editingLadderSubIdx, setEditingLadderSubIdx] = useState<number | null>(null)
  const [labelDraft, setLabelDraft] = useState('')

  const toggleRow = (rowId: string) => {
    const updated = { ...checkedRows, [rowId]: !checkedRows[rowId] }
    setCheckedRows(updated)
    saveProgress(updated)
  }

  // ── Cell editing ──────────────────────────────────────────────────────────

  const startCellEdit = (phaseId: string, rowId: string, field: keyof Omit<TableRow, 'id'>, value: string) => {
    setEditingCell({ phaseId, rowId, field })
    setCellDraft(value)
  }

  const commitCellEdit = () => {
    if (!editingCell) return
    const newPhases = phases.map(p =>
      p.id !== editingCell.phaseId ? p : {
        ...p,
        rows: p.rows.map(r =>
          r.id !== editingCell.rowId ? r : { ...r, [editingCell.field]: cellDraft }
        ),
      }
    )
    setPhases(newPhases)
    savePhases(newPhases)
    setEditingCell(null)
  }

  const cancelCellEdit = () => setEditingCell(null)

  // ── Row management ────────────────────────────────────────────────────────

  const addRow = (phaseId: string) => {
    const newPhases = phases.map(p =>
      p.id !== phaseId ? p : {
        ...p,
        rows: [...p.rows, { id: generateId(), category: '', module: '', duration: '', deliverable: '', signOff: '' }],
      }
    )
    setPhases(newPhases)
    savePhases(newPhases)
  }

  const deleteRow = (phaseId: string, rowId: string) => {
    const newPhases = phases.map(p =>
      p.id !== phaseId ? p : { ...p, rows: p.rows.filter(r => r.id !== rowId) }
    )
    setPhases(newPhases)
    savePhases(newPhases)
    setCheckedRows(prev => { const n = { ...prev }; delete n[rowId]; return n })
  }

  const moveRow = (phaseId: string, rowIdx: number, direction: 'up' | 'down') => {
    const newPhases = phases.map(p => {
      if (p.id !== phaseId) return p
      const rows = [...p.rows]
      const swapIdx = direction === 'up' ? rowIdx - 1 : rowIdx + 1
      if (swapIdx < 0 || swapIdx >= rows.length) return p;
      [rows[rowIdx], rows[swapIdx]] = [rows[swapIdx], rows[rowIdx]]
      return { ...p, rows }
    })
    setPhases(newPhases)
    savePhases(newPhases)
  }

  // ── Phase header editing ──────────────────────────────────────────────────

  const startHeaderEdit = (phaseId: string, field: 'title' | 'objective', value: string) => {
    setEditingPhaseHeader({ phaseId, field })
    setHeaderDraft(value)
  }

  const commitHeaderEdit = () => {
    if (!editingPhaseHeader) return
    const newPhases = phases.map(p =>
      p.id !== editingPhaseHeader.phaseId ? p : { ...p, [editingPhaseHeader.field]: headerDraft }
    )
    setPhases(newPhases)
    savePhases(newPhases)
    setEditingPhaseHeader(null)
  }

  // ─────────────────────────────────────────────────────────────────────────

  const phaseAccent = [
    { gradient: 'from-cyan-500 to-blue-600', ring: 'ring-cyan-400', dot: 'bg-cyan-400', bar: 'from-cyan-400 to-blue-500', text: 'text-cyan-400', glow: 'shadow-cyan-500/60' },
    { gradient: 'from-blue-500 to-indigo-600', ring: 'ring-blue-400', dot: 'bg-blue-400', bar: 'from-blue-400 to-indigo-500', text: 'text-blue-400', glow: 'shadow-blue-500/60' },
    { gradient: 'from-indigo-500 to-purple-600', ring: 'ring-indigo-400', dot: 'bg-indigo-400', bar: 'from-indigo-400 to-purple-500', text: 'text-indigo-400', glow: 'shadow-indigo-500/60' },
    { gradient: 'from-purple-500 to-pink-600', ring: 'ring-purple-400', dot: 'bg-purple-400', bar: 'from-purple-400 to-pink-500', text: 'text-purple-400', glow: 'shadow-purple-500/60' },
  ]

  return (
    <div className="flex-1 h-full overflow-y-auto bg-[#07182D] px-6 py-8">      <div className="max-w-6xl mx-auto w-full">

        {/* ── Mission completion popup (phases 1–3) ── */}
        {showMissionPopup !== null && MISSION_POPUPS[showMissionPopup] && (() => {
          const popup = MISSION_POPUPS[showMissionPopup]
          const nextMission = showMissionPopup + 1
          return (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
              <style>{`@keyframes pop-in { 0% { opacity:0; transform: scale(0.5) translateY(20px); } 60% { transform: scale(1.08) translateY(-4px); } 100% { opacity:1; transform: scale(1) translateY(0); } }`}</style>
              <div
                className="relative bg-[#081a2e] border border-white/10 rounded-2xl px-10 py-8 max-w-md w-full mx-4 shadow-2xl cursor-pointer hover:border-white/20 transition-all duration-200 hover:scale-[1.01]"
                style={{ animation: 'pop-in 0.5s cubic-bezier(.34,1.56,.64,1) both' }}
                onClick={dismissMissionPopup}
              >
                <h2 className="text-2xl font-extrabold text-white mb-3 tracking-tight">{popup.title}</h2>
                <p className="text-gray-400 text-sm mb-3">{popup.intro}</p>
                <ul className="space-y-2 mb-5">
                  {popup.items.map((item, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-gray-200">
                      <span className="mt-0.5 w-4 h-4 flex-shrink-0 rounded-full bg-green-500/20 border border-green-500/40 flex items-center justify-center">
                        <Check className="w-2.5 h-2.5 text-green-400" strokeWidth={3} />
                      </span>
                      {item}
                    </li>
                  ))}
                </ul>
                <p className="text-cyan-300/80 text-sm font-medium mb-5">{popup.ready}</p>
                <div className="flex items-center justify-center gap-2 text-xs text-gray-500">
                  <span>Click anywhere to continue to Mission {nextMission}</span>
                  <span className="text-gray-600">→</span>
                </div>
              </div>
            </div>
          )
        })()}

        {/* ── Fireworks celebration overlay ── */}
        {showCelebration && (
          <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-none">
            {/* Particles */}
            <style>{`
              @keyframes burst {
                0%   { transform: translate(0,0) scale(1); opacity: 1; }
                100% { transform: translate(var(--dx), var(--dy)) scale(0); opacity: 0; }
              }
              @keyframes pop-in {
                0%   { opacity:0; transform: scale(0.5) translateY(20px); }
                60%  { transform: scale(1.08) translateY(-4px); }
                100% { opacity:1; transform: scale(1) translateY(0); }
              }
            `}</style>
            {particles.map(p => (
              <div
                key={p.id}
                style={{
                  position: 'fixed',
                  left: p.left,
                  top: p.top,
                  width: `${p.size}px`,
                  height: `${p.size}px`,
                  borderRadius: p.shape,
                  background: p.color,
                  ['--dx' as string]: `${p.dx}px`,
                  ['--dy' as string]: `${p.dy}px`,
                  animation: `burst ${p.dur}s ease-out ${p.delay}s both`,
                  boxShadow: `0 0 6px ${p.color}`,
                }}
              />
            ))}
            {/* Modal card */}
            <div
              className="pointer-events-auto relative bg-[#0a1f38] border border-white/10 rounded-2xl px-12 py-10 max-w-lg w-full mx-4 text-center shadow-2xl"
              style={{ animation: 'pop-in 0.6s cubic-bezier(.34,1.56,.64,1) 0.2s both' }}
            >
              <div className="text-6xl mb-4">🎉</div>
              <h2 className="text-3xl font-extrabold text-white mb-3 tracking-tight">Mission Accomplished!</h2>
              <p className="text-gray-300 text-sm mb-3 text-left">Excellent work! You are now able to:</p>
              <ul className="space-y-2 mb-4 text-left">
                {[
                  'Independently lead technical sales engagements',
                  'Represent the SE team confidently',
                  'Drive opportunities from discovery to proposal',
                  'Contribute value back to the organization',
                ].map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-gray-200">
                    <span className="mt-0.5 w-4 h-4 flex-shrink-0 rounded-full bg-green-500/20 border border-green-500/40 flex items-center justify-center">
                      <Check className="w-2.5 h-2.5 text-green-400" strokeWidth={3} />
                    </span>
                    {item}
                  </li>
                ))}
              </ul>
              <p className="text-cyan-300/80 text-sm font-medium mb-6 text-left">You are operating as a fully capable and trusted SE.</p>
              <button
                onClick={() => { setShowCelebration(false); setCelebrationDismissed(true) }}
                className="px-6 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 text-white rounded-lg font-semibold text-sm hover:from-cyan-400 hover:to-blue-500 transition-all shadow-lg shadow-cyan-500/30"
              >
                Let's Go! 🏁
              </button>
            </div>
          </div>
        )}

        {/* Page header */}
        <div className="mb-6">
          {/* Title */}
          {isAdmin && editingTitle ? (
            <div className="flex items-center gap-2 mb-1">
              <input autoFocus className="bg-slate-700/80 text-white border border-cyan-400/50 rounded px-2 py-1 text-2xl font-bold focus:outline-none w-full max-w-xl" value={labelDraft} onChange={e => setLabelDraft(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { setPageTitle(labelDraft); saveSettings(labelDraft, pageSubtitle, ladderLabels, ladderSubs); setEditingTitle(false) } if (e.key === 'Escape') setEditingTitle(false) }} />
              <button onClick={() => { setPageTitle(labelDraft); saveSettings(labelDraft, pageSubtitle, ladderLabels, ladderSubs); setEditingTitle(false) }} className="p-1 hover:bg-green-500/20 rounded text-green-400"><Check className="w-4 h-4" /></button>
              <button onClick={() => setEditingTitle(false)} className="p-1 hover:bg-red-500/20 rounded text-red-400"><X className="w-4 h-4" /></button>
            </div>
          ) : (
            <div className="flex items-center gap-2 group/ptitle">
              <h1 className="text-2xl font-bold text-white">{pageTitle}</h1>
              {isAdmin && <button onClick={() => { setLabelDraft(pageTitle); setEditingTitle(true); setEditingSubtitle(false); setEditingLadderIdx(null) }} className="opacity-0 group-hover/ptitle:opacity-100 p-0.5 hover:bg-slate-600/50 rounded text-gray-500 transition-opacity"><Pencil className="w-3.5 h-3.5" /></button>}
            </div>
          )}
          {/* Subtitle */}
          {isAdmin && editingSubtitle ? (
            <div className="flex items-center gap-2 mt-1">
              <input autoFocus className="bg-slate-700/80 text-cyan-400 border border-cyan-400/50 rounded px-2 py-0.5 text-sm font-medium focus:outline-none w-64" value={labelDraft} onChange={e => setLabelDraft(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { setPageSubtitle(labelDraft); saveSettings(pageTitle, labelDraft, ladderLabels, ladderSubs); setEditingSubtitle(false) } if (e.key === 'Escape') setEditingSubtitle(false) }} />
              <button onClick={() => { setPageSubtitle(labelDraft); saveSettings(pageTitle, labelDraft, ladderLabels, ladderSubs); setEditingSubtitle(false) }} className="p-1 hover:bg-green-500/20 rounded text-green-400"><Check className="w-3.5 h-3.5" /></button>
              <button onClick={() => setEditingSubtitle(false)} className="p-1 hover:bg-red-500/20 rounded text-red-400"><X className="w-3.5 h-3.5" /></button>
            </div>
          ) : (
            <div className="flex items-center gap-2 mt-1 group/psub">
              <p className="text-cyan-400 text-sm font-medium">{pageSubtitle}</p>
              {isAdmin && <button onClick={() => { setLabelDraft(pageSubtitle); setEditingSubtitle(true); setEditingTitle(false); setEditingLadderIdx(null); setEditingLadderSubIdx(null) }} className="opacity-0 group-hover/psub:opacity-100 p-0.5 hover:bg-slate-600/50 rounded text-gray-500 transition-opacity"><Pencil className="w-3 h-3" /></button>}
            </div>
          )}
          {isAdmin && (
            <p className="text-gray-500 text-xs mt-2">Admin mode — click any cell, header, or gate to edit. Use + / × to add or remove rows.</p>
          )}
        </div>

        {/* ── Mission Ladder nodes ── */}
        <div className="mb-10 rounded-2xl border border-slate-700/50 bg-slate-800/30 backdrop-blur-sm overflow-hidden px-6 py-5">
          <div className="relative flex items-start justify-between">
            {/* connector line background */}
            <div className="absolute top-7 left-0 right-0 h-2 rounded-full bg-slate-700/50" />
            {/* connector line fill */}
            <div
              className="absolute top-7 left-0 h-2 rounded-full bg-gradient-to-r from-cyan-400 via-blue-500 via-indigo-500 to-purple-500 transition-all duration-1000 ease-out"
              style={{ width: `${phaseComplete.filter(Boolean).length === 0 ? 0 : phaseComplete.filter(Boolean).length === 4 ? 100 : ((phaseComplete.filter(Boolean).length - 0.5) / 3) * 100}%` }}
            />
            {LADDER_STAGES.map((stage, i) => {
              const done = phaseComplete[i]
              const active = !done && (i === 0 || phaseComplete[i - 1])
              const locked = isPhaseLockedForUser(i)
              const phaseId = `phase${i + 1}`
              return (
                <div key={i} className="flex flex-col items-center gap-2 relative z-10" style={{ width: '25%' }}>
                  <button
                    onClick={() => scrollToPhase(phaseId)}
                    title={locked ? `Complete Phase ${i} first to unlock` : `Go to ${ladderLabels[i] ?? stage.label}`}
                    className={`
                      relative w-14 h-14 rounded-full flex items-center justify-center border-2 transition-all duration-500 focus:outline-none
                      ${locked ? 'cursor-not-allowed' : 'cursor-pointer hover:scale-110'}
                      ${done
                        ? `bg-gradient-to-br ${stage.color} border-transparent shadow-xl ${stage.glow}`
                        : active
                          ? `${stage.bg} ${stage.border} shadow-md`
                          : `bg-slate-800 ${stage.border}`
                      }
                    `}
                  >
                    <span className="text-2xl leading-none select-none transition-all duration-500">
                      {stage.emoji}
                    </span>
                    {done && (
                      <span className="absolute -top-1 -right-1 w-5 h-5 bg-green-500 rounded-full flex items-center justify-center shadow-lg">
                        <Check className="w-3 h-3 text-white" strokeWidth={3} />
                      </span>
                    )}
                    {locked && (
                      <span className="absolute -bottom-1 -right-1 w-5 h-5 bg-slate-700 border border-slate-500 rounded-full flex items-center justify-center">
                        <Lock className="w-2.5 h-2.5 text-slate-400" />
                      </span>
                    )}
                  </button>
                  <div className="w-full text-center">
                    {isAdmin && editingLadderIdx === i ? (
                      <div className="flex items-center gap-1 justify-center mt-0.5">
                        <input autoFocus className="bg-slate-700/80 text-white border border-cyan-400/50 rounded px-1 py-0.5 text-[11px] font-bold focus:outline-none w-28 text-center" value={labelDraft} onChange={e => setLabelDraft(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { const upd = ladderLabels.map((l, j) => j === i ? labelDraft : l); setLadderLabels(upd); saveSettings(pageTitle, pageSubtitle, upd, ladderSubs); setEditingLadderIdx(null) } if (e.key === 'Escape') setEditingLadderIdx(null) }} />
                        <button onClick={() => { const upd = ladderLabels.map((l, j) => j === i ? labelDraft : l); setLadderLabels(upd); saveSettings(pageTitle, pageSubtitle, upd, ladderSubs); setEditingLadderIdx(null) }} className="p-0.5 hover:bg-green-500/20 rounded text-green-400"><Check className="w-3 h-3" /></button>
                        <button onClick={() => setEditingLadderIdx(null)} className="p-0.5 hover:bg-red-500/20 rounded text-red-400"><X className="w-3 h-3" /></button>
                      </div>
                    ) : (
                      <div className={`group/lbl flex items-center justify-center gap-1`}>
                        <p className={`text-xs font-bold transition-colors duration-500 ${done ? stage.text : active ? 'text-gray-200' : 'text-slate-600'}`}>{ladderLabels[i] ?? stage.label}</p>
                        {isAdmin && <button onClick={() => { setLabelDraft(ladderLabels[i] ?? stage.label); setEditingLadderIdx(i); setEditingLadderSubIdx(null); setEditingTitle(false); setEditingSubtitle(false) }} className="opacity-0 group-hover/lbl:opacity-100 p-0.5 hover:bg-slate-600/50 rounded text-gray-500 transition-opacity"><Pencil className="w-2.5 h-2.5" /></button>}
                      </div>
                    )}
                    {isAdmin && editingLadderSubIdx === i ? (
                      <div className="flex items-center gap-1 justify-center mt-0.5">
                        <input autoFocus className="bg-slate-700/80 text-slate-300 border border-slate-500/60 rounded px-1 py-0.5 text-[10px] focus:outline-none w-32 text-center" value={labelDraft} onChange={e => setLabelDraft(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { const upd = ladderSubs.map((s, j) => j === i ? labelDraft : s); setLadderSubs(upd); saveSettings(pageTitle, pageSubtitle, ladderLabels, upd); setEditingLadderSubIdx(null) } if (e.key === 'Escape') setEditingLadderSubIdx(null) }} />
                        <button onClick={() => { const upd = ladderSubs.map((s, j) => j === i ? labelDraft : s); setLadderSubs(upd); saveSettings(pageTitle, pageSubtitle, ladderLabels, upd); setEditingLadderSubIdx(null) }} className="p-0.5 hover:bg-green-500/20 rounded text-green-400"><Check className="w-3 h-3" /></button>
                        <button onClick={() => setEditingLadderSubIdx(null)} className="p-0.5 hover:bg-red-500/20 rounded text-red-400"><X className="w-3 h-3" /></button>
                      </div>
                    ) : (
                      <div className="group/sub flex items-center justify-center gap-1">
                        <p className="text-[10px] text-slate-500 mt-0.5">{ladderSubs[i] ?? stage.sub}</p>
                        {isAdmin && <button onClick={() => { setLabelDraft(ladderSubs[i] ?? stage.sub); setEditingLadderSubIdx(i); setEditingLadderIdx(null); setEditingTitle(false); setEditingSubtitle(false) }} className="opacity-0 group-hover/sub:opacity-100 p-0.5 hover:bg-slate-600/50 rounded text-gray-500 transition-opacity mt-0.5"><Pencil className="w-2 h-2" /></button>}
                      </div>
                    )}
                    {done && (
                      <span className="inline-block mt-1 text-[9px] font-bold text-green-400 bg-green-500/10 border border-green-500/20 px-1.5 py-0.5 rounded-full">Complete ✓</span>
                    )}
                    {active && !done && !locked && (
                      <span className={`inline-block mt-1 text-[9px] font-bold ${stage.text} bg-slate-700/60 border border-slate-600/40 px-1.5 py-0.5 rounded-full`}>In Progress</span>
                    )}
                    {locked && (
                      <span className="inline-block mt-1 text-[9px] font-bold text-slate-500 bg-slate-800/60 border border-slate-600/30 px-1.5 py-0.5 rounded-full">🔒 Locked</span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Phases */}
        <div className="space-y-10">
          {phases.map((phase, phaseIdx) => {
            const accent = phaseAccent[phaseIdx % phaseAccent.length]
            const total = phase.rows.length
            const done = phase.rows.filter(r => checkedRows[r.id]).length
            const pct = total === 0 ? 0 : Math.round((done / total) * 100)
            const allDone = done === total && total > 0
            const isCollapsed = !!collapsed[phase.id]
            const isLocked = isPhaseLockedForUser(phaseIdx)

            return (
              <div key={phase.id} ref={el => { phaseRefs.current[phase.id] = el }} className={`rounded-xl border overflow-hidden transition-all duration-300 ${isLocked ? 'border-slate-700/30 opacity-60' : 'border-slate-700/50'}`}>

                {/* Phase header */}
                <div
                  className={`px-6 py-4 select-none ${isLocked ? 'bg-slate-800/70 cursor-not-allowed' : `bg-gradient-to-r ${accent.gradient} cursor-pointer`}`}
                  onClick={() => { if (!isLocked) setCollapsed(prev => ({ ...prev, [phase.id]: !prev[phase.id] })) }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1" onClick={e => e.stopPropagation()}>
                      {/* Title */}
                      {isAdmin && editingPhaseHeader?.phaseId === phase.id && editingPhaseHeader.field === 'title' ? (
                        <div className="flex items-center gap-2 mb-1">
                          <input autoFocus className="flex-1 bg-white/20 text-white placeholder-white/50 border border-white/40 rounded px-2 py-1 text-lg font-bold focus:outline-none" value={headerDraft} onChange={e => setHeaderDraft(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') commitHeaderEdit(); if (e.key === 'Escape') setEditingPhaseHeader(null) }} />
                          <button onClick={commitHeaderEdit} className="p-1 hover:bg-white/20 rounded text-white"><Check className="w-4 h-4" /></button>
                          <button onClick={() => setEditingPhaseHeader(null)} className="p-1 hover:bg-white/20 rounded text-white"><X className="w-4 h-4" /></button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 mb-1 group/title">
                          <h2 className={`text-lg font-bold ${isLocked ? 'text-slate-400' : 'text-white'}`}>{phase.title}</h2>
                          {isAdmin && <button onClick={e => { e.stopPropagation(); startHeaderEdit(phase.id, 'title', phase.title) }} className="opacity-0 group-hover/title:opacity-100 p-0.5 hover:bg-white/20 rounded text-white/70 transition-opacity"><Pencil className="w-3 h-3" /></button>}
                        </div>
                      )}
                      {/* Objective */}
                      {isAdmin && editingPhaseHeader?.phaseId === phase.id && editingPhaseHeader.field === 'objective' ? (
                        <div className="flex items-center gap-2">
                          <input autoFocus className="flex-1 bg-white/20 text-white/90 placeholder-white/50 border border-white/40 rounded px-2 py-0.5 text-sm focus:outline-none" value={headerDraft} onChange={e => setHeaderDraft(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') commitHeaderEdit(); if (e.key === 'Escape') setEditingPhaseHeader(null) }} />
                          <button onClick={commitHeaderEdit} className="p-1 hover:bg-white/20 rounded text-white"><Check className="w-3 h-3" /></button>
                          <button onClick={() => setEditingPhaseHeader(null)} className="p-1 hover:bg-white/20 rounded text-white"><X className="w-3 h-3" /></button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2 group/obj">
                          <p className="text-white/80 text-sm font-medium">Objective: {phase.objective}</p>
                          {isAdmin && <button onClick={e => { e.stopPropagation(); startHeaderEdit(phase.id, 'objective', phase.objective) }} className="opacity-0 group-hover/obj:opacity-100 p-0.5 hover:bg-white/20 rounded text-white/70 transition-opacity"><Pencil className="w-3 h-3" /></button>}
                        </div>
                      )}
                    </div>
                    {/* Collapse toggle / Lock indicator */}
                    <div className="flex items-center gap-2 pt-0.5 flex-shrink-0">
                      {isLocked ? (
                        <div className="flex items-center gap-1.5 bg-slate-700/60 border border-slate-600/50 rounded-lg px-2.5 py-1">
                          <Lock className="w-3.5 h-3.5 text-slate-400" />
                          <span className="text-slate-400 text-xs font-medium">Complete Phase {phaseIdx} first</span>
                        </div>
                      ) : (
                        <>
                          {allDone && <Trophy className="w-4 h-4 text-yellow-300" />}
                          <span className="text-white/60 text-xs font-medium">{done}/{total}</span>
                          {isCollapsed
                            ? <ChevronDown className="w-5 h-5 text-white/70" />
                            : <ChevronUp className="w-5 h-5 text-white/70" />
                          }
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* ── Collapsible body ── */}
                {!isLocked && !isCollapsed && <>

                {/* ── Progress pipeline ── */}
                <div className="bg-slate-900/60 border-b border-slate-700/40 px-6 py-4">
                  {/* Top bar: count + percent */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      {allDone ? (
                        <span className={`flex items-center gap-1.5 text-xs font-bold ${accent.text}`}>
                          <Trophy className="w-3.5 h-3.5" /> Phase Complete!
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400 font-medium">{done} / {total} completed</span>
                      )}
                    </div>
                    <span className={`text-xs font-bold tabular-nums ${allDone ? accent.text : 'text-gray-400'}`}>{pct}%</span>
                  </div>

                  {/* Filled progress bar */}
                  <div className="relative h-2 bg-slate-700/60 rounded-full overflow-hidden">
                    <div
                      className={`absolute inset-y-0 left-0 bg-gradient-to-r ${accent.bar} rounded-full transition-all duration-700 ease-out`}
                      style={{ width: `${pct}%` }}
                    />
                    {allDone && (
                      <div className={`absolute inset-0 bg-gradient-to-r ${accent.bar} rounded-full opacity-40 animate-pulse`} />
                    )}
                  </div>

                  {/* Step nodes pipeline */}
                  <div className="relative flex items-center" style={{ marginTop: '-18px' }}>
                    <div className="relative flex justify-between w-full">
                      {phase.rows.map((row, i) => {
                        const isChecked = !!checkedRows[row.id]
                        const label = row.category ? row.category.split(' ')[0] : `Step ${i + 1}`
                        return (
                          <div key={row.id} className="flex flex-col items-center gap-1.5" style={{ width: `${100 / total}%` }}>
                            {/* node */}
                            <div
                              className={`
                                relative z-10 w-7 h-7 rounded-full flex items-center justify-center border-2 transition-all duration-500 cursor-pointer select-none
                                ${isChecked
                                  ? `${accent.dot} border-transparent text-white shadow-lg ${accent.glow}`
                                  : 'bg-slate-800 border-slate-600 text-slate-500 hover:border-slate-400'
                                }
                              `}
                              onClick={() => toggleRow(row.id)}
                              title={row.category || `Step ${i + 1}`}
                            >
                              {isChecked
                                ? <Check className="w-3.5 h-3.5 text-white" strokeWidth={3} />
                                : <span className="text-[10px] font-bold">{i + 1}</span>
                              }
                              {/* pulse ring on tick */}
                              {isChecked && (
                                <span className={`absolute inset-0 rounded-full ${accent.dot} opacity-0`} />
                              )}
                            </div>
                            {/* label */}
                            <span className={`text-[9px] text-center leading-tight max-w-[52px] truncate transition-colors duration-300 ${isChecked ? accent.text : 'text-slate-500'}`}>
                              {label}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* All done banner */}
                  {allDone && (
                    <div className={`mt-3 flex items-center justify-center gap-2 py-1.5 rounded-lg bg-gradient-to-r ${accent.bar} bg-opacity-10 border border-white/10`}>
                      <Trophy className="w-3.5 h-3.5 text-white" />
                      <span className="text-white text-xs font-semibold tracking-wide">All tasks signed off — phase complete 🎉</span>
                    </div>
                  )}
                </div>

                {/* Table */}
                <div className="overflow-x-auto bg-slate-800/30">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-700/50 bg-slate-800/60">
                        {COLUMNS.map(col => (
                          <th key={col.key} className="text-left px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider whitespace-nowrap">
                            {col.label}
                          </th>
                        ))}
                        <th className="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wider text-center whitespace-nowrap w-20">Done</th>
                        {isAdmin && <th className="px-3 py-3 w-20" />}
                      </tr>
                    </thead>
                    <tbody>
                      {phase.rows.map((row, rowIdx) => {
                        const isChecked = !!checkedRows[row.id]
                        return (
                          <tr
                            key={row.id}
                            className={`border-b border-slate-700/30 transition-all duration-500 group/row
                              ${isChecked
                                ? 'bg-green-900/10 hover:bg-green-900/15'
                                : rowIdx % 2 === 0 ? 'bg-slate-800/10 hover:bg-slate-700/20' : 'bg-slate-800/25 hover:bg-slate-700/20'
                              }`}
                          >
                            {COLUMNS.map(col => {
                              const isEditing =
                                editingCell?.phaseId === phase.id &&
                                editingCell?.rowId === row.id &&
                                editingCell?.field === col.key
                              return (
                                <td key={col.key} className={`px-4 py-3 align-top transition-all duration-300 ${isChecked ? 'text-gray-500' : 'text-gray-200'}`}>
                                  {isAdmin && isEditing ? (
                                    <div className="flex items-start gap-1">
                                      <div className="flex-1">
                                        <textarea autoFocus rows={3} className="w-full bg-slate-700/80 text-white border border-cyan-400/50 rounded px-2 py-1 text-sm focus:outline-none resize-none min-w-[120px]" value={cellDraft} onChange={e => setCellDraft(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); commitCellEdit() } if (e.key === 'Escape') cancelCellEdit() }} />
                                        <p className="text-[10px] text-slate-500 mt-0.5 leading-tight">Shift+Enter for newline &nbsp;·&nbsp; <span className="font-mono">[text](url)</span> for links &nbsp;·&nbsp; <span className="font-mono">- item</span> or <span className="font-mono">1. item</span> per line for lists</p>
                                      </div>
                                      <div className="flex flex-col gap-1 mt-0.5">
                                        <button onClick={commitCellEdit} className="p-0.5 hover:bg-green-500/20 rounded text-green-400"><Check className="w-3.5 h-3.5" /></button>
                                        <button onClick={cancelCellEdit} className="p-0.5 hover:bg-red-500/20 rounded text-red-400"><X className="w-3.5 h-3.5" /></button>
                                      </div>
                                    </div>
                                  ) : (
                                    <div
                                      className={`${isAdmin ? 'cursor-pointer hover:bg-slate-600/30 rounded px-1 -mx-1 py-0.5 group/cell relative' : ''}`}
                                      onClick={() => isAdmin && startCellEdit(phase.id, row.id, col.key, row[col.key])}
                                    >
                                      {renderCellContent(row[col.key], isChecked)}
                                      {isAdmin && <Pencil className="w-3 h-3 text-gray-500 absolute right-1 top-1 opacity-0 group-hover/cell:opacity-100 transition-opacity" />}
                                    </div>
                                  )}
                                </td>
                              )
                            })}

                            {/* Checkbox cell */}
                            <td className="px-4 py-3 align-middle text-center">
                              <button
                                onClick={() => toggleRow(row.id)}
                                className={`
                                  relative w-6 h-6 rounded-md border-2 flex items-center justify-center mx-auto transition-all duration-300 focus:outline-none
                                  ${isChecked
                                    ? `${accent.dot} border-transparent shadow-md ${accent.glow}`
                                    : 'bg-transparent border-slate-500 hover:border-slate-300'
                                  }
                                `}
                                title="Mark as complete"
                              >
                                <Check
                                  className={`w-3.5 h-3.5 transition-all duration-300 ${isChecked ? 'text-white opacity-100 scale-100' : 'opacity-0 scale-50'}`}
                                  strokeWidth={3}
                                />
                                {isChecked && <span className={`absolute inset-0 rounded-md ${accent.dot} opacity-0`} />}
                              </button>
                            </td>

                            {isAdmin && (
                              <td className="px-3 py-3 align-top">
                                <div className="opacity-0 group-hover/row:opacity-100 flex flex-col items-center gap-0.5 transition-opacity">
                                  <button onClick={() => moveRow(phase.id, rowIdx, 'up')} disabled={rowIdx === 0} className="p-1 hover:bg-blue-500/20 rounded text-gray-500 hover:text-blue-400 transition-all disabled:opacity-20 disabled:cursor-not-allowed" title="Move up">
                                    <ArrowUp className="w-3 h-3" />
                                  </button>
                                  <button onClick={() => moveRow(phase.id, rowIdx, 'down')} disabled={rowIdx === phase.rows.length - 1} className="p-1 hover:bg-blue-500/20 rounded text-gray-500 hover:text-blue-400 transition-all disabled:opacity-20 disabled:cursor-not-allowed" title="Move down">
                                    <ArrowDown className="w-3 h-3" />
                                  </button>
                                  <button onClick={() => deleteRow(phase.id, row.id)} className="p-1 hover:bg-red-500/20 rounded text-gray-500 hover:text-red-400 transition-all mt-0.5" title="Delete row">
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              </td>
                            )}
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Add row + Gate */}
                <div className="bg-slate-800/20 border-t border-slate-700/30 px-4 py-2 flex items-center justify-end">
                  {isAdmin && (
                    <button onClick={() => addRow(phase.id)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-cyan-400 hover:text-white hover:bg-cyan-500/20 border border-cyan-500/30 hover:border-cyan-400/60 rounded-lg transition-all font-medium">
                      <Plus className="w-3.5 h-3.5" />
                      Add row
                    </button>
                  )}
                </div>
                </> /* end collapsible body */}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
