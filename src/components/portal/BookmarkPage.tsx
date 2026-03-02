'use client'

import { useState, useEffect, useMemo, useRef } from 'react'
import {
  Bookmark as BookmarkIcon,
  Plus,
  Trash2,
  ExternalLink,
  Tag,
  FolderPlus,
  Loader2,
  AlertCircle,
  Search,
  ChevronDown,
  X,
  Edit2,
  Check,
  LayoutGrid,
  List,
  AlignJustify,
  Grid2X2,
  Calendar,
  Link2,
  Download,
  Upload,
  FileWarning,
  Layers,
  FolderOpen,
} from 'lucide-react'
import api from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Category {
  id: number
  name: string
  description: string | null
  created_at: string
}

interface Bookmark {
  id: number
  name: string
  description: string | null
  url: string
  category_id: number | null
  category: Category | null
  created_at: string
  updated_at: string
}

type SortOption = 'name_asc' | 'name_desc' | 'category' | 'date_desc' | 'date_asc'
type ViewMode = 'tiles' | 'large' | 'list' | 'compact' | 'category'

const SORT_LABELS: Record<SortOption, string> = {
  name_asc: 'Name A → Z',
  name_desc: 'Name Z → A',
  category: 'By Category',
  date_desc: 'Newest First',
  date_asc: 'Oldest First',
}

const VIEW_OPTIONS: { mode: ViewMode; icon: React.ReactNode; label: string }[] = [
  { mode: 'tiles',    icon: <LayoutGrid className="w-4 h-4" />,    label: 'Tiles'    },
  { mode: 'large',    icon: <Grid2X2 className="w-4 h-4" />,       label: 'Large'    },
  { mode: 'list',     icon: <List className="w-4 h-4" />,          label: 'List'     },
  { mode: 'compact',  icon: <AlignJustify className="w-4 h-4" />,  label: 'Compact'  },
  { mode: 'category', icon: <Layers className="w-4 h-4" />,        label: 'Category' },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

// ─── CSV helpers ─────────────────────────────────────────────────────────────

function csvEscape(val: string) {
  return `"${val.replace(/"/g, '""')}"`
}

function parseCSVLine(line: string): string[] {
  const result: string[] = []
  let current = ''
  let quoted = false
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (ch === '"') {
      if (quoted && line[i + 1] === '"') { current += '"'; i++ }
      else { quoted = !quoted }
    } else if (ch === ',' && !quoted) {
      result.push(current.trim())
      current = ''
    } else {
      current += ch
    }
  }
  result.push(current.trim())
  return result
}

function hostname(url: string) {
  try { return new URL(url).hostname.replace(/^www\./, '') } catch { return url }
}

const CAT_COLORS = [
  'bg-cyan-500/15 text-cyan-400 border-cyan-500/30',
  'bg-blue-500/15 text-blue-400 border-blue-500/30',
  'bg-violet-500/15 text-violet-400 border-violet-500/30',
  'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  'bg-amber-500/15 text-amber-400 border-amber-500/30',
  'bg-rose-500/15 text-rose-400 border-rose-500/30',
  'bg-pink-500/15 text-pink-400 border-pink-500/30',
  'bg-teal-500/15 text-teal-400 border-teal-500/30',
]
function catColor(name: string) {
  let h = 0; for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0
  return CAT_COLORS[h % CAT_COLORS.length]
}

function catTextColor(name: string) {
  return catColor(name).split(' ').find((c) => c.startsWith('text-')) ?? 'text-cyan-400'
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function CategoryBadge({ name }: { name: string }) {
  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full border ${catColor(name)}`}>
      <Tag className="w-2.5 h-2.5" />{name}
    </span>
  )
}

function UncatBadge() {
  return (
    <span className="inline-flex items-center bg-slate-700/60 text-gray-500 text-[10px] px-2 py-0.5 rounded-full border border-slate-600/40">
      Uncategorized
    </span>
  )
}

function InlineEditForm({
  editName, setEditName, editDesc, setEditDesc, editUrl, setEditUrl,
  editCategoryId, setEditCategoryId, categories, savingEdit, onSave, onCancel, className = '',
}: {
  editName: string; setEditName: (v: string) => void
  editDesc: string; setEditDesc: (v: string) => void
  editUrl: string; setEditUrl: (v: string) => void
  editCategoryId: number | ''; setEditCategoryId: (v: number | '') => void
  categories: Category[]; savingEdit: boolean
  onSave: () => void; onCancel: () => void; className?: string
}) {
  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      <input className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
        value={editName} onChange={(e) => setEditName(e.target.value)} placeholder="Name" />
      <input className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
        value={editDesc} onChange={(e) => setEditDesc(e.target.value)} placeholder="Description (optional)" />
      <input className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-500"
        value={editUrl} onChange={(e) => setEditUrl(e.target.value)} placeholder="https://…" />
      <select value={editCategoryId} onChange={(e) => setEditCategoryId(e.target.value === '' ? '' : Number(e.target.value))}
        className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-gray-300 focus:outline-none focus:border-cyan-500">
        <option value="">No category</option>
        {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>
      <div className="flex gap-2 mt-1">
        <button onClick={onSave} disabled={savingEdit}
          className="flex-1 flex items-center justify-center gap-1 py-1.5 text-xs bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors disabled:opacity-50">
          {savingEdit ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />} Save
        </button>
        <button onClick={onCancel} className="flex-1 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 text-gray-300 rounded-lg transition-colors">
          Cancel
        </button>
      </div>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function BookmarkPage() {
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'admin'

  const [bookmarks, setBookmarks] = useState<Bookmark[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [viewMode, setViewMode] = useState<ViewMode>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('bookmark_viewMode')
      if (saved && ['tiles', 'large', 'list', 'compact', 'category'].includes(saved)) return saved as ViewMode
    }
    return 'tiles'
  })
  const [searchTerm, setSearchTerm] = useState('')
  const [filterCategoryId, setFilterCategoryId] = useState<number | 'all'>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('bookmark_filterCategory')
      if (saved && saved !== 'all') return Number(saved)
    }
    return 'all'
  })
  const [sortBy, setSortBy] = useState<SortOption>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('bookmark_sortBy')
      if (saved && ['name_asc', 'name_desc', 'category', 'date_desc', 'date_asc'].includes(saved)) return saved as SortOption
    }
    return 'date_desc'
  })

  const [showAddBookmark, setShowAddBookmark] = useState(false)
  const [bName, setBName] = useState('')
  const [bDesc, setBDesc] = useState('')
  const [bUrl, setBUrl] = useState('')
  const [bCategoryId, setBCategoryId] = useState<number | ''>('')
  const [savingBookmark, setSavingBookmark] = useState(false)
  const [bookmarkError, setBookmarkError] = useState<string | null>(null)

  const [editingId, setEditingId] = useState<number | null>(null)
  const [editName, setEditName] = useState('')
  const [editDesc, setEditDesc] = useState('')
  const [editUrl, setEditUrl] = useState('')
  const [editCategoryId, setEditCategoryId] = useState<number | ''>('')
  const [savingEdit, setSavingEdit] = useState(false)

  const [showAddCategory, setShowAddCategory] = useState(false)
  const [catName, setCatName] = useState('')
  const [catDesc, setCatDesc] = useState('')
  const [savingCategory, setSavingCategory] = useState(false)
  const [categoryError, setCategoryError] = useState<string | null>(null)

  const [deletingBookmarkId, setDeletingBookmarkId] = useState<number | null>(null)
  const [deletingCategoryId, setDeletingCategoryId] = useState<number | null>(null)

  const [editingCategoryId, setEditingCategoryId] = useState<number | null>(null)
  const [editCatName, setEditCatName] = useState('')
  const [editCatDesc, setEditCatDesc] = useState('')
  const [savingCatEdit, setSavingCatEdit] = useState(false)
  const [showCategoryPanel, setShowCategoryPanel] = useState(false)

  const [importing, setImporting] = useState(false)
  const [importError, setImportError] = useState<string | null>(null)
  const [importSummary, setImportSummary] = useState<{ created: number; failed: number; errors: string[] } | null>(null)
  const importInputRef = useRef<HTMLInputElement>(null)

  // ── Fetch ──────────────────────────────────────────────────────────────────

  const fetchAll = async () => {
    try {
      setLoading(true); setError(null)
      const [bmRes, catRes] = await Promise.all([
        api.get(`/api/bookmarks?sort=${sortBy}${filterCategoryId !== 'all' ? `&category_id=${filterCategoryId}` : ''}`),
        api.get('/api/bookmarks/categories'),
      ])
      setBookmarks(bmRes.data); setCategories(catRes.data)
    } catch (err: any) { setError(err.response?.data?.detail || 'Failed to load bookmarks') }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchAll() }, [sortBy, filterCategoryId])

  // Persist user preferences to localStorage
  useEffect(() => { localStorage.setItem('bookmark_viewMode', viewMode) }, [viewMode])
  useEffect(() => { localStorage.setItem('bookmark_sortBy', sortBy) }, [sortBy])
  useEffect(() => { localStorage.setItem('bookmark_filterCategory', String(filterCategoryId)) }, [filterCategoryId])

  const filtered = useMemo(() => {
    if (!searchTerm.trim()) return bookmarks
    const term = searchTerm.toLowerCase()
    return bookmarks.filter(
      (b) => b.name.toLowerCase().includes(term) || b.description?.toLowerCase().includes(term) ||
        b.url.toLowerCase().includes(term) || b.category?.name.toLowerCase().includes(term)
    )
  }, [bookmarks, searchTerm])

  // ── CRUD ───────────────────────────────────────────────────────────────────

  const handleAddBookmark = async () => {
    if (!bName.trim() || !bUrl.trim()) { setBookmarkError('Name and URL are required'); return }
    try {
      setSavingBookmark(true); setBookmarkError(null)
      await api.post('/api/bookmarks', { name: bName.trim(), description: bDesc.trim() || null, url: bUrl.trim(), category_id: bCategoryId !== '' ? bCategoryId : null })
      setBName(''); setBDesc(''); setBUrl(''); setBCategoryId(''); setShowAddBookmark(false); fetchAll()
    } catch (err: any) { setBookmarkError(err.response?.data?.detail || 'Failed to add bookmark') }
    finally { setSavingBookmark(false) }
  }

  const startEdit = (b: Bookmark) => { setEditingId(b.id); setEditName(b.name); setEditDesc(b.description || ''); setEditUrl(b.url); setEditCategoryId(b.category_id ?? '') }
  const cancelEdit = () => setEditingId(null)

  const saveEdit = async (id: number) => {
    if (!editName.trim() || !editUrl.trim()) return
    try {
      setSavingEdit(true)
      await api.put(`/api/bookmarks/${id}`, { name: editName.trim(), description: editDesc.trim() || null, url: editUrl.trim(), category_id: editCategoryId !== '' ? editCategoryId : null })
      setEditingId(null); fetchAll()
    } catch (err: any) { alert(err.response?.data?.detail || 'Failed to update bookmark') }
    finally { setSavingEdit(false) }
  }

  const deleteBookmark = async (id: number) => {
    if (!confirm('Delete this bookmark?')) return
    try { setDeletingBookmarkId(id); await api.delete(`/api/bookmarks/${id}`); setBookmarks((prev) => prev.filter((b) => b.id !== id)) }
    catch (err: any) { alert(err.response?.data?.detail || 'Failed to delete bookmark') }
    finally { setDeletingBookmarkId(null) }
  }

  const handleAddCategory = async () => {
    if (!catName.trim()) { setCategoryError('Category name is required'); return }
    try {
      setSavingCategory(true); setCategoryError(null)
      await api.post('/api/bookmarks/categories', { name: catName.trim(), description: catDesc.trim() || null })
      setCatName(''); setCatDesc(''); setShowAddCategory(false); fetchAll()
    } catch (err: any) { setCategoryError(err.response?.data?.detail || 'Failed to add category') }
    finally { setSavingCategory(false) }
  }

  const deleteCategory = async (id: number, name: string) => {
    if (!confirm(`Delete category "${name}"? Bookmarks inside will become uncategorized.`)) return
    try { setDeletingCategoryId(id); await api.delete(`/api/bookmarks/categories/${id}`); if (filterCategoryId === id) setFilterCategoryId('all'); fetchAll() }
    catch (err: any) { alert(err.response?.data?.detail || 'Failed to delete category') }
    finally { setDeletingCategoryId(null) }
  }

  const startEditCategory = (cat: Category) => {
    setEditingCategoryId(cat.id)
    setEditCatName(cat.name)
    setEditCatDesc(cat.description || '')
  }
  const cancelEditCategory = () => setEditingCategoryId(null)
  const saveEditCategory = async () => {
    if (!editCatName.trim() || editingCategoryId === null) return
    try {
      setSavingCatEdit(true)
      await api.put(`/api/bookmarks/categories/${editingCategoryId}`, { name: editCatName.trim(), description: editCatDesc.trim() || null })
      setEditingCategoryId(null)
      fetchAll()
    } catch (err: any) { alert(err.response?.data?.detail || 'Failed to rename category') }
    finally { setSavingCatEdit(false) }
  }

  // ── Shared helpers ─────────────────────────────────────────────────────────

  // ── CSV Export ─────────────────────────────────────────────────────────────

  const handleExport = () => {
    const header = ['name', 'description', 'url', 'category']
    const rows = bookmarks.map((b) => [
      csvEscape(b.name),
      csvEscape(b.description || ''),
      csvEscape(b.url),
      csvEscape(b.category?.name || ''),
    ])
    const csv = [header.map(csvEscape), ...rows].map((r) => r.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `bookmarks_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // ── CSV Import ─────────────────────────────────────────────────────────────

  const handleImportFile = async (file: File) => {
    setImporting(true)
    setImportError(null)
    setImportSummary(null)
    try {
      const text = await file.text()
      const lines = text.split(/\r?\n/).filter((l) => l.trim())
      if (lines.length < 2) throw new Error('CSV must have a header row and at least one data row')
      const dataLines = lines.slice(1)

      // Build local category name→id map; create unknown categories on-the-fly
      const catMap: Record<string, number> = {}
      // Refresh categories before import
      const catRes = await api.get('/api/bookmarks/categories')
      const freshCats: Category[] = catRes.data
      freshCats.forEach((c) => { catMap[c.name.toLowerCase()] = c.id })

      let created = 0
      let failed = 0
      const errors: string[] = []

      for (let i = 0; i < dataLines.length; i++) {
        const row = parseCSVLine(dataLines[i])
        if (row.length < 3) { failed++; errors.push(`Row ${i + 2}: too few columns`); continue }
        const [name, description, url, categoryName] = row
        if (!name || !url) { failed++; errors.push(`Row ${i + 2}: name and URL are required`); continue }

        let categoryId: number | null = null
        if (categoryName) {
          const key = categoryName.toLowerCase()
          if (catMap[key] !== undefined) {
            categoryId = catMap[key]
          } else {
            try {
              const res = await api.post('/api/bookmarks/categories', { name: categoryName, description: null })
              catMap[key] = res.data.id
              categoryId = res.data.id
            } catch {
              // category may already exist with different casing — try to find it
              const match = freshCats.find((c) => c.name.toLowerCase() === key)
              if (match) { catMap[key] = match.id; categoryId = match.id }
            }
          }
        }

        try {
          await api.post('/api/bookmarks', {
            name: name.trim(),
            description: description?.trim() || null,
            url: url.trim(),
            category_id: categoryId,
          })
          created++
        } catch (err: any) {
          failed++
          errors.push(`Row ${i + 2} "${name}": ${err.response?.data?.detail || 'failed'}`)
        }
      }

      setImportSummary({ created, failed, errors: errors.slice(0, 8) })
      fetchAll()
    } catch (err: any) {
      setImportError(err.message || 'Failed to import CSV')
    } finally {
      setImporting(false)
      if (importInputRef.current) importInputRef.current.value = ''
    }
  }

  const openLink = (e: React.MouseEvent, url: string) => {
    if ((e.target as HTMLElement).closest('[data-admin-action]')) return
    window.open(url, '_blank', 'noopener,noreferrer')
  }

  const AdminActions = ({ b }: { b: Bookmark }) => isAdmin ? (
    <div data-admin-action className="flex items-center gap-1 shrink-0">
      <button data-admin-action onClick={(e) => { e.stopPropagation(); startEdit(b) }}
        className="flex items-center gap-1 px-2 py-1 text-[10px] bg-slate-700 hover:bg-cyan-600/30 hover:text-cyan-400 text-gray-400 rounded transition-colors">
        <Edit2 className="w-3 h-3" /> Edit
      </button>
      <button data-admin-action onClick={(e) => { e.stopPropagation(); deleteBookmark(b.id) }} disabled={deletingBookmarkId === b.id}
        className="flex items-center gap-1 px-2 py-1 text-[10px] bg-slate-700 hover:bg-red-500/20 hover:text-red-400 text-gray-400 rounded transition-colors disabled:opacity-50">
        {deletingBookmarkId === b.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <Trash2 className="w-3 h-3" />} Delete
      </button>
    </div>
  ) : null

  // ── View renderers ─────────────────────────────────────────────────────────

  const renderTiles = (cols: string) => (
    <div className={`grid ${cols} gap-4`}>
      {filtered.map((b) =>
        editingId === b.id ? (
          <div key={b.id} className="bg-slate-800 border border-cyan-500/40 rounded-xl p-4">
            <InlineEditForm {...{ editName, setEditName, editDesc, setEditDesc, editUrl, setEditUrl, editCategoryId, setEditCategoryId, categories, savingEdit }}
              onSave={() => saveEdit(b.id)} onCancel={cancelEdit} />
          </div>
        ) : (
          <div key={b.id}
            className="group relative bg-slate-800/70 hover:bg-slate-800 border border-slate-700/50 hover:border-cyan-500/40 rounded-xl p-4 flex flex-col justify-between transition-all duration-200 cursor-pointer"
            onClick={(e) => openLink(e, b.url)}>
            <div className="mb-2">{b.category ? <CategoryBadge name={b.category.name} /> : <UncatBadge />}</div>
            <div className="flex items-start justify-between gap-2 mb-1">
              <h3 className="text-sm font-semibold text-white leading-snug break-words flex-1">{b.name}</h3>
              <ExternalLink className="w-4 h-4 text-gray-500 group-hover:text-cyan-400 transition-colors flex-shrink-0 mt-0.5" />
            </div>
            {b.description && <p className="text-xs text-gray-400 line-clamp-2 mb-1">{b.description}</p>}
            <div className="mt-auto">
              <p className="text-[10px] text-gray-600 truncate mt-1">{hostname(b.url)}</p>
              <p className="text-[10px] text-gray-600 mt-0.5 flex items-center gap-1"><Calendar className="w-2.5 h-2.5" />{formatDate(b.created_at)}</p>
            </div>
            {isAdmin && (
              <div data-admin-action className="flex items-center gap-1 mt-3 pt-2 border-t border-slate-700/50 opacity-0 group-hover:opacity-100 transition-opacity">
                <AdminActions b={b} />
              </div>
            )}
          </div>
        )
      )}
    </div>
  )

  const renderList = () => (
    <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl overflow-hidden divide-y divide-slate-700/50">
      {/* Header row */}
      <div className="hidden md:flex items-center gap-4 px-4 py-2 bg-slate-800/60">
        <div className="w-8 flex-shrink-0" />
        <span className="flex-1 text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Name</span>
        <span className="w-36 flex-shrink-0 text-[10px] font-semibold text-gray-500 uppercase tracking-wider hidden sm:block">Category</span>
        <span className="w-28 flex-shrink-0 text-[10px] font-semibold text-gray-500 uppercase tracking-wider hidden md:block">Added</span>
        {isAdmin && <span className="w-24 flex-shrink-0" />}
      </div>
      {filtered.map((b) =>
        editingId === b.id ? (
          <div key={b.id} className="p-4 bg-slate-800 border-l-2 border-cyan-500">
            <InlineEditForm {...{ editName, setEditName, editDesc, setEditDesc, editUrl, setEditUrl, editCategoryId, setEditCategoryId, categories, savingEdit }}
              onSave={() => saveEdit(b.id)} onCancel={cancelEdit} />
          </div>
        ) : (
          <div key={b.id}
            className="group flex items-center gap-4 px-4 py-3 hover:bg-slate-700/40 cursor-pointer transition-colors"
            onClick={(e) => openLink(e, b.url)}>
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/20 flex items-center justify-center flex-shrink-0">
              <Link2 className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-white truncate">{b.name}</span>
                <ExternalLink className="w-3.5 h-3.5 text-gray-600 group-hover:text-cyan-400 transition-colors flex-shrink-0" />
              </div>
              {b.description && <p className="text-xs text-gray-500 truncate mt-0.5">{b.description}</p>}
              <p className="text-[10px] text-gray-600 truncate mt-0.5">{hostname(b.url)}</p>
            </div>
            <div className="hidden sm:block w-36 flex-shrink-0">{b.category ? <CategoryBadge name={b.category.name} /> : <UncatBadge />}</div>
            <div className="hidden md:flex items-center gap-1 text-[10px] text-gray-500 flex-shrink-0 w-28">
              <Calendar className="w-3 h-3" />{formatDate(b.created_at)}
            </div>
            <div data-admin-action className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
              <AdminActions b={b} />
            </div>
          </div>
        )
      )}
    </div>
  )

  const renderGrouped = () => {
    // Group filtered bookmarks by category
    const groups: { catName: string; catId: number | null; color: string; items: Bookmark[] }[] = []
    const seen: Record<string, number> = {}

    filtered.forEach((b) => {
      const key = b.category ? String(b.category.id) : '__uncat__'
      if (seen[key] === undefined) {
        seen[key] = groups.length
        groups.push({
          catName: b.category?.name || 'Uncategorized',
          catId: b.category?.id ?? null,
          color: b.category ? catColor(b.category.name) : 'bg-slate-700/40 text-gray-500 border-slate-600/40',
          items: [],
        })
      }
      groups[seen[key]].items.push(b)
    })

    if (groups.length === 0) return null

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {groups.map((group) => (
          <div key={group.catId ?? '__uncat__'}
            className="bg-slate-800/70 backdrop-blur-sm rounded-xl border border-slate-700/50 hover:border-cyan-500/40 transition-all flex flex-col overflow-hidden shadow-lg">

            {/* ── Category header ── */}
            <div className="bg-gradient-to-r from-slate-900/80 to-slate-800/60 px-4 pt-4 pb-3 border-b-2 border-cyan-500/30">
              {editingCategoryId === group.catId && isAdmin ? (
                <div className="flex items-center gap-2">
                  <input
                    autoFocus
                    value={editCatName}
                    onChange={(e) => setEditCatName(e.target.value)}
                    onKeyDown={(e) => { if (e.key === 'Enter') saveEditCategory(); if (e.key === 'Escape') cancelEditCategory() }}
                    className="flex-1 bg-slate-700 border border-cyan-500/50 rounded-lg px-2.5 py-1.5 text-sm font-bold text-white focus:outline-none focus:border-cyan-400"
                  />
                  <button onClick={saveEditCategory} disabled={savingCatEdit}
                    className="p-1.5 rounded-lg bg-cyan-600/30 hover:bg-cyan-600/50 text-cyan-300 transition-colors disabled:opacity-50">
                    {savingCatEdit ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                  </button>
                  <button onClick={cancelEditCategory} className="p-1.5 rounded-lg hover:bg-slate-700 text-gray-400 transition-colors">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center flex-shrink-0">
                    <FolderOpen className="w-4.5 h-4.5 text-cyan-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className={`text-sm font-bold truncate leading-tight ${group.catId ? catTextColor(group.catName) : 'text-gray-400'}`}>
                      {group.catName}
                    </h3>
                    <p className="text-[10px] text-gray-500 mt-0.5 font-medium">
                      {group.items.length} bookmark{group.items.length !== 1 ? 's' : ''}
                      {group.items.length > 4 && <span className="text-gray-600"> · scroll for more</span>}
                    </p>
                  </div>
                  <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full border flex-shrink-0 ${group.color}`}>
                    {group.items.length}
                  </span>
                  {isAdmin && group.catId !== null && (
                    <button onClick={() => startEditCategory(categories.find(c => c.id === group.catId)!)}
                      className="p-1.5 rounded-lg hover:bg-slate-700/60 text-gray-500 hover:text-cyan-400 transition-colors flex-shrink-0"
                      title="Rename category">
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* ── Bookmark rows (max 4 visible, then scroll) ── */}
            <div className="overflow-y-auto max-h-[176px] bg-slate-800/40 divide-y divide-slate-700/40">
              {group.items.map((b, idx) =>
                editingId === b.id ? (
                  <div key={b.id} className="p-3 bg-slate-800/90 border-l-2 border-cyan-500">
                    <InlineEditForm
                      {...{ editName, setEditName, editDesc, setEditDesc, editUrl, setEditUrl, editCategoryId, setEditCategoryId, categories, savingEdit }}
                      onSave={() => saveEdit(b.id)} onCancel={cancelEdit} />
                  </div>
                ) : (
                  <div key={b.id}
                    className="group flex items-center gap-3 px-3 py-2.5 hover:bg-slate-700/50 cursor-pointer transition-colors border-l-2 border-transparent hover:border-cyan-500/50"
                    onClick={(e) => openLink(e, b.url)}>
                    {/* Row number */}
                    <span className="w-5 h-5 rounded flex items-center justify-center text-[9px] font-bold text-gray-600 bg-slate-700/60 flex-shrink-0">
                      {idx + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs font-semibold text-white truncate group-hover:text-cyan-300 transition-colors">{b.name}</span>
                        <ExternalLink className="w-3 h-3 text-gray-600 group-hover:text-cyan-400 transition-colors flex-shrink-0" />
                      </div>
                      {b.description && (
                        <p className="text-[10px] text-gray-500 truncate mt-0.5 leading-tight">{b.description}</p>
                      )}
                    </div>
                    <div data-admin-action className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                      <AdminActions b={b} />
                    </div>
                  </div>
                )
              )}
            </div>

          </div>
        ))}
      </div>
    )
  }

  const renderCompact = () => (
    <div className="divide-y divide-slate-700/30">
      {filtered.map((b) =>
        editingId === b.id ? (
          <div key={b.id} className="py-3 px-2 bg-slate-800/60 rounded-lg mb-1">
            <InlineEditForm {...{ editName, setEditName, editDesc, setEditDesc, editUrl, setEditUrl, editCategoryId, setEditCategoryId, categories, savingEdit }}
              onSave={() => saveEdit(b.id)} onCancel={cancelEdit} />
          </div>
        ) : (
          <div key={b.id}
            className="group flex items-center gap-3 py-1.5 px-2 hover:bg-slate-700/30 rounded-lg cursor-pointer transition-colors"
            onClick={(e) => openLink(e, b.url)}>
            <BookmarkIcon className="w-3.5 h-3.5 text-cyan-500/60 flex-shrink-0" />
            <span className="text-sm text-white font-medium truncate flex-1 min-w-0">{b.name}</span>
            {b.category && (
              <span className={`hidden sm:inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded border flex-shrink-0 ${catColor(b.category.name)}`}>
                {b.category.name}
              </span>
            )}
            <span className="text-[10px] text-gray-600 truncate hidden md:block max-w-[200px]">{hostname(b.url)}</span>
            <ExternalLink className="w-3.5 h-3.5 text-gray-600 group-hover:text-cyan-400 transition-colors flex-shrink-0" />
            <div data-admin-action className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
              <AdminActions b={b} />
            </div>
          </div>
        )
      )}
    </div>
  )

  // ── Loading ────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
      </div>
    )
  }

  // ── Main render ────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full overflow-hidden bg-[#07182D]">

      {/* ── Header ── */}
      <div className="px-6 py-4 border-b border-slate-700/50 flex-shrink-0 space-y-3">
        {/* Title row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <BookmarkIcon className="w-6 h-6 text-cyan-400" />
            <h1 className="text-xl font-bold text-white">SE Bookmark Central</h1>
            <span className="text-xs bg-slate-700 text-gray-400 px-2 py-0.5 rounded-full">
              {bookmarks.length} link{bookmarks.length !== 1 ? 's' : ''}
            </span>
          </div>
          {isAdmin && (
            <div className="flex items-center space-x-2">
              {/* CSV export */}
              <button onClick={handleExport} disabled={bookmarks.length === 0}
                title="Export bookmarks to CSV"
                className="flex items-center space-x-1.5 px-3 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white rounded-lg transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
                <Download className="w-3.5 h-3.5" /><span>Export CSV</span>
              </button>
              {/* CSV import */}
              <button onClick={() => importInputRef.current?.click()} disabled={importing}
                title="Import bookmarks from CSV"
                className="flex items-center space-x-1.5 px-3 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white rounded-lg transition-colors disabled:opacity-50">
                {importing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                <span>{importing ? 'Importing…' : 'Import CSV'}</span>
              </button>
              <input ref={importInputRef} type="file" accept=".csv,text/csv" className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleImportFile(f) }} />
              <button onClick={() => { setShowAddCategory(true); setCategoryError(null) }}
                className="flex items-center space-x-1.5 px-3 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 text-gray-300 hover:text-white rounded-lg transition-colors">
                <FolderPlus className="w-3.5 h-3.5" /><span>Add Category</span>
              </button>
              <button onClick={() => { setShowAddBookmark(true); setBookmarkError(null) }}
                className="flex items-center space-x-1.5 px-3 py-1.5 text-xs bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white rounded-lg transition-all shadow-lg shadow-cyan-500/20">
                <Plus className="w-3.5 h-3.5" /><span>Add Bookmark</span>
              </button>
            </div>
          )}
        </div>

        {/* Controls row */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Search */}
          <div className="relative flex-1 min-w-[160px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input type="text" placeholder="Search bookmarks…" value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500" />
          </div>
          {/* Sort */}
          <div className="relative">
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value as SortOption)}
              className="appearance-none pl-3 pr-8 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg text-gray-300 focus:outline-none focus:border-cyan-500 cursor-pointer">
              {(Object.keys(SORT_LABELS) as SortOption[]).map((opt) => <option key={opt} value={opt}>{SORT_LABELS[opt]}</option>)}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" />
          </div>
          {/* Category filter */}
          <div className="relative">
            <select value={filterCategoryId} onChange={(e) => setFilterCategoryId(e.target.value === 'all' ? 'all' : Number(e.target.value))}
              className="appearance-none pl-3 pr-8 py-2 text-sm bg-slate-800 border border-slate-700 rounded-lg text-gray-300 focus:outline-none focus:border-cyan-500 cursor-pointer">
              <option value="all">All Categories</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" />
          </div>
          {/* View toggle */}
          <div className="flex items-center bg-slate-800 border border-slate-700 rounded-lg p-0.5 gap-0.5">
            {VIEW_OPTIONS.map(({ mode, icon, label }) => (
              <button key={mode} onClick={() => setViewMode(mode)} title={label}
                className={`flex items-center justify-center w-8 h-8 rounded-md transition-all ${
                  viewMode === mode
                    ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white shadow'
                    : 'text-gray-400 hover:text-white hover:bg-slate-700'
                }`}>
                {icon}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Import result banner */}
      {(importError || importSummary) && (
        <div className={`mx-6 mt-3 flex-shrink-0 rounded-lg border px-4 py-3 text-sm ${
          importError ? 'bg-red-400/10 border-red-400/20 text-red-400' : 'bg-slate-800 border-slate-700'
        }`}>
          {importError ? (
            <div className="flex items-center gap-2"><FileWarning className="w-4 h-4 flex-shrink-0" />{importError}</div>
          ) : importSummary ? (
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-medium text-white">
                  Import complete — <span className="text-green-400">{importSummary.created} added</span>
                  {importSummary.failed > 0 && <span className="text-red-400">, {importSummary.failed} failed</span>}
                </span>
                <button onClick={() => setImportSummary(null)} className="text-gray-500 hover:text-white transition-colors"><X className="w-4 h-4" /></button>
              </div>
              {importSummary.errors.length > 0 && (
                <ul className="text-xs text-red-400 space-y-0.5 mt-1">
                  {importSummary.errors.map((e, i) => <li key={i}>• {e}</li>)}
                </ul>
              )}
            </div>
          ) : null}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mx-6 mt-3 flex items-center space-x-2 text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-4 py-3 text-sm flex-shrink-0">
          <AlertCircle className="w-4 h-4 flex-shrink-0" /><span>{error}</span>
        </div>
      )}

      {/* Admin category panel */}
      {isAdmin && (
        <div className="mx-6 mt-3 flex-shrink-0">
          {/* Clickable header */}
          <button
            onClick={() => setShowCategoryPanel((v) => !v)}
            className={`w-full flex items-center justify-between px-4 py-2.5 rounded-xl border transition-all ${
              showCategoryPanel
                ? 'bg-slate-800/80 border-cyan-500/40 rounded-b-none'
                : 'bg-slate-800/50 border-slate-700/50 hover:border-slate-600'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <Tag className="w-4 h-4 text-cyan-400" />
              <span className="text-sm font-semibold text-white">Manage Categories</span>
              <span className="text-[10px] bg-slate-700 text-gray-400 px-2 py-0.5 rounded-full">
                {categories.length}
              </span>
            </div>
            <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform duration-200 ${
              showCategoryPanel ? 'rotate-180' : ''
            }`} />
          </button>

          {/* Expanded panel */}
          {showCategoryPanel && (
            <div className="bg-slate-800/70 border border-cyan-500/30 border-t-0 rounded-b-xl px-4 py-3">
              {categories.length === 0 ? (
                <p className="text-xs text-gray-500 py-1">No categories yet. Use "Add Category" to create one.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {categories.map((cat) => (
                    <span key={cat.id} className={`inline-flex items-center gap-1.5 text-xs px-3 py-1 rounded-full border ${catColor(cat.name)}`}>
                      <Tag className="w-3 h-3" />
                      {editingCategoryId === cat.id ? (
                        <span className="flex items-center gap-1">
                          <input
                            autoFocus
                            value={editCatName}
                            onChange={(e) => setEditCatName(e.target.value)}
                            onKeyDown={(e) => { if (e.key === 'Enter') saveEditCategory(); if (e.key === 'Escape') cancelEditCategory() }}
                            className="bg-transparent border-b border-current outline-none w-28 text-xs"
                          />
                          <button onClick={saveEditCategory} disabled={savingCatEdit} className="hover:opacity-70 disabled:opacity-50">
                            {savingCatEdit ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
                          </button>
                          <button onClick={cancelEditCategory} className="hover:opacity-70"><X className="w-3 h-3" /></button>
                        </span>
                      ) : (
                        <>
                          {cat.name}
                          <button onClick={() => startEditCategory(cat)} className="ml-0.5 hover:opacity-70 transition-opacity" title="Rename">
                            <Edit2 className="w-3 h-3" />
                          </button>
                          <button onClick={() => deleteCategory(cat.id, cat.name)} disabled={deletingCategoryId === cat.id}
                            className="hover:opacity-70 transition-opacity disabled:opacity-50">
                            {deletingCategoryId === cat.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <X className="w-3 h-3" />}
                          </button>
                        </>
                      )}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Bookmark content ── */}
      <div className="flex-1 overflow-y-auto px-6 py-5">
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center py-16">
            <BookmarkIcon className="w-12 h-12 text-gray-600 mb-4" />
            <p className="text-gray-400 font-medium">No bookmarks found</p>
            <p className="text-gray-600 text-sm mt-1">{isAdmin ? 'Click "Add Bookmark" to get started.' : 'No bookmarks have been added yet.'}</p>
          </div>
        ) : (
          <>
            {viewMode === 'tiles'    && renderTiles('grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4')}
            {viewMode === 'large'    && renderTiles('grid-cols-1 sm:grid-cols-2 lg:grid-cols-3')}
            {viewMode === 'list'     && renderList()}
            {viewMode === 'compact'  && renderCompact()}
            {viewMode === 'category' && renderGrouped()}
          </>
        )}
      </div>

      {/* ── Modal: Add Bookmark ── */}
      {showAddBookmark && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-base font-semibold text-white flex items-center gap-2"><Plus className="w-5 h-5 text-cyan-400" /> Add Bookmark</h2>
              <button onClick={() => setShowAddBookmark(false)} className="p-1.5 hover:bg-slate-700 rounded-lg text-gray-400 hover:text-white transition-colors"><X className="w-4 h-4" /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Name *</label>
                <input className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                  placeholder="e.g. Cisco DevNet" value={bName} onChange={(e) => setBName(e.target.value)} autoFocus />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Description</label>
                <textarea className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500 resize-none"
                  placeholder="Short description (optional)" rows={2} value={bDesc} onChange={(e) => setBDesc(e.target.value)} />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">URL *</label>
                <input type="url" className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                  placeholder="https://…" value={bUrl} onChange={(e) => setBUrl(e.target.value)} />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Category</label>
                <select value={bCategoryId} onChange={(e) => setBCategoryId(e.target.value === '' ? '' : Number(e.target.value))}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-gray-300 focus:outline-none focus:border-cyan-500">
                  <option value="">No category</option>
                  {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              {bookmarkError && (
                <div className="flex items-center gap-2 text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2 text-xs">
                  <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />{bookmarkError}
                </div>
              )}
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowAddBookmark(false)} className="flex-1 py-2 text-sm bg-slate-700 hover:bg-slate-600 text-gray-300 rounded-lg transition-colors">Cancel</button>
              <button onClick={handleAddBookmark} disabled={savingBookmark}
                className="flex-1 py-2 text-sm bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white rounded-lg transition-all disabled:opacity-50 flex items-center justify-center gap-2">
                {savingBookmark ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />} Add Bookmark
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Modal: Add Category ── */}
      {showAddCategory && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-2xl p-6 w-full max-w-sm shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-base font-semibold text-white flex items-center gap-2"><FolderPlus className="w-5 h-5 text-cyan-400" /> Add Category</h2>
              <button onClick={() => setShowAddCategory(false)} className="p-1.5 hover:bg-slate-700 rounded-lg text-gray-400 hover:text-white transition-colors"><X className="w-4 h-4" /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-gray-400 mb-1">Category Name *</label>
                <input className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                  placeholder="e.g. Engineering Tools" value={catName} onChange={(e) => setCatName(e.target.value)} autoFocus
                  onKeyDown={(e) => e.key === 'Enter' && handleAddCategory()} />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">Description</label>
                <input className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-cyan-500"
                  placeholder="Optional description" value={catDesc} onChange={(e) => setCatDesc(e.target.value)} />
              </div>
              {categoryError && (
                <div className="flex items-center gap-2 text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2 text-xs">
                  <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />{categoryError}
                </div>
              )}
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowAddCategory(false)} className="flex-1 py-2 text-sm bg-slate-700 hover:bg-slate-600 text-gray-300 rounded-lg transition-colors">Cancel</button>
              <button onClick={handleAddCategory} disabled={savingCategory}
                className="flex-1 py-2 text-sm bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white rounded-lg transition-all disabled:opacity-50 flex items-center justify-center gap-2">
                {savingCategory ? <Loader2 className="w-4 h-4 animate-spin" /> : <FolderPlus className="w-4 h-4" />} Add Category
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
