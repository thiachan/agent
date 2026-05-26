'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, ShieldCheck, AlertTriangle, RefreshCw, BookOpen, ChevronDown, ChevronUp, FileJson, MessageSquare } from 'lucide-react'
import api from '@/lib/api'

// ─── Types ────────────────────────────────────────────────────────────────────

type Mode = 'query' | 'validate'

interface ValidationFinding {
  claim: string
  status: 'validated' | 'needs_revision' | 'inaccurate'
  exact_quote?: string
  cisco_answer?: string
  sources: any[]
}

interface ContentValidationResult {
  id: number
  module_name: string
  is_truncated: boolean
  extracted_claims: string[]
  validation_findings: ValidationFinding[]
  qc_report: string
  validated_count: number
  flagged_count: number
  timestamp: Date
}

interface SourceMeta {
  doc_meta_info?: Record<string, unknown>
  is_answer_unknown?: boolean
  [key: string]: unknown
}

interface QCResult {
  id: number
  query: string
  answer: string
  sources: SourceMeta[]
  is_answer_unknown: boolean
  return_code: number
  return_message: string
  conversation_title?: string
  timestamp: Date
}

type SourceFilter = 'CDC' | 'SC' | 'HZ' | 'ALL'

const SOURCE_LABELS: Record<SourceFilter, string> = {
  CDC: 'Cisco Docs (CDC)',
  SC: 'Sales Connect (SC)',
  HZ: 'Help Zone (HZ)',
  ALL: 'All Sources',
}

// ─── Source Metadata Card ─────────────────────────────────────────────────────

function SourceCard({ meta, index }: { meta: SourceMeta; index: number }) {
  const [open, setOpen] = useState(false)
  const docMeta = meta.doc_meta_info

  const title =
    (docMeta as any)?.title ||
    (docMeta as any)?.doc_title ||
    (docMeta as any)?.name ||
    `Reference ${index + 1}`

  const url =
    (docMeta as any)?.url ||
    (docMeta as any)?.link ||
    (docMeta as any)?.source_url ||
    null

  return (
    <div className="border border-slate-600/40 rounded-lg overflow-hidden text-xs">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3 py-2 bg-slate-700/40 hover:bg-slate-700/60 transition-colors text-left"
      >
        <div className="flex items-center gap-2 min-w-0">
          <BookOpen className="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
          <span className="text-slate-200 truncate font-medium">{title}</span>
        </div>
        {open ? (
          <ChevronUp className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 ml-2" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 flex-shrink-0 ml-2" />
        )}
      </button>
      {open && (
        <div className="px-3 py-2 bg-slate-800/40 space-y-1.5">
          {url ? (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-400 hover:underline break-all"
            >
              {url}
            </a>
          ) : null}
          {docMeta && Object.keys(docMeta).length > 0 ? (
            <pre className="text-slate-400 text-[10px] overflow-auto max-h-32 whitespace-pre-wrap">
              {JSON.stringify(docMeta, null, 2)}
            </pre>
          ) : (
            <span className="text-slate-500">No additional metadata</span>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Result Card ──────────────────────────────────────────────────────────────

function ResultCard({ result }: { result: QCResult }) {
  const [sourcesOpen, setSourcesOpen] = useState(false)

  return (
    <div className="rounded-xl border border-slate-700/50 bg-slate-800/40 overflow-hidden">
      {/* Query */}
      <div className="px-4 py-3 border-b border-slate-700/40 bg-slate-700/20">
        <p className="text-xs text-slate-400 uppercase tracking-wider mb-1 font-semibold">Query</p>
        <p className="text-sm text-white">{result.query}</p>
      </div>

      {/* Answer */}
      <div className="px-4 py-4">
        {result.is_answer_unknown ? (
          <div className="flex items-start gap-3 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
            <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-amber-300 text-sm font-medium">No grounded answer found</p>
              <p className="text-amber-400/70 text-xs mt-1">
                Try rephrasing your query or selecting broader sources.
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-start gap-3">
            <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-1" />
            <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">{result.answer}</p>
          </div>
        )}
      </div>

      {/* Sources toggle */}
      {result.sources.length > 0 && (
        <div className="px-4 pb-4">
          <button
            onClick={() => setSourcesOpen((o) => !o)}
            className="flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            {sourcesOpen ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            {sourcesOpen ? 'Hide' : 'Show'} {result.sources.length} source
            {result.sources.length !== 1 ? 's' : ''}
          </button>
          {sourcesOpen && (
            <div className="mt-2 space-y-1.5">
              {result.sources.map((src, i) => (
                <SourceCard key={i} meta={src} index={i} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="px-4 py-2 border-t border-slate-700/30 bg-slate-700/10 flex items-center justify-between">
        <span
          className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
            result.return_code === 0
              ? 'bg-emerald-500/15 text-emerald-400'
              : 'bg-red-500/15 text-red-400'
          }`}
        >
          {result.return_message}
        </span>
        <span className="text-[10px] text-slate-500">
          {result.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          {result.conversation_title ? ` · ${result.conversation_title}` : ''}
        </span>
      </div>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function QCAgent() {
  const [mode, setMode] = useState<Mode>('query')
  const [query, setQuery] = useState('')
  const [jsonContent, setJsonContent] = useState('')
  const [moduleName, setModuleName] = useState('')
  const [selectedSource, setSelectedSource] = useState<SourceFilter>('CDC')
  const [results, setResults] = useState<QCResult[]>([])
  const [validationResults, setValidationResults] = useState<ContentValidationResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const jsonRef = useRef<HTMLTextAreaElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const nextId = useRef(1)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [results])

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault()
    const trimmed = query.trim()
    if (!trimmed || loading) return

    setLoading(true)
    setError(null)
    const submittedQuery = trimmed
    setQuery('')

    try {
      const { data } = await api.post('/api/qc-agent/query', {
        query: submittedQuery,
        selected_sources: selectedSource,
      })

      setResults((prev) => [
        ...prev,
        {
          id: nextId.current++,
          query: submittedQuery,
          answer: data.answer,
          sources: data.sources ?? [],
          is_answer_unknown: data.is_answer_unknown ?? false,
          return_code: data.return_code ?? 0,
          return_message: data.return_message ?? 'Success',
          conversation_title: data.conversation_title,
          timestamp: new Date(),
        },
      ])
    } catch (err: any) {
      const msg =
        err.response?.data?.detail ||
        err.message ||
        'Request failed. Please try again.'
      setError(msg)
    } finally {
      setLoading(false)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }

  const handleValidateContent = async () => {
    const trimmed = jsonContent.trim()
    if (!trimmed || loading) return

    setLoading(true)
    setError(null)

    try {
      const { data } = await api.post('/api/qc-agent/validate-content', {
        json_content: trimmed,
        module_name: moduleName || undefined,
        selected_sources: selectedSource,
      })

      setValidationResults((prev) => [
        ...prev,
        {
          id: nextId.current++,
          module_name: data.module_name,
          is_truncated: data.is_truncated,
          extracted_claims: data.extracted_claims,
          validation_findings: data.validation_findings,
          qc_report: data.qc_report,
          validated_count: data.validated_count,
          flagged_count: data.flagged_count,
          timestamp: new Date(),
        },
      ])
      
      // Clear inputs after successful validation
      setJsonContent('')
      setModuleName('')
    } catch (err: any) {
      const msg =
        err.response?.data?.detail ||
        err.message ||
        'Validation failed. Please check your JSON and try again.'
      setError(msg)
    } finally {
      setLoading(false)
      setTimeout(() => jsonRef.current?.focus(), 50)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="flex flex-col h-full bg-[#07182D]">
      {/* Header */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-slate-700/50 bg-slate-900/40">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h1 className="text-lg font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-cyan-400" />
              QC Agent
            </h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Cisco-data-grounded content validation · Powered by Cisco Data RAG API
            </p>
          </div>

          {/* Source selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Source:</span>
            <div className="flex rounded-lg overflow-hidden border border-slate-600/50">
              {(Object.keys(SOURCE_LABELS) as SourceFilter[]).map((src) => (
                <button
                  key={src}
                  onClick={() => setSelectedSource(src)}
                  className={`px-2.5 py-1.5 text-xs transition-colors ${
                    selectedSource === src
                      ? 'bg-cyan-500/30 text-cyan-300 border-r border-slate-600/50 last:border-r-0'
                      : 'text-slate-400 hover:text-white hover:bg-slate-700/40 border-r border-slate-600/50 last:border-r-0'
                  }`}
                >
                  {src}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Mode Switcher */}
        <div className="flex gap-2">
          <button
            onClick={() => setMode('query')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors ${
              mode === 'query'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-700/40 border border-transparent'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            Quick Query
          </button>
          <button
            onClick={() => setMode('validate')}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors ${
              mode === 'validate'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-700/40 border border-transparent'
            }`}
          >
            <FileJson className="w-3.5 h-3.5" />
            Content Validation
          </button>
        </div>
      </div>

      {/* Results area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {results.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center h-full text-center py-16">
            <ShieldCheck className="w-12 h-12 text-cyan-500/40 mb-4" />
            <h2 className="text-slate-300 font-medium text-lg mb-2">Validate content against Cisco data</h2>
            <p className="text-slate-500 text-sm max-w-sm">
              Ask any question. Answers are grounded in Cisco-approved documentation and sales content.
            </p>
            <div className="mt-6 grid grid-cols-1 gap-2 w-full max-w-sm">
              {[
                'How does Cisco AI Access work?',
                'What is the licensing model for Cisco AI Defense?',
                'Explain Cisco Smart Licensing on IOS XE.',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    setQuery(suggestion)
                    inputRef.current?.focus()
                  }}
                  className="text-left px-3 py-2.5 rounded-lg border border-slate-700/50 bg-slate-800/40 hover:bg-slate-700/40 text-slate-300 hover:text-white text-xs transition-colors"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {results.map((result) => (
          <ResultCard key={result.id} result={result} />
        ))}

        {loading && (
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-slate-700/40 bg-slate-800/30 text-sm text-slate-400">
            <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
            Querying Cisco Data RAG…
          </div>
        )}

        {error && (
          <div className="flex items-start gap-3 px-4 py-3 rounded-xl border border-red-500/30 bg-red-500/10 text-sm text-red-300">
            <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Error</p>
              <p className="text-red-400/80 text-xs mt-0.5">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="ml-auto text-red-400/60 hover:text-red-300 text-xs"
            >
              Dismiss
            </button>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex-shrink-0 px-6 py-4 border-t border-slate-700/50 bg-slate-900/20">
        {results.length > 0 && (
          <div className="flex justify-end mb-2">
            <button
              onClick={() => setResults([])}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
            >
              <RefreshCw className="w-3 h-3" />
              Clear history
            </button>
          </div>
        )}
        <form onSubmit={handleSubmit} className="flex gap-3 items-end">
          <textarea
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question to validate against Cisco data… (Enter to send)"
            rows={2}
            className="flex-1 resize-none bg-slate-800/60 border border-slate-600/50 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/40 focus:border-cyan-500/40 transition-all"
          />
          <button
            type="submit"
            disabled={!query.trim() || loading}
            className="flex-shrink-0 p-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl transition-all shadow-lg shadow-cyan-500/20"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </form>
        <p className="text-[10px] text-slate-600 mt-2 text-right">
          Source: {SOURCE_LABELS[selectedSource]} · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
