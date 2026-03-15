'use client'

import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { api } from '@/lib/api'
import { Check, ChevronDown, ExternalLink, Lightbulb, Lock, Pencil, Plus, Trophy, X } from 'lucide-react'

// ── Types ──────────────────────────────────────────────────────────────────────
interface LearnMoreItem {
  id: string
  type: 'link' | 'text'
  label: string
  url?: string
}

interface Task {
  id: string
  category: string   // displayed as title
  module: string     // displayed as description
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

// ── Helpers ────────────────────────────────────────────────────────────────────
const rnd = () => Math.random().toString(36).slice(2, 10)

const ACCENTS = [
  { pill: 'bg-cyan-500',    gradient: 'from-cyan-600 to-blue-700',     dot: 'bg-cyan-500',    dotGlow: 'shadow-cyan-500/50',    bar: 'bg-cyan-400',    text: 'text-cyan-400',    border: 'border-cyan-500/30',    icon: '🥷' },
  { pill: 'bg-purple-500',  gradient: 'from-purple-600 to-indigo-700', dot: 'bg-purple-500',  dotGlow: 'shadow-purple-500/50',  bar: 'bg-purple-400',  text: 'text-purple-400',  border: 'border-purple-500/30',  icon: '⚔️' },
  { pill: 'bg-amber-500',   gradient: 'from-amber-500 to-orange-600',  dot: 'bg-amber-500',   dotGlow: 'shadow-amber-500/50',   bar: 'bg-amber-400',   text: 'text-amber-400',   border: 'border-amber-500/30',   icon: '🛡️' },
  { pill: 'bg-emerald-500', gradient: 'from-emerald-600 to-green-700', dot: 'bg-emerald-500', dotGlow: 'shadow-emerald-500/50', bar: 'bg-emerald-400', text: 'text-emerald-400', border: 'border-emerald-500/30', icon: '🎓' },
]

const DEFAULT_TIPS = [
  'Bookmark this page for easy access as you navigate throughout your SE onboarding journey.',
  'Check off items as you go to track your progress. Your progress is automatically saved to your account.',
  "Can't find what you need? Your assigned mentor or manager is ready to provide 1:1 support.",
]

// ── Component ──────────────────────────────────────────────────────────────────
export function Onboarding({ simulateUser = false }: { simulateUser?: boolean }) {
  const user = useAuthStore(s => s.user)
  const isAdmin = !simulateUser && user?.role === 'admin'

  // ── Data ──
  const [phases, setPhases] = useState<Phase[]>([])
  const [activeTab, setActiveTab] = useState(0)
  const [checked, setChecked] = useState<Record<string, boolean>>({})
  const [tips, setTips] = useState<string[]>(DEFAULT_TIPS)
  const [pageTitle, setPageTitle] = useState('Enterprise SE Onboarding Playbook')
  const [pageSub, setPageSub] = useState('Industrial Model')

  // ── Inline edit state ──
  type TaskField = 'category' | 'module' | 'url'
  const [editTask, setEditTask] = useState<{ pId: string; tId: string; field: TaskField } | null>(null)
  const [editVal, setEditVal] = useState('')
  const [editPhase, setEditPhase] = useState<{ pId: string; field: 'title' | 'objective' } | null>(null)
  const [editPhaseVal, setEditPhaseVal] = useState('')
  const [editPageField, setEditPageField] = useState<'title' | 'sub' | null>(null)
  const [editPageVal, setEditPageVal] = useState('')
  const [editTipIdx, setEditTipIdx] = useState<number | null>(null)
  const [editTipVal, setEditTipVal] = useState('')

  // ── Learn More expand / edit state ──
  const [expandedLM, setExpandedLM] = useState<Set<string>>(new Set())
  const [lmEdit, setLmEdit] = useState<{
    pId: string; taskId: string; itemId: string | null
    type: 'link' | 'text'; label: string; url: string
  } | null>(null)

  // ── Celebration ──
  const [fireworks, setFireworks] = useState(false)
  const [unlockPopup, setUnlockPopup] = useState<number | null>(null)
  const prevComplete = useRef<Record<string, boolean>>({})

  // ── Fetch ──
  useEffect(() => {
    api.get('/api/onboarding/phases').then(r => setPhases(r.data.phases)).catch(console.error)
    api.get('/api/onboarding/progress').then(r => setChecked(r.data.checkedRows || {})).catch(console.error)
    api.get('/api/onboarding/settings').then(r => {
      const d = r.data
      if (d.title) setPageTitle(d.title)
      if (d.subtitle) setPageSub(d.subtitle)
      if (d.tipCards?.length) setTips(d.tipCards)
    }).catch(console.error)
  }, [])

  // ── Phase completion detection ──
  useEffect(() => {
    phases.forEach((phase, idx) => {
      const wasComplete = prevComplete.current[phase.id]
      const allDone = phase.rows.length > 0 && phase.rows.every(r => checked[r.id])
      if (allDone && !wasComplete) {
        if (idx < phases.length - 1) setUnlockPopup(idx + 1)
        else setFireworks(true)
      }
      prevComplete.current[phase.id] = allDone
    })
  }, [checked, phases])

  // ── Persist helpers ──
  const savePhases = useCallback((p: Phase[]) => {
    api.put('/api/onboarding/phases', { phases: p }).catch(console.error)
  }, [])

  const saveSettings = useCallback((title: string, sub: string, t: string[]) => {
    api.put('/api/onboarding/settings', { title, subtitle: sub, ladderLabels: [], ladderSubs: [], tipCards: t }).catch(console.error)
  }, [])

  // ── Toggle task completion ──
  const toggle = (id: string) => {
    const upd = { ...checked, [id]: !checked[id] }
    setChecked(upd)
    api.put('/api/onboarding/progress', { checkedRows: upd }).catch(console.error)
  }

  // ── Phase access control ──
  const isLocked = (idx: number) => {
    if (isAdmin || idx === 0) return false
    const prev = phases[idx - 1]
    return prev ? !prev.rows.every(r => checked[r.id]) : false
  }

  // ── Task editing ──
  const startTaskEdit = (pId: string, tId: string, field: TaskField, val: string) => {
    setEditTask({ pId, tId, field })
    setEditVal(val || '')
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
    const t: Task = { id: rnd(), category: 'New Task', module: 'Click title or description to edit.', url: '' }
    const upd = phases.map(p => {
      if (p.id !== pId) return p
      const rows = [...p.rows]
      afterIdx !== undefined ? rows.splice(afterIdx + 1, 0, t) : rows.push(t)
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

  // ── Learn More helpers ──
  const toggleLM = (taskId: string) =>
    setExpandedLM(prev => { const s = new Set(prev); s.has(taskId) ? s.delete(taskId) : s.add(taskId); return s })

  const saveLMItems = (pId: string, taskId: string, items: LearnMoreItem[]) => {
    const upd = phases.map(p =>
      p.id !== pId ? p : { ...p, rows: p.rows.map(r => r.id !== taskId ? r : { ...r, learnMore: items }) }
    )
    setPhases(upd); savePhases(upd)
  }

  const commitLMEdit = (pId: string) => {
    if (!lmEdit) return
    const currentItems = phases.find(p => p.id === pId)?.rows.find(r => r.id === lmEdit.taskId)?.learnMore || []
    let updated: LearnMoreItem[]
    if (lmEdit.itemId === null) {
      if (!lmEdit.label.trim()) { setLmEdit(null); return }
      updated = [...currentItems, { id: rnd(), type: lmEdit.type, label: lmEdit.label.trim(), ...(lmEdit.type === 'link' && lmEdit.url.trim() ? { url: lmEdit.url.trim() } : {}) }]
    } else {
      updated = currentItems.map(i => i.id !== lmEdit.itemId ? i : { ...i, label: lmEdit.label, ...(lmEdit.type === 'link' ? { url: lmEdit.url || undefined } : { url: undefined }) })
    }
    saveLMItems(pId, lmEdit.taskId, updated)
    setLmEdit(null)
  }

  // ── Phase header editing ──
  const commitPhaseEdit = () => {
    if (!editPhase) return
    const upd = phases.map(p =>
      p.id !== editPhase.pId ? p : { ...p, [editPhase.field]: editPhaseVal }
    )
    setPhases(upd); savePhases(upd); setEditPhase(null)
  }

  const phase = phases[activeTab]
  const acc = ACCENTS[activeTab % ACCENTS.length]

  // ── Render ─────────────────────────────────────────────────────────────────────
  return (
    <div className="h-full overflow-y-auto bg-slate-950 text-white">
      {/* ── Fireworks overlay ── */}
      {fireworks && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 cursor-pointer"
          onClick={() => setFireworks(false)}
        >
          <div className="text-center">
            <div className="text-8xl mb-6 animate-bounce">🎉</div>
            <h2 className="text-4xl font-bold text-yellow-300">All Missions Complete!</h2>
            <p className="text-white/60 mt-3 text-lg">You're fully onboarded. Welcome to the team!</p>
            <p className="text-xs text-white/30 mt-8">Click anywhere to dismiss</p>
          </div>
        </div>
      )}

      {/* ── Mission unlock popup ── */}
      {unlockPopup !== null && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 cursor-pointer"
          onClick={() => setUnlockPopup(null)}
        >
          <div className="bg-slate-800 border border-white/10 rounded-2xl p-10 max-w-sm text-center shadow-2xl">
            <div className="text-6xl mb-4">{ACCENTS[unlockPopup % ACCENTS.length]?.icon}</div>
            <h3 className="text-2xl font-bold text-white mb-2">
              Mission {unlockPopup + 1} Unlocked!
            </h3>
            <p className="text-white/50 text-sm">{phases[unlockPopup]?.title}</p>
            <p className="text-xs text-white/30 mt-8">Click anywhere to continue</p>
          </div>
        </div>
      )}

      <div className="max-w-5xl mx-auto px-6 pt-6 pb-20">
        {/* ── Page header ── */}
        <div className="mb-6">
          {editPageField === 'title' ? (
            <div className="flex items-center gap-2">
              <input
                autoFocus
                className="text-3xl font-bold bg-transparent border-b-2 border-cyan-400 text-white focus:outline-none flex-1"
                value={editPageVal}
                onChange={e => setEditPageVal(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') { setPageTitle(editPageVal); saveSettings(editPageVal, pageSub, tips); setEditPageField(null) }
                  if (e.key === 'Escape') setEditPageField(null)
                }}
              />
              <button onClick={() => { setPageTitle(editPageVal); saveSettings(editPageVal, pageSub, tips); setEditPageField(null) }} className="p-1 text-green-400 hover:bg-green-500/20 rounded"><Check className="w-4 h-4" /></button>
              <button onClick={() => setEditPageField(null)} className="p-1 text-red-400 hover:bg-red-500/20 rounded"><X className="w-4 h-4" /></button>
            </div>
          ) : (
            <h1
              className={`text-3xl font-bold text-white group ${isAdmin ? 'cursor-pointer hover:text-cyan-300 transition-colors' : ''}`}
              onClick={() => isAdmin && (setEditPageVal(pageTitle), setEditPageField('title'))}
            >
              {pageTitle}
              {isAdmin && <Pencil className="w-4 h-4 inline ml-2 opacity-0 group-hover:opacity-50 transition-opacity" />}
            </h1>
          )}
          {editPageField === 'sub' ? (
            <div className="flex items-center gap-2 mt-1">
              <input
                autoFocus
                className="text-sm bg-transparent border-b border-cyan-400 text-cyan-400 focus:outline-none"
                value={editPageVal}
                onChange={e => setEditPageVal(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') { setPageSub(editPageVal); saveSettings(pageTitle, editPageVal, tips); setEditPageField(null) }
                  if (e.key === 'Escape') setEditPageField(null)
                }}
              />
              <button onClick={() => { setPageSub(editPageVal); saveSettings(pageTitle, editPageVal, tips); setEditPageField(null) }} className="p-1 text-green-400 hover:bg-green-500/20 rounded"><Check className="w-3 h-3" /></button>
              <button onClick={() => setEditPageField(null)} className="p-1 text-red-400 hover:bg-red-500/20 rounded"><X className="w-3 h-3" /></button>
            </div>
          ) : (
            <p
              className={`text-sm text-cyan-400 font-medium mt-1 group ${isAdmin ? 'cursor-pointer hover:text-cyan-300' : ''}`}
              onClick={() => isAdmin && (setEditPageVal(pageSub), setEditPageField('sub'))}
            >
              {pageSub}
              {isAdmin && <Pencil className="w-3 h-3 inline ml-1 opacity-0 group-hover:opacity-50 transition-opacity" />}
            </p>
          )}
        </div>

        {/* ── Mission tab bar ── */}
        <div className="flex gap-2 mb-6 overflow-x-auto pb-1 scrollbar-none">
          {phases.map((p, i) => {
            const a = ACCENTS[i % ACCENTS.length]
            const locked = isLocked(i)
            const done = p.rows.filter(r => checked[r.id]).length
            const total = p.rows.length
            return (
              <button
                key={p.id}
                onClick={() => !locked && setActiveTab(i)}
                className={`flex-shrink-0 flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold transition-all whitespace-nowrap ${
                  activeTab === i
                    ? `${a.pill} text-white shadow-lg`
                    : locked
                    ? 'bg-slate-800/40 text-slate-600 cursor-not-allowed'
                    : 'bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700'
                }`}
              >
                {p.title}
                {locked && <Lock className="w-3 h-3 flex-shrink-0" />}
                {!locked && done === total && total > 0 && <Trophy className="w-3 h-3 text-yellow-300 flex-shrink-0" />}
                {!locked && done > 0 && done < total && (
                  <span className="text-[10px] opacity-60">{done}/{total}</span>
                )}
              </button>
            )
          })}
        </div>

        {/* ── Tip cards ── */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
          {tips.map((tip, i) => (
            <div key={i} className="relative group/tip bg-amber-500/10 border border-amber-500/20 rounded-xl p-4 flex items-start gap-3">
              <Lightbulb className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
              {isAdmin && editTipIdx === i ? (
                <div className="flex-1">
                  <textarea
                    autoFocus
                    rows={3}
                    className="w-full bg-slate-800 text-white text-sm border border-amber-400/40 rounded px-2 py-1 focus:outline-none resize-none"
                    value={editTipVal}
                    onChange={e => setEditTipVal(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        const upd = tips.map((t, j) => j === i ? editTipVal : t)
                        setTips(upd); saveSettings(pageTitle, pageSub, upd); setEditTipIdx(null)
                      }
                      if (e.key === 'Escape') setEditTipIdx(null)
                    }}
                  />
                  <div className="flex gap-1 mt-1">
                    <button onClick={() => { const upd = tips.map((t, j) => j === i ? editTipVal : t); setTips(upd); saveSettings(pageTitle, pageSub, upd); setEditTipIdx(null) }} className="p-0.5 text-green-400 hover:bg-green-500/20 rounded"><Check className="w-3 h-3" /></button>
                    <button onClick={() => setEditTipIdx(null)} className="p-0.5 text-red-400 hover:bg-red-500/20 rounded"><X className="w-3 h-3" /></button>
                  </div>
                </div>
              ) : (
                <p
                  className={`text-sm text-amber-200/80 leading-relaxed ${isAdmin ? 'cursor-pointer hover:text-amber-100' : ''}`}
                  onClick={() => isAdmin && (setEditTipVal(tip), setEditTipIdx(i))}
                >
                  {tip}
                </p>
              )}
              {isAdmin && editTipIdx !== i && (
                <button
                  onClick={() => { const upd = tips.filter((_, j) => j !== i); setTips(upd); saveSettings(pageTitle, pageSub, upd) }}
                  className="absolute top-2 right-2 opacity-0 group-hover/tip:opacity-100 p-1 text-red-400 hover:bg-red-500/20 rounded transition-opacity"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>
          ))}
          {isAdmin && (
            <button
              onClick={() => { const upd = [...tips, 'New tip — click to edit.']; setTips(upd); saveSettings(pageTitle, pageSub, upd) }}
              className="border border-dashed border-slate-700 rounded-xl p-4 flex items-center justify-center gap-2 text-slate-500 hover:text-white hover:border-slate-500 transition-all text-sm"
            >
              <Plus className="w-4 h-4" /> Add tip
            </button>
          )}
        </div>

        {/* ── Admin hint bar ── */}
        {isAdmin && (
          <div className="bg-slate-800/40 border border-slate-700/30 rounded-lg px-4 py-2 mb-6 text-xs text-slate-400">
            Admin mode — click any card title or description to edit inline.{' '}
            Use <span className="text-green-400 font-bold">+</span> to add or{' '}
            <span className="text-red-400 font-bold">×</span> to remove tasks.
          </div>
        )}

        {/* ── Active phase ── */}
        {phase && (() => {
          const locked = isLocked(activeTab)
          const total = phase.rows.length
          const done = phase.rows.filter(r => checked[r.id]).length
          const pct = total === 0 ? 0 : Math.round((done / total) * 100)

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
                <div className="w-14 h-14 rounded-full bg-black/25 flex items-center justify-center text-3xl flex-shrink-0 border border-white/20">
                  {acc.icon}
                </div>
                <div className="flex-1 min-w-0">
                  {/* Phase title */}
                  {isAdmin && editPhase?.pId === phase.id && editPhase.field === 'title' ? (
                    <div className="flex items-center gap-2 mb-1">
                      <input autoFocus className="bg-white/20 text-white text-xl font-bold border border-white/40 rounded px-2 py-0.5 focus:outline-none flex-1" value={editPhaseVal} onChange={e => setEditPhaseVal(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') commitPhaseEdit(); if (e.key === 'Escape') setEditPhase(null) }} />
                      <button onClick={commitPhaseEdit} className="p-1 text-white/80 hover:bg-white/20 rounded"><Check className="w-4 h-4" /></button>
                      <button onClick={() => setEditPhase(null)} className="p-1 text-white/50 hover:bg-white/20 rounded"><X className="w-4 h-4" /></button>
                    </div>
                  ) : (
                    <h2
                      className={`text-xl font-bold text-white mb-1 group/pt ${isAdmin ? 'cursor-pointer hover:text-white/80' : ''}`}
                      onClick={() => isAdmin && (setEditPhaseVal(phase.title), setEditPhase({ pId: phase.id, field: 'title' }))}
                    >
                      {phase.title}
                      {isAdmin && <Pencil className="w-3 h-3 inline ml-1.5 opacity-0 group-hover/pt:opacity-60" />}
                    </h2>
                  )}
                  {/* Phase objective */}
                  {isAdmin && editPhase?.pId === phase.id && editPhase.field === 'objective' ? (
                    <div className="flex items-center gap-2">
                      <input autoFocus className="bg-white/20 text-white/80 text-sm border border-white/40 rounded px-2 py-0.5 focus:outline-none flex-1" value={editPhaseVal} onChange={e => setEditPhaseVal(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') commitPhaseEdit(); if (e.key === 'Escape') setEditPhase(null) }} />
                      <button onClick={commitPhaseEdit} className="p-1 text-white/80 hover:bg-white/20 rounded"><Check className="w-3 h-3" /></button>
                      <button onClick={() => setEditPhase(null)} className="p-1 text-white/50 hover:bg-white/20 rounded"><X className="w-3 h-3" /></button>
                    </div>
                  ) : (
                    <p
                      className={`text-white/70 text-sm group/po ${isAdmin ? 'cursor-pointer hover:text-white/90' : ''}`}
                      onClick={() => isAdmin && (setEditPhaseVal(phase.objective), setEditPhase({ pId: phase.id, field: 'objective' }))}
                    >
                      {phase.objective}
                      {isAdmin && <Pencil className="w-3 h-3 inline ml-1 opacity-0 group-hover/po:opacity-60" />}
                    </p>
                  )}
                  {/* Progress */}
                  <div className="mt-3">
                    <div className="flex justify-between text-xs text-white/60 mb-1.5">
                      <span>{done}/{total} complete</span>
                      <span className="font-bold text-white/80">{pct}%</span>
                    </div>
                    <div className="h-1.5 bg-white/20 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-white/80 rounded-full transition-all duration-700 ease-out"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* ── Alternating timeline ── */}
              <div className="relative">
                {/* Center dashed line */}
                <div className="hidden sm:block absolute left-1/2 top-4 bottom-4 -translate-x-1/2 w-px border-l-2 border-dashed border-slate-700/60" />

                <div className="space-y-6">
                  {phase.rows.map((task, idx) => {
                    const isRight = idx % 2 === 0
                    const isDone = !!checked[task.id]
                    const isEditingTitle = editTask?.pId === phase.id && editTask.tId === task.id && editTask.field === 'category'
                    const isEditingDesc = editTask?.pId === phase.id && editTask.tId === task.id && editTask.field === 'module'

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
                          <h3
                            className={`font-semibold text-sm mb-2 leading-snug ${isDone ? 'text-slate-400 line-through' : 'text-white'} ${isAdmin ? 'cursor-pointer hover:text-cyan-300 transition-colors' : ''}`}
                            onClick={() => isAdmin && startTaskEdit(phase.id, task.id, 'category', task.category)}
                          >
                            {task.category}
                          </h3>
                        )}

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
                          <p
                            className={`text-xs leading-relaxed mb-3 ${isDone ? 'text-slate-500' : 'text-slate-400'} ${isAdmin ? 'cursor-pointer hover:text-slate-200 transition-colors' : ''}`}
                            onClick={() => isAdmin && startTaskEdit(phase.id, task.id, 'module', task.module)}
                          >
                            {task.module}
                          </p>
                        )}

                        {/* ── Action row ── */}
                        <div className="flex items-center gap-2 flex-wrap">
                          {/* Learn More toggle */}
                          {(() => {
                            const lmItems = task.learnMore || []
                            const hasContent = lmItems.length > 0 || !!task.url
                            const isOpen = expandedLM.has(task.id)
                            if (!hasContent && !isAdmin) {
                              return (
                                <span className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700/50 text-slate-500 text-xs font-semibold rounded-lg cursor-default border border-slate-700">
                                  Learn More
                                </span>
                              )
                            }
                            return (
                              <button
                                onClick={() => toggleLM(task.id)}
                                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors border ${
                                  isOpen
                                    ? 'bg-blue-600 text-white border-blue-500'
                                    : hasContent
                                    ? 'bg-blue-600/20 text-blue-300 border-blue-500/40 hover:bg-blue-600/40'
                                    : 'bg-blue-600/10 text-blue-400/60 border-dashed border-blue-500/30 hover:bg-blue-600/20 hover:text-blue-300'
                                }`}
                              >
                                Learn More
                                <ChevronDown className={`w-3 h-3 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
                              </button>
                            )
                          })()}

                          <button
                            onClick={() => toggle(task.id)}
                            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg transition-all border ${
                              isDone
                                ? 'bg-green-600/25 text-green-400 border-green-500/40 hover:bg-green-600/35'
                                : 'bg-slate-700 text-slate-300 border-slate-600 hover:bg-slate-600 hover:text-white'
                            }`}
                          >
                            {isDone ? (
                              <><Check className="w-3 h-3" /> Completed</>
                            ) : (
                              <>Mark Complete</>
                            )}
                          </button>

                          {isAdmin && (
                            <>
                              <button
                                onClick={() => addTask(phase.id, idx)}
                                className="p-1.5 text-slate-500 hover:text-green-400 hover:bg-green-500/10 rounded-lg transition-colors"
                                title="Add task after this one"
                              >
                                <Plus className="w-3.5 h-3.5" />
                              </button>
                              <button
                                onClick={() => deleteTask(phase.id, task.id)}
                                className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                                title="Delete task"
                              >
                                <X className="w-3.5 h-3.5" />
                              </button>
                            </>
                          )}
                        </div>

                        {/* ── Learn More expandable panel ── */}
                        {expandedLM.has(task.id) && (
                          <div className="mt-3 pt-3 border-t border-slate-700/50">
                            <ul className="space-y-2 mb-2">
                              {/* Legacy single-url backward compat */}
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
                                if (isEditingItem) {
                                  return (
                                    <li key={item.id} className="bg-slate-700/50 rounded-lg p-2">
                                      <div className="flex flex-col gap-1.5">
                                        <input autoFocus placeholder="Label / Text" className="w-full bg-slate-700 text-white text-xs border border-cyan-400/50 rounded px-2 py-1 focus:outline-none" value={lmEdit.label} onChange={e => setLmEdit({ ...lmEdit, label: e.target.value })} onKeyDown={e => { if (e.key === 'Escape') setLmEdit(null) }} />
                                        {lmEdit.type === 'link' && (
                                          <input placeholder="https://..." className="w-full bg-slate-700 text-slate-300 text-xs border border-cyan-400/50 rounded px-2 py-1 focus:outline-none" value={lmEdit.url} onChange={e => setLmEdit({ ...lmEdit, url: e.target.value })} onKeyDown={e => { if (e.key === 'Enter') commitLMEdit(phase.id); if (e.key === 'Escape') setLmEdit(null) }} />
                                        )}
                                        <div className="flex gap-1">
                                          <button onClick={() => commitLMEdit(phase.id)} className="p-0.5 text-green-400 hover:bg-green-500/20 rounded"><Check className="w-3 h-3" /></button>
                                          <button onClick={() => setLmEdit(null)} className="p-0.5 text-red-400 hover:bg-red-500/20 rounded"><X className="w-3 h-3" /></button>
                                        </div>
                                      </div>
                                    </li>
                                  )
                                }
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
                                    {isAdmin && (
                                      <div className="flex gap-0.5 opacity-0 group-hover/lmi:opacity-100 transition-opacity flex-shrink-0">
                                        <button onClick={() => setLmEdit({ pId: phase.id, taskId: task.id, itemId: item.id, type: item.type, label: item.label, url: item.url || '' })} className="p-0.5 text-slate-400 hover:text-cyan-400 hover:bg-cyan-500/10 rounded"><Pencil className="w-3 h-3" /></button>
                                        <button onClick={() => saveLMItems(phase.id, task.id, (task.learnMore || []).filter(i => i.id !== item.id))} className="p-0.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded"><X className="w-3 h-3" /></button>
                                      </div>
                                    )}
                                  </li>
                                )
                              })}
                            </ul>

                            {/* New item form */}
                            {isAdmin && lmEdit?.taskId === task.id && lmEdit.itemId === null && (
                              <div className="bg-slate-700/50 rounded-lg p-2 mb-2">
                                <div className="flex flex-col gap-1.5">
                                  <input autoFocus placeholder={lmEdit.type === 'link' ? 'Link label...' : 'Instruction text...'} className="w-full bg-slate-700 text-white text-xs border border-cyan-400/50 rounded px-2 py-1 focus:outline-none" value={lmEdit.label} onChange={e => setLmEdit({ ...lmEdit, label: e.target.value })} onKeyDown={e => { if (e.key === 'Escape') setLmEdit(null) }} />
                                  {lmEdit.type === 'link' && (
                                    <input placeholder="https://..." className="w-full bg-slate-700 text-slate-300 text-xs border border-cyan-400/50 rounded px-2 py-1 focus:outline-none" value={lmEdit.url} onChange={e => setLmEdit({ ...lmEdit, url: e.target.value })} onKeyDown={e => { if (e.key === 'Enter') commitLMEdit(phase.id); if (e.key === 'Escape') setLmEdit(null) }} />
                                  )}
                                  <div className="flex gap-1">
                                    <button onClick={() => commitLMEdit(phase.id)} className="p-0.5 text-green-400 hover:bg-green-500/20 rounded"><Check className="w-3 h-3" /></button>
                                    <button onClick={() => setLmEdit(null)} className="p-0.5 text-red-400 hover:bg-red-500/20 rounded"><X className="w-3 h-3" /></button>
                                  </div>
                                </div>
                              </div>
                            )}

                            {/* Admin add buttons */}
                            {isAdmin && !(lmEdit?.taskId === task.id) && (
                              <div className="flex gap-1.5">
                                <button onClick={() => setLmEdit({ pId: phase.id, taskId: task.id, itemId: null, type: 'text', label: '', url: '' })} className="flex items-center gap-1 px-2 py-1 text-xs text-slate-400 hover:text-white border border-dashed border-slate-600 hover:border-slate-400 rounded-lg transition-colors">
                                  <Plus className="w-3 h-3" /> Add Text
                                </button>
                                <button onClick={() => setLmEdit({ pId: phase.id, taskId: task.id, itemId: null, type: 'link', label: '', url: '' })} className="flex items-center gap-1 px-2 py-1 text-xs text-slate-400 hover:text-white border border-dashed border-slate-600 hover:border-slate-400 rounded-lg transition-colors">
                                  <ExternalLink className="w-3 h-3" /> Add Link
                                </button>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )

                    // ── Mobile: single column; Desktop: alternating left/right ──
                    return (
                      <div key={task.id} className="relative flex items-start sm:items-center">
                        {/* Left side (desktop) */}
                        <div className="hidden sm:block sm:w-[calc(50%-24px)] sm:pr-5">
                          {!isRight && card}
                        </div>

                        {/* Center dot */}
                        <div className="hidden sm:flex w-12 justify-center flex-shrink-0 z-10">
                          <div
                            className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all duration-300 cursor-pointer ${
                              isDone
                                ? `${acc.dot} border-transparent text-white shadow-lg ${acc.dotGlow}`
                                : 'bg-slate-900 border-slate-600 text-slate-400 hover:border-slate-400'
                            }`}
                            onClick={() => toggle(task.id)}
                            title={isDone ? 'Mark incomplete' : 'Mark complete'}
                          >
                            {isDone ? <Check className="w-4 h-4" strokeWidth={3} /> : idx + 1}
                          </div>
                        </div>

                        {/* Right side (desktop) */}
                        <div className="hidden sm:block sm:w-[calc(50%-24px)] sm:pl-5">
                          {isRight && card}
                        </div>

                        {/* Mobile: always full width with number badge */}
                        <div className="flex sm:hidden w-full gap-3">
                          <div
                            className={`w-7 h-7 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold border-2 transition-all mt-1 cursor-pointer ${
                              isDone
                                ? `${acc.dot} border-transparent text-white`
                                : 'bg-slate-900 border-slate-600 text-slate-400'
                            }`}
                            onClick={() => toggle(task.id)}
                          >
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
              {isAdmin && (
                <div className="flex justify-center mt-10">
                  <button
                    onClick={() => addTask(phase.id)}
                    className="flex items-center gap-2 px-5 py-2.5 border border-dashed border-slate-700 rounded-xl text-sm text-slate-500 hover:text-white hover:border-slate-500 transition-all"
                  >
                    <Plus className="w-4 h-4" />
                    Add task to {phase.title}
                  </button>
                </div>
              )}
            </>
          )
        })()}
      </div>
    </div>
  )
}
