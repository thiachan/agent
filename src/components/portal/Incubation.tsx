'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, ChevronDown, ChevronUp, FileText, AlertCircle, FlaskConical } from 'lucide-react'
import api from '@/lib/api'

interface SourceDoc {
  content?: string
  score?: number
  metadata?: Record<string, unknown>
}

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources?: SourceDoc[]
  error?: boolean
}

export function Incubation() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [filterKey, setFilterKey] = useState('')
  const [filterValue, setFilterValue] = useState('')
  const [filters, setFilters] = useState<Record<string, string>>({})
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const msgId = useRef(0)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const addFilter = () => {
    const k = filterKey.trim()
    const v = filterValue.trim()
    if (!k || !v) return
    setFilters(prev => ({ ...prev, [k]: v }))
    setFilterKey('')
    setFilterValue('')
  }

  const removeFilter = (key: string) => {
    setFilters(prev => {
      const next = { ...prev }
      delete next[key]
      return next
    })
  }

  const sendMessage = async () => {
    const query = input.trim()
    if (!query || loading) return

    const userMsg: Message = { id: ++msgId.current, role: 'user', content: query }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const body: { query: string; meta_filters?: Record<string, string> } = { query }
      if (Object.keys(filters).length > 0) body.meta_filters = filters

      const resp = await api.post('/api/incubation/search', body)
      const data = resp.data

      const assistantMsg: Message = {
        id: ++msgId.current,
        role: 'assistant',
        content: data.answer || 'No answer returned.',
        sources: data.sources || [],
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message ||
        'Something went wrong.'
      setMessages(prev => [
        ...prev,
        { id: ++msgId.current, role: 'assistant', content: detail, error: true },
      ])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="flex flex-col h-full bg-[#07182D]">
      {/* Header */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-slate-700/50 bg-slate-800/40">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-violet-500 to-purple-700 flex items-center justify-center shadow-lg shadow-violet-500/30">
            <FlaskConical className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-white">Incubation Bot</h1>
            <p className="text-xs text-gray-400">Cisco AI Defense · DRIFT RAG · Granite Reranker</p>
          </div>
        </div>
      </div>

      {/* Metadata filters bar */}
      <div className="flex-shrink-0 border-b border-slate-700/30 bg-slate-800/20">
        <button
          onClick={() => setShowFilters(v => !v)}
          className="w-full flex items-center justify-between px-6 py-2 text-xs text-gray-400 hover:text-white transition-colors"
        >
          <span className="flex items-center space-x-2">
            <span>Metadata Filters</span>
            {Object.keys(filters).length > 0 && (
              <span className="bg-violet-600 text-white rounded-full px-2 py-0.5 text-[10px]">
                {Object.keys(filters).length}
              </span>
            )}
          </span>
          {showFilters ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>

        {showFilters && (
          <div className="px-6 pb-3 space-y-2">
            {/* Active filters */}
            {Object.entries(filters).length > 0 && (
              <div className="flex flex-wrap gap-2 mb-2">
                {Object.entries(filters).map(([k, v]) => (
                  <span
                    key={k}
                    className="flex items-center space-x-1 bg-violet-600/20 border border-violet-500/30 text-violet-300 rounded-full px-2.5 py-0.5 text-xs"
                  >
                    <span>{k}: {v}</span>
                    <button
                      onClick={() => removeFilter(k)}
                      className="ml-1 hover:text-white"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            )}
            {/* Add filter */}
            <div className="flex items-center space-x-2">
              <input
                type="text"
                value={filterKey}
                onChange={e => setFilterKey(e.target.value)}
                placeholder="key (e.g. department)"
                className="flex-1 bg-slate-700/50 border border-slate-600/50 rounded-lg px-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-violet-500/50"
              />
              <input
                type="text"
                value={filterValue}
                onChange={e => setFilterValue(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && addFilter()}
                placeholder="value"
                className="flex-1 bg-slate-700/50 border border-slate-600/50 rounded-lg px-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-violet-500/50"
              />
              <button
                onClick={addFilter}
                className="px-3 py-1.5 bg-violet-600/80 hover:bg-violet-600 text-white text-xs rounded-lg transition-colors"
              >
                Add
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6 min-h-0">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-3">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500/20 to-purple-700/20 border border-violet-500/20 flex items-center justify-center">
              <FlaskConical className="w-8 h-8 text-violet-400" />
            </div>
            <p className="text-white font-medium">Ask the Incubation Bot</p>
            <p className="text-gray-400 text-sm max-w-sm">
              Query the AI Defense knowledge base — battlecards, FAQs, discovery packets, and more.
            </p>
          </div>
        )}

        {messages.map(msg => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'user' ? (
              <div className="max-w-[70%] bg-gradient-to-br from-violet-600/80 to-purple-700/80 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm shadow-lg shadow-violet-900/30">
                {msg.content}
              </div>
            ) : (
              <div className="max-w-[85%] space-y-3">
                {/* Answer bubble */}
                <div
                  className={`rounded-2xl rounded-tl-sm px-4 py-3 text-sm shadow-md ${
                    msg.error
                      ? 'bg-red-900/30 border border-red-500/30 text-red-300'
                      : 'bg-slate-800/80 border border-slate-700/50 text-gray-100'
                  }`}
                >
                  {msg.error && (
                    <div className="flex items-center space-x-2 mb-1">
                      <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                      <span className="text-xs text-red-400 font-medium">Error</span>
                    </div>
                  )}
                  <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
                </div>

                {/* Sources */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-[10px] uppercase tracking-wider text-gray-500 px-1">Sources</p>
                    {msg.sources.map((src, i) => (
                      <div
                        key={i}
                        className="bg-slate-800/50 border border-slate-700/40 rounded-xl px-3 py-2.5 space-y-1.5"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-1.5">
                            <FileText className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                            <span className="text-xs text-gray-300 truncate max-w-[300px]">
                              {(src.metadata?.source as string) ||
                                (src.metadata?.filename as string) ||
                                (src.metadata?.file_name as string) ||
                                `Source ${i + 1}`}
                            </span>
                          </div>
                          {src.score != null && (
                            <span
                              className={`text-[10px] font-mono px-1.5 py-0.5 rounded-full ${
                                src.score >= 0.8
                                  ? 'bg-emerald-900/40 text-emerald-400'
                                  : src.score >= 0.6
                                  ? 'bg-yellow-900/40 text-yellow-400'
                                  : 'bg-slate-700/50 text-gray-400'
                              }`}
                            >
                              {src.score.toFixed(3)}
                            </span>
                          )}
                        </div>
                        {src.content && (
                          <p className="text-xs text-gray-400 leading-relaxed line-clamp-3">
                            {src.content}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-800/80 border border-slate-700/50 rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex items-center space-x-2 text-gray-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span className="text-xs">Searching knowledge base…</span>
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex-shrink-0 px-4 py-4 border-t border-slate-700/50 bg-slate-800/20">
        <div className="flex items-end space-x-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about AI Defense, battlecards, competitor positioning…"
            rows={1}
            className="flex-1 bg-slate-700/50 border border-slate-600/50 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-violet-500/50 resize-none leading-relaxed"
            style={{ minHeight: '44px', maxHeight: '120px' }}
            onInput={e => {
              const el = e.currentTarget
              el.style.height = 'auto'
              el.style.height = `${Math.min(el.scrollHeight, 120)}px`
            }}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            className="flex-shrink-0 w-10 h-10 flex items-center justify-center bg-gradient-to-br from-violet-600 to-purple-700 text-white rounded-xl hover:from-violet-500 hover:to-purple-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-violet-900/30"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
        <p className="text-[10px] text-gray-600 mt-2 px-1">Enter to send · Shift+Enter for new line</p>
      </div>
    </div>
  )
}
