'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Loader2, FileText, RefreshCw, FlaskConical } from 'lucide-react'
import api from '@/lib/api'

// ─── Types ────────────────────────────────────────────────────────────────────

type Phase = 'topic_select' | 'prequalify' | 'discovery' | 'discovery_need' | 'chat'

interface SourceDoc {
  content?: string
  score?: number
  metadata?: Record<string, unknown>
}

interface Message {
  id: number
  role: 'bot' | 'user'
  content: string
  options?: string[]
  sources?: SourceDoc[]
  error?: boolean
}

// ─── Conversation config ──────────────────────────────────────────────────────

const TOPICS = ['Sales', 'Demo', 'Support', 'License', 'Customer Qualify', 'Other']

const PREQUALIFY: Record<string, Array<{ q: string; options: string[] }>> = {
  Sales: [
    { q: "What is the customer's primary use case?", options: ['Shadow AI / AI Access', 'AI App Security', 'Both'] },
    { q: 'Which region / theater?', options: ['Americas', 'EMEA', 'APJC'] },
    { q: 'What is the project type?', options: ['New Logo', 'Expansion / Upsell', 'Renewal'] },
  ],
  Demo: [
    { q: 'Which product area to demo?', options: ['AI Access', 'AI Validation', 'AI Runtime Protection', 'Full AI Defense'] },
    { q: 'Who is the target audience?', options: ['CISO / CIO', 'Security Team', 'AI / Dev Team', 'Executive'] },
    { q: 'What is the demo timeline?', options: ['This week', 'Within 2 weeks', 'Within a month'] },
  ],
  Support: [
    { q: 'Which product is affected?', options: ['AI Access', 'AI Validation', 'AI Runtime Protection', 'Other'] },
    { q: 'What is the severity?', options: ['Critical – production down', 'High – major impact', 'Medium', 'Low'] },
    { q: 'Is this customer-facing or internal?', options: ['Customer-facing', 'Internal'] },
  ],
  License: [
    { q: 'Which license tier?', options: ['Validation Essentials', 'Runtime Essentials', 'Advantage', 'AI Access only'] },
    { q: 'How many AI apps to protect?', options: ['1–5', '6–20', '21–50', '50+'] },
    { q: 'New purchase or renewal?', options: ['New purchase', 'Renewal', 'Upgrade'] },
  ],
  'Customer Qualify': [
    { q: 'Does the customer have AI apps in production or development?', options: ['Yes – in production', 'In development', 'Planning stage', 'Not yet'] },
    { q: 'Does a security team own AI governance?', options: ['Yes', 'In progress', 'No'] },
    { q: 'Budget signal?', options: ['Confirmed budget', 'Budget discussion ongoing', 'No budget yet'] },
  ],
  Other: [
    { q: 'What best describes your request?', options: ['Partner enablement', 'Competitive intel', 'Pricing question', "Other – I'll describe below"] },
  ],
}

const DISCOVERY_BASE: Array<{ key: string; q: string }> = [
  { key: 'account', q: 'What is the account name?' },
  { key: 'contact', q: 'Contact name and title?' },
  { key: 'region',  q: 'Location / region?' },
  { key: 'sfdc',    q: 'SFDC Opportunity ID (or N/A)?' },
]

const TOPIC_NEED_QUESTION: Record<string, string> = {
  Sales:              'What specific sales support or objection are you trying to address? I\'ll search the knowledge base for you.',
  Demo:               'What specific demo scenario or asset do you need? I\'ll search the knowledge base for you.',
  Support:            'Describe the issue in detail — what exactly do you need help resolving? I\'ll search the knowledge base for you.',
  License:            'What specifically do you need to know about licensing or packaging? I\'ll search the knowledge base for you.',
  'Customer Qualify': 'What specific qualification criteria or objections are you trying to address? I\'ll search the knowledge base for you.',
  Other:              'Describe what you need — I\'ll search the knowledge base for you.',
}

// ─── Component ────────────────────────────────────────────────────────────────

export function Incubation() {
  const [messages, setMessages]             = useState<Message[]>([])
  const [phase, setPhase]                   = useState<Phase>('topic_select')
  const [topic, setTopic]                   = useState<string | null>(null)
  const [prequalifyStep, setPrequalifyStep] = useState(0)
  const [prequalifyAnswers, setPrequalifyAnswers] = useState<string[]>([])
  const [discoveryStep, setDiscoveryStep]   = useState(0)
  const [discoveryAnswers, setDiscoveryAnswers] = useState<Record<string, string>>({})
  const [contextPrefix, setContextPrefix]   = useState('')
  const [input, setInput]                   = useState('')
  const [loading, setLoading]               = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef  = useRef<HTMLTextAreaElement>(null)
  const msgId     = useRef(0)

  const nextId  = () => ++msgId.current
  const pushBot = (content: string, options?: string[]) =>
    setMessages(prev => [...prev, { id: nextId(), role: 'bot', content, options }])
  const pushUser = (content: string) =>
    setMessages(prev => [...prev, { id: nextId(), role: 'user', content }])

  // Initial greeting on mount
  useEffect(() => {
    pushBot(
      "Hello! I'm the Incubation Bot for Cisco AI Defense.\n\nNote: I am powered by AI. Please verify accuracy before sharing results with customers.\n\nHow can I help you today? Please choose a topic:",
      TOPICS
    )
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // ── conversation flow helpers ─────────────────────────────────────────────

  const startPrequalify = (selectedTopic: string) => {
    const qs = PREQUALIFY[selectedTopic]
    pushBot(`Great, let's qualify this **${selectedTopic}** request.\n\n${qs[0].q}`, qs[0].options)
    setPhase('prequalify')
    setTopic(selectedTopic)
    setPrequalifyStep(0)
  }

  const advancePrequalify = (currentStep: number, currentTopic: string, answer: string) => {
    setPrequalifyAnswers(prev => [...prev, answer])
    const qs = PREQUALIFY[currentTopic]
    const next = currentStep + 1
    if (next < qs.length) {
      pushBot(qs[next].q, qs[next].options)
      setPrequalifyStep(next)
    } else {
      pushBot(`Perfect — pre-qualification complete.\n\nNow I need a few account details.\n\n${DISCOVERY_BASE[0].q}`)
      setPhase('discovery')
      setDiscoveryStep(0)
    }
  }

  const queryDrift = async (query: string) => {
    setLoading(true)
    try {
      // Send last 6 messages as history so DRIFT has conversation context
      const history = messages
        .filter(m => m.role === 'user' || (m.role === 'bot' && !m.error && m.content.length > 10))
        .slice(-6)
        .map(m => ({ role: m.role, content: m.content.slice(0, 400) }))

      const resp = await api.post('/api/incubation/search', { query, history })
      const data = resp.data
      setMessages(prev => [...prev, {
        id: nextId(), role: 'bot',
        content: data.answer || 'No answer returned.',
        sources: data.sources || [],
      }])
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (err as Error)?.message || 'Something went wrong.'
      setMessages(prev => [...prev, { id: nextId(), role: 'bot', content: detail, error: true }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const advanceDiscovery = (answer: string, currentStep: number, currentTopic: string) => {
    const key = DISCOVERY_BASE[currentStep].key
    const updated = { ...discoveryAnswers, [key]: answer }
    setDiscoveryAnswers(updated)
    const next = currentStep + 1
    if (next < DISCOVERY_BASE.length) {
      pushBot(DISCOVERY_BASE[next].q)
      setDiscoveryStep(next)
    } else {
      // Last step: ask the topic-specific question then immediately fire DRIFT on the answer
      const needQ = TOPIC_NEED_QUESTION[currentTopic] || 'What do you need help with? I\'ll search the knowledge base.'
      pushBot(needQ)
      setPhase('discovery_need')
    }
  }

  // ── user interactions ─────────────────────────────────────────────────────

  const dismissOptions = () =>
    setMessages(prev => prev.map((m, i) => i === prev.length - 1 ? { ...m, options: undefined } : m))

  const handleTopicSelect = (opt: string) => {
    dismissOptions()
    pushUser(opt)
    startPrequalify(opt)
  }

  const handleQuickReply = (opt: string) => {
    dismissOptions()
    pushUser(opt)
    if (phase === 'prequalify' && topic) advancePrequalify(prequalifyStep, topic, opt)
  }

  const handleSend = async () => {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    dismissOptions()
    pushUser(text)

    if (phase === 'prequalify' && topic) { advancePrequalify(prequalifyStep, topic, text); return }
    if (phase === 'discovery' && topic) { advanceDiscovery(text, discoveryStep, topic); return }
    if (phase === 'discovery_need') {
      // Build context prefix from topic + prequalify answers — stored for all subsequent queries
      const qs = topic ? PREQUALIFY[topic] : []
      const contextParts = [
        topic ? `Topic: ${topic}` : '',
        ...qs.map((q, i) => prequalifyAnswers[i] ? `${q.q.replace(/\?$/, '')}: ${prequalifyAnswers[i]}` : ''),
      ].filter(Boolean)
      const prefix = contextParts.length ? `[Context: ${contextParts.join(' | ')}] ` : ''
      setContextPrefix(prefix)
      setPhase('chat')
      queryDrift(prefix + text)
      return
    }

    // phase === 'chat' — DRIFT query, always include context prefix
    queryDrift(contextPrefix + text)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const handleReset = () => {
    setMessages([])
    setPhase('topic_select')
    setTopic(null)
    setPrequalifyStep(0)
    setPrequalifyAnswers([])
    setDiscoveryStep(0)
    setDiscoveryAnswers({})
    setContextPrefix('')
    setInput('')
    setTimeout(() => pushBot(
      "Hello! I'm the Incubation Bot for Cisco AI Defense.\n\nNote: I am powered by AI. Please verify accuracy before sharing results with customers.\n\nHow can I help you today? Please choose a topic:",
      TOPICS
    ), 50)
  }

  const placeholder = phase === 'chat'
    ? 'Ask about AI Defense, battlecards, competitor positioning…'
    : 'Type your answer, or click an option above…'

  // ── render ────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-full bg-[#07182D]">

      {/* Header */}
      <div className="flex-shrink-0 px-5 py-3 border-b border-slate-700/50 bg-slate-900/60 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-700 flex items-center justify-center shadow shadow-violet-700/40">
            <FlaskConical className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-white leading-tight">Incubation Bot</p>
            <p className="text-[10px] text-gray-400">Cisco AI Defense · DRIFT RAG · Granite Reranker</p>
          </div>
        </div>
        <button
          onClick={handleReset}
          title="Start new conversation"
          className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-slate-700/50 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Info banner */}
      <div className="flex-shrink-0 bg-blue-900/30 border-b border-blue-700/30 px-5 py-2">
        <p className="text-[11px] text-blue-300">
          AI-generated content — verify accuracy and completeness before sharing with customers.
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-5 space-y-4 min-h-0">
        {messages.map((msg, idx) => (
          <div key={msg.id}>
            <div className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>

              {msg.role === 'user' ? (
                <div className="max-w-[72%] bg-gradient-to-br from-violet-600/90 to-purple-700/90 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm shadow shadow-violet-900/30 whitespace-pre-wrap">
                  {msg.content}
                </div>
              ) : (
                <div className="max-w-[82%] space-y-3">

                  {/* Bot bubble */}
                  <div className={`rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap shadow ${
                    msg.error
                      ? 'bg-red-900/30 border border-red-500/30 text-red-300'
                      : 'bg-slate-800/80 border border-slate-700/40 text-gray-100'
                  }`}>
                    {msg.content}
                  </div>

                  {/* Quick-reply buttons — only on last message */}
                  {msg.options && idx === messages.length - 1 && (
                    <div className="flex flex-col space-y-2 pl-1">
                      {msg.options.map(opt => (
                        <button
                          key={opt}
                          onClick={() => phase === 'topic_select' ? handleTopicSelect(opt) : handleQuickReply(opt)}
                          className="text-left px-4 py-2 rounded-full border border-violet-500/50 text-violet-300 hover:bg-violet-600/20 hover:border-violet-400 hover:text-white transition-all text-sm w-fit"
                        >
                          {opt}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Sources */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="space-y-1.5">
                      <p className="text-[10px] uppercase tracking-wider text-gray-500 px-1">Sources</p>
                      {msg.sources.map((src, i) => (
                        <div key={i} className="bg-slate-800/50 border border-slate-700/40 rounded-xl px-3 py-2 space-y-1">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-1.5">
                              <FileText className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                              <span className="text-xs text-gray-300 truncate max-w-[260px]">
                                {(src.metadata?.source as string) ||
                                  (src.metadata?.filename as string) ||
                                  (src.metadata?.file_name as string) ||
                                  `Source ${i + 1}`}
                              </span>
                            </div>
                            {src.score != null && (
                              <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded-full ${
                                src.score >= 0.8 ? 'bg-emerald-900/40 text-emerald-400'
                                  : src.score >= 0.6 ? 'bg-yellow-900/40 text-yellow-400'
                                  : 'bg-slate-700/50 text-gray-400'
                              }`}>
                                {src.score.toFixed(3)}
                              </span>
                            )}
                          </div>
                          {src.content && (
                            <p className="text-xs text-gray-400 leading-relaxed line-clamp-3">{src.content}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-800/80 border border-slate-700/40 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center space-x-2 text-gray-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-xs">Searching knowledge base…</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex-shrink-0 px-4 py-3 border-t border-slate-700/50 bg-slate-900/40">
        <div className="flex items-end space-x-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows={1}
            disabled={loading}
            className="flex-1 bg-slate-700/50 border border-slate-600/50 rounded-xl px-4 py-2.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-violet-500/50 resize-none leading-relaxed disabled:opacity-50"
            style={{ minHeight: '40px', maxHeight: '120px' }}
            onInput={e => {
              const el = e.currentTarget
              el.style.height = 'auto'
              el.style.height = `${Math.min(el.scrollHeight, 120)}px`
            }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="flex-shrink-0 w-9 h-9 flex items-center justify-center bg-gradient-to-br from-violet-600 to-purple-700 text-white rounded-xl hover:from-violet-500 hover:to-purple-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
        <p className="text-[10px] text-gray-600 mt-1.5 px-1">Enter to send · Shift+Enter for new line</p>
      </div>

    </div>
  )
}
