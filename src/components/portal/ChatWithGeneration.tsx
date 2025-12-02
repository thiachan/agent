'use client'

import { useState, useEffect, useRef } from 'react'
import { Send, Loader2, FileText, Video, Presentation, Download, Sparkles, Bot, Music, Mic2, Settings, ArrowLeft, Users } from 'lucide-react'
import api from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'

interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  metadata?: any
  created_at?: string
}

interface Model {
  id: string
  name: string
  provider: string
  model_id: string
  type: string
}

interface GenerationOption {
  type: 'ppt' | 'mp4' | 'doc' | 'pdf' | 'speech' | 'podcast'
  label: string
  icon: React.ReactNode
}

const generationOptions: GenerationOption[] = [
  { type: 'ppt', label: 'PowerPoint', icon: <Presentation size={18} /> },
  { type: 'mp4', label: 'Video', icon: <Video size={18} /> },
  { type: 'doc', label: 'Document', icon: <FileText size={18} /> },
  { type: 'pdf', label: 'PDF', icon: <FileText size={18} /> },
  { type: 'speech', label: 'Speech (MP3)', icon: <Mic2 size={18} /> },
  { type: 'podcast', label: 'Podcast (MP3)', icon: <Music size={18} /> },
]

interface Template {
  id: number
  filename: string
  title: string
  file_type: string
  file_size: number
  created_at: string
  owner: {
    id: number
    full_name: string
  }
}

interface ChatWithGenerationProps {
  sessionId?: number | null
  onNewChat?: () => void
  onSessionCreated?: (sessionId: number) => void
}

export function ChatWithGeneration({ sessionId: propSessionId, onNewChat, onSessionCreated }: ChatWithGenerationProps) {
  const { isAuthenticated } = useAuthStore()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState<{ messageId: number; type: string } | null>(null)
  const [sessionId, setSessionId] = useState<number | null>(propSessionId || null)
  const [selectedContentType, setSelectedContentType] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState<string>('auto')
  const [availableModels, setAvailableModels] = useState<Model[]>([])
  const [loadingModels, setLoadingModels] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [ciscoTemplateId, setCiscoTemplateId] = useState<number | null>(null)
  const [currentChatTitle, setCurrentChatTitle] = useState<string>('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (propSessionId !== undefined) {
      setSessionId(propSessionId)
    }
  }, [propSessionId])

  useEffect(() => {
    if (isAuthenticated) {
      fetchModels()
      findCiscoTemplate()
      checkConnection()
      // Check connection periodically
      const interval = setInterval(checkConnection, 30000) // Check every 30 seconds
      return () => clearInterval(interval)
    }
  }, [isAuthenticated])

  const checkConnection = async () => {
    try {
      const response = await api.get('/api/models/')
      setIsConnected(response.status === 200 && response.data?.models?.length > 0)
    } catch (error) {
      setIsConnected(false)
    }
  }

  useEffect(() => {
    if (sessionId) {
      loadSessionMessages(sessionId)
    } else {
      setMessages([])
      setCurrentChatTitle('')
    }
  }, [sessionId])

  
  const loadSessionMessages = async (sid: number) => {
    try {
      const response = await api.get(`/api/chat/sessions/${sid}/messages`)
      if (response.data) {
        setCurrentChatTitle(response.data.title || 'Chat')
        const loadedMessages: Message[] = response.data.messages.map((msg: any) => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          metadata: msg.metadata,
          created_at: msg.created_at,
        }))
        setMessages(loadedMessages)
      }
    } catch (error) {
      console.error('Failed to load session messages:', error)
    }
  }

  const findCiscoTemplate = async () => {
    try {
      const response = await api.get('/api/upload/templates')
      if (response.data && response.data.templates) {
        const ciscoTemplate = response.data.templates.find((t: Template) => {
          const filename = t.filename.toLowerCase()
          return (filename.includes('cisco') && 
                  filename.includes('template') && 
                  filename.includes('light') &&
                  filename.includes('icon')) ||
                 filename.includes('cisco_powerpoint_template_light')
        })
        if (ciscoTemplate) {
          setCiscoTemplateId(ciscoTemplate.id)
        } else {
          if (response.data.templates.length > 0) {
            setCiscoTemplateId(response.data.templates[0].id)
          }
        }
      }
    } catch (error: any) {
      console.error('Failed to fetch templates:', error)
    }
  }

  const fetchModels = async () => {
    setLoadingModels(true)
    try {
      const response = await api.get('/api/models/')
      if (response.data && response.data.models) {
        setAvailableModels(response.data.models)
        if (response.data.models.length > 0 && selectedModel === 'auto') {
          const defaultModel = response.data.models.find((m: Model) => m.id === 'auto') || response.data.models[0]
          if (defaultModel) {
            setSelectedModel(defaultModel.id)
          }
        }
      }
    } catch (error: any) {
      console.error('Failed to fetch models:', error)
      setAvailableModels([])
    } finally {
      setLoadingModels(false)
    }
  }

  const detectGenerationRequest = (text: string): string[] => {
    const lowerText = text.toLowerCase()
    const requestedTypes: string[] = []
    
    // Check if this is an audio request (mp3, wav, speech, audio)
    const isAudioRequest = lowerText.includes('mp3') || lowerText.includes('wav') || 
                          lowerText.includes('speech') || lowerText.includes('audio') ||
                          lowerText.includes('save as') || lowerText.includes('save them')
    
    if (isAudioRequest) {
      // Check for podcast/dialogue keywords
      const hasPodcastKeywords = lowerText.includes('podcast') || 
                                 lowerText.includes('dialogue') || 
                                 lowerText.includes('interview') || 
                                 lowerText.includes('conversation')
      
      if (hasPodcastKeywords) {
        // This is a podcast request (dialogue format)
        requestedTypes.push('podcast')
      } else {
        // This is a speech request (monologue, single voice)
        requestedTypes.push('speech')
      }
    }
    
    if (lowerText.includes('powerpoint') || lowerText.includes('ppt') || lowerText.includes('presentation') ||
        lowerText.includes('generate ppt') || lowerText.includes('create ppt') || 
        lowerText.includes('make presentation')) {
      requestedTypes.push('ppt')
    }
    
    if (lowerText.includes('video') || lowerText.includes('mp4') || 
        lowerText.includes('generate video') || lowerText.includes('create video') || 
        lowerText.includes('make video')) {
      requestedTypes.push('mp4')
    }
    
    if (lowerText.includes('document') || lowerText.includes('doc') || 
        lowerText.includes('word') || lowerText.includes('generate document') || 
        lowerText.includes('create document')) {
      requestedTypes.push('doc')
    }
    
    if (lowerText.includes('pdf') || lowerText.includes('generate pdf') || 
        lowerText.includes('create pdf')) {
      requestedTypes.push('pdf')
    }
    
    return requestedTypes
  }

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const token = localStorage.getItem('auth_token')
    if (!token) {
      alert('Please log in to send messages')
      return
    }

    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      content: input,
    }
    setMessages((prev) => [...prev, userMessage])
    const currentInput = input
    setInput('')
    setLoading(true)

    const requestedTypes = detectGenerationRequest(currentInput)

    try {
      // Always use 'auto' model ID which should map to GPT-4.1 (Cisco)
      const response = await api.post('/api/chat/message', {
        message: currentInput,
        session_id: sessionId,
        model_id: 'auto', // Fixed to use default model
        content_type: selectedContentType, // Pass selected content type to backend
      })
      
      // Clear selected content type after sending
      setSelectedContentType(null)

      const { session_id, message } = response.data
      setSessionId(session_id)
      if (onSessionCreated && session_id) {
        onSessionCreated(session_id)
      }

      // Check if this message has PowerPoint generation metadata (needs confirmation)
      // The message content is the RAG response, which will be used for PowerPoint generation

      // Check if this is an agent response with PowerPoint data
      let agentResult = null
      if (message.metadata?.agent_call?.result) {
        agentResult = message.metadata.agent_call.result
      } else if (message.content.startsWith('Agent Response:')) {
        // Try to parse the agent response from the content
        try {
          const jsonMatch = message.content.match(/\{[\s\S]*\}/)
          if (jsonMatch) {
            agentResult = JSON.parse(jsonMatch[0])
          }
        } catch (e) {
          console.warn('Failed to parse agent response:', e)
        }
      }

      // If agent returned PowerPoint (Presenton.ai with path or local with base64)
      if (agentResult?.status === 'success') {
        // Presenton.ai returns a download path URL
        if (agentResult?.path) {
          // Store the path in metadata for download button
          const assistantMessage: Message = {
            id: message.id,
            role: message.role,
            content: `✅ ${agentResult.message || 'Successfully generated PowerPoint presentation. Click to download.'}`,
            metadata: {
              ...message.metadata,
              // Don't add requested_generation to avoid showing duplicate buttons
              generated: ['ppt'],
              presenton_path: agentResult.path,  // Store download URL
              presentation_id: agentResult.presentation_id,
              edit_path: agentResult.edit_path,
              credits_consumed: agentResult.credits_consumed,
            },
          }
          setMessages((prev) => [...prev, assistantMessage])
          return
        }
        // Local generation returns base64 data
        else if (agentResult?.ppt_data) {
          try {
            // Decode base64 to blob
            const base64Data = agentResult.ppt_data
            const binaryString = atob(base64Data)
            const bytes = new Uint8Array(binaryString.length)
            for (let i = 0; i < binaryString.length; i++) {
              bytes[i] = binaryString.charCodeAt(i)
            }
            const blob = new Blob([bytes], { 
              type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation' 
            })
            
            // Trigger download
            const url = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = agentResult.filename || `presentation_${Date.now()}.pptx`
            document.body.appendChild(a)
            a.click()
            window.URL.revokeObjectURL(url)
            document.body.removeChild(a)
            
            // Update message to show success
            const assistantMessage: Message = {
              id: message.id,
              role: message.role,
              content: `✅ ${agentResult.message || 'PowerPoint presentation generated and downloaded successfully!'}\n\nFilename: ${agentResult.filename || 'presentation.pptx'}`,
              metadata: {
                ...message.metadata,
                requested_generation: requestedTypes,
                generated: ['ppt'],
              },
            }
            setMessages((prev) => [...prev, assistantMessage])
            return
          } catch (downloadError) {
            console.error('Failed to download PowerPoint:', downloadError)
            // Fall through to show the message normally
          }
        }
      }

      // Check if agent returned an error
      if (agentResult?.status === 'error') {
        const assistantMessage: Message = {
          id: message.id,
          role: message.role,
          content: `❌ Error: ${agentResult.message || 'Failed to generate PowerPoint'}`,
          metadata: {
            ...message.metadata,
            requested_generation: requestedTypes,
          },
        }
        setMessages((prev) => [...prev, assistantMessage])
        return
      }

      const assistantMessage: Message = {
        id: message.id,
        role: message.role,
        content: message.content,
        metadata: {
          ...message.metadata,
          requested_generation: requestedTypes,
        },
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (error: any) {
      const errorMessage: Message = {
        id: Date.now(),
        role: 'assistant',
        content: `Error: ${error.response?.data?.detail || 'Failed to send message'}`,
      }
      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const confirmGeneratePPT = async (messageId: number) => {
    const message = messages.find((m) => m.id === messageId)
    if (!message || !message.metadata?.ppt_generation) return

    setGenerating({ messageId, type: 'ppt' })

    try {
      const pptGen = message.metadata.ppt_generation
      // Use the assistant's message content for PowerPoint generation
      const response = await api.post('/api/generate/confirm-ppt', {
        content: message.content, // Use the assistant's response content
        topic: pptGen.topic,
        session_id: pptGen.session_id,
        template_id: pptGen.template_id,
      })

      const agentResult = response.data.agent_result

      // Update the message to show the result
      if (agentResult?.status === 'success') {
        if (agentResult?.path) {
          // Presenton.ai response with download path
          setMessages((prev) =>
            prev.map((m) =>
              m.id === messageId
                ? {
                    ...m,
                    content: `✅ ${agentResult.message || 'Successfully generated PowerPoint presentation. Click to download.'}`,
                    metadata: {
                      ...m.metadata,
                      generated: ['ppt'],
                      presenton_path: agentResult.path,
                      presentation_id: agentResult.presentation_id,
                      edit_path: agentResult.edit_path,
                      credits_consumed: agentResult.credits_consumed,
                      ppt_generation: undefined, // Remove generation metadata
                    },
                  }
                : m
            )
          )
        } else if (agentResult?.ppt_data) {
          // Local generation with base64 data
          try {
            const base64Data = agentResult.ppt_data
            const binaryString = atob(base64Data)
            const bytes = new Uint8Array(binaryString.length)
            for (let i = 0; i < binaryString.length; i++) {
              bytes[i] = binaryString.charCodeAt(i)
            }
            const blob = new Blob([bytes], {
              type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            })

            const url = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = agentResult.filename || `presentation_${Date.now()}.pptx`
            document.body.appendChild(a)
            a.click()
            window.URL.revokeObjectURL(url)
            document.body.removeChild(a)

            setMessages((prev) =>
              prev.map((m) =>
                m.id === messageId
                  ? {
                      ...m,
                      content: `✅ ${agentResult.message || 'PowerPoint presentation generated and downloaded successfully!'}\n\nFilename: ${agentResult.filename || 'presentation.pptx'}`,
                      metadata: {
                        ...m.metadata,
                        generated: ['ppt'],
                        ppt_generation: undefined,
                      },
                    }
                  : m
              )
            )
          } catch (downloadError) {
            console.error('Failed to download PowerPoint:', downloadError)
            setMessages((prev) =>
              prev.map((m) =>
                m.id === messageId
                  ? {
                      ...m,
                      content: `✅ ${agentResult.message || 'PowerPoint generated successfully!'}`,
                      metadata: {
                        ...m.metadata,
                        generated: ['ppt'],
                        ppt_generation: undefined,
                      },
                    }
                  : m
              )
            )
          }
        }
      } else {
        // Error case
        setMessages((prev) =>
          prev.map((m) =>
            m.id === messageId
              ? {
                  ...m,
                  content: `❌ Error: ${agentResult?.message || 'Failed to generate PowerPoint'}`,
                  metadata: {
                    ...m.metadata,
                    ppt_preview: undefined,
                  },
                }
              : m
          )
        )
      }
    } catch (error: any) {
      console.error('Failed to generate PowerPoint:', error)
      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId
            ? {
                ...m,
                content: `❌ Error: ${error.response?.data?.detail || 'Failed to generate PowerPoint'}`,
                metadata: {
                  ...m.metadata,
                  ppt_preview: undefined,
                },
              }
            : m
        )
      )
    } finally {
      setGenerating(null)
    }
  }

  const cancelGeneratePPT = (messageId: number) => {
    // Remove the generation metadata and just show the content without confirmation buttons
    setMessages((prev) =>
      prev.map((m) =>
        m.id === messageId
          ? {
              ...m,
              metadata: {
                ...m.metadata,
                ppt_generation: undefined,
              },
            }
          : m
      )
    )
  }

  const generateDocument = async (messageId: number, type: string) => {
    const message = messages.find((m) => m.id === messageId)
    if (!message) return

    setGenerating({ messageId, type })

    try {
      const userMessage = messages.find((m, idx) => 
        idx < messages.findIndex(msg => msg.id === messageId) && m.role === 'user'
      )
      const topic = userMessage?.content || 'Business Content'

      const templateId = (type === 'ppt' || type === 'mp4') ? ciscoTemplateId : undefined
      
      // For podcast and video, use the script from metadata if available, otherwise use message content
      let content = message.content
      if (type === 'podcast' && message.metadata?.podcast_generation?.script) {
        content = message.metadata.podcast_generation.script
      } else if (type === 'mp4' && message.metadata?.video_generation?.script) {
        content = message.metadata.video_generation.script
      }
      
      // Determine topic based on type
      let finalTopic = topic
      if (type === 'podcast' && message.metadata?.podcast_generation?.topic) {
        finalTopic = message.metadata.podcast_generation.topic
      } else if (type === 'speech' && message.metadata?.speech_generation?.topic) {
        finalTopic = message.metadata.speech_generation.topic
      } else if (type === 'doc' && message.metadata?.doc_generation?.topic) {
        finalTopic = message.metadata.doc_generation.topic
      } else if (type === 'mp4' && message.metadata?.video_generation?.topic) {
        finalTopic = message.metadata.video_generation.topic
      }
      
      const response = await api.post(
        '/api/generate/document',
        {
          content: content,
          type: type,
          session_id: sessionId,
          topic: finalTopic,
          template_id: templateId,
        },
        {
          responseType: 'blob',
        }
      )

      const url = window.URL.createObjectURL(response.data)
      const a = document.createElement('a')
      a.href = url
      const extension = 
        type === 'ppt' ? 'pptx' : 
        type === 'mp4' ? 'mp4' : 
        type === 'doc' ? 'docx' : 
        type === 'pdf' ? 'pdf' :
        type === 'speech' ? 'mp3' :
        type === 'podcast' ? 'mp3' :
        'txt'
      a.download = `generated_${type}_${Date.now()}.${extension}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId
            ? {
                ...m,
                metadata: {
                  ...m.metadata,
                  generated: [...(m.metadata?.generated || []), type],
                },
              }
            : m
        )
      )
    } catch (error: any) {
      alert(`Failed to generate ${type}: ${error.response?.data?.detail || 'Unknown error'}`)
    } finally {
      setGenerating(null)
    }
  }

  const getModelIcon = (modelName: string) => {
    if (modelName.toLowerCase().includes('gpt') || modelName.toLowerCase().includes('openai')) {
      return <Bot className="w-4 h-4" />
    }
    if (modelName.toLowerCase().includes('claude')) {
      return <Sparkles className="w-4 h-4" />
    }
    return <Bot className="w-4 h-4" />
  }

  // Always use GPT-4.1 (Cisco) - no model selection needed
  const selectedModelName = 'GPT-4.1 (Cisco)'

  return (
    <div className="flex flex-col h-full bg-transparent">
      {/* Header */}
      <div className="border-b border-slate-700/50 bg-slate-800/30 px-6 py-4 backdrop-blur-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {onNewChat && (
              <button
                onClick={onNewChat}
                className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors text-gray-300 hover:text-white"
                title="New Chat"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
            )}
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-br from-cyan-400 to-blue-600 rounded-lg flex items-center justify-center">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">
                  GPT-4.1 (Cisco)
                </h2>
                <p className="text-sm text-gray-400">
                  {currentChatTitle || 'New Chat'} • {messages.length} messages
                </p>
              </div>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'} ${isConnected ? 'animate-pulse' : ''}`}></div>
            <span className="text-xs text-gray-400">{isConnected ? 'Connected' : 'Disconnected'}</span>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6 bg-transparent">
        {messages.length === 0 && (
          <div className="text-center text-gray-400 mt-12">
            <Bot className="mx-auto mb-4 text-cyan-400" size={48} />
            <p className="text-lg font-medium mb-2 text-white">Welcome to AGENT</p>
            <p className="text-sm mb-4 text-gray-400">I can help with analysis, insights, document creation, presentations, and more.</p>
            <div className="max-w-2xl mx-auto space-y-2 text-sm">
              <div className="bg-gray-300/10 p-3 rounded-lg border border-gray-400/15 text-gray-400">
                "I have a client with challenges on zone based segmentation - what is my best pitch?"
              </div>
              <div className="bg-gray-300/10 p-3 rounded-lg border border-gray-400/15 text-gray-400">
                "Explain to me what is hybrid mesh firewall and how Cisco can help?"
              </div>
              <div className="bg-gray-300/10 p-3 rounded-lg border border-gray-400/15 text-gray-400">
                "Tell me about AI model protection and give me ideas to pitch it using powerpoint"
              </div>
              <div className="bg-gray-300/10 p-3 rounded-lg border border-gray-400/15 text-gray-400">
                "Please generate a demo video for SnortML"
              </div>
              <div className="bg-gray-300/10 p-3 rounded-lg border border-gray-400/15 text-gray-400">
                "Create a podcast about AI protection use cases"
              </div>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div className={`max-w-3xl ${message.role === 'user' ? 'flex flex-col items-end' : 'flex flex-col items-start'}`}>
              <div
                className={`rounded-2xl px-5 py-3 ${
                  message.role === 'user'
                    ? 'bg-gradient-to-r from-cyan-500 to-blue-600 text-white'
                    : 'bg-slate-800/70 text-gray-200 border border-slate-700/50 shadow-lg backdrop-blur-sm'
                }`}
              >
                <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
              </div>

              {/* Podcast Generation Button */}
              {message.role === 'assistant' && message.metadata?.podcast_generation && message.metadata.podcast_generation.ready_for_mp3 && (
                <div className="mt-3 flex items-center gap-3">
                  <button
                    onClick={() => generateDocument(message.id, 'podcast')}
                    disabled={generating?.messageId === message.id && generating?.type === 'podcast'}
                    className="flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-cyan-400 border border-cyan-400/30 hover:from-cyan-500/30 hover:to-blue-600/30 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {generating?.messageId === message.id && generating?.type === 'podcast' ? (
                      <>
                        <Loader2 className="animate-spin" size={16} />
                        <span>Generating MP3...</span>
                      </>
                    ) : (
                      <>
                        <Users size={16} />
                        <span>Generate Podcast MP3</span>
                      </>
                    )}
                  </button>
                </div>
              )}

              {/* Speech Generation Button */}
              {message.role === 'assistant' && message.metadata?.speech_generation && message.metadata.speech_generation.ready_for_mp3 && (
                <div className="mt-3 flex items-center gap-3">
                  <button
                    onClick={() => generateDocument(message.id, 'speech')}
                    disabled={generating?.messageId === message.id && generating?.type === 'speech'}
                    className="flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-cyan-400 border border-cyan-400/30 hover:from-cyan-500/30 hover:to-blue-600/30 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {generating?.messageId === message.id && generating?.type === 'speech' ? (
                      <>
                        <Loader2 className="animate-spin" size={16} />
                        <span>Generating MP3...</span>
                      </>
                    ) : (
                      <>
                        <Mic2 size={16} />
                        <span>Generate Speech MP3</span>
                      </>
                    )}
                  </button>
                </div>
              )}

              {/* Document Generation Button */}
              {message.role === 'assistant' && message.metadata?.doc_generation && message.metadata.doc_generation.ready_for_doc && (
                <div className="mt-3 flex items-center gap-3">
                  <button
                    onClick={() => generateDocument(message.id, 'doc')}
                    disabled={generating?.messageId === message.id && generating?.type === 'doc'}
                    className="flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-cyan-400 border border-cyan-400/30 hover:from-cyan-500/30 hover:to-blue-600/30 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {generating?.messageId === message.id && generating?.type === 'doc' ? (
                      <>
                        <Loader2 className="animate-spin" size={16} />
                        <span>Generating Document...</span>
                      </>
                    ) : (
                      <>
                        <FileText size={16} />
                        <span>Generate Document</span>
                      </>
                    )}
                  </button>
                </div>
              )}

              {/* Video Generation Button - DISABLED: Only demo videos are available */}
              {/* Removed: Video generation via HeyGen is disabled in production */}

              {/* PowerPoint Generation Confirmation */}
              {message.role === 'assistant' && message.metadata?.ppt_generation && (
                <div className="mt-3 flex items-center gap-3">
                  <button
                    onClick={() => confirmGeneratePPT(message.id)}
                    disabled={generating?.messageId === message.id && generating?.type === 'ppt'}
                    className="flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-cyan-400 border border-cyan-400/30 hover:from-cyan-500/30 hover:to-blue-600/30 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {generating?.messageId === message.id && generating?.type === 'ppt' ? (
                      <>
                        <Loader2 className="animate-spin" size={16} />
                        <span>Generating...</span>
                      </>
                    ) : (
                      <>
                        <Presentation size={16} />
                        <span>Yes, generate PowerPoint</span>
                      </>
                    )}
                  </button>
                  <button
                    onClick={() => cancelGeneratePPT(message.id)}
                    disabled={generating?.messageId === message.id && generating?.type === 'ppt'}
                    className="px-4 py-2 rounded-lg text-sm font-medium bg-slate-700/50 text-gray-300 border border-slate-600/50 hover:bg-slate-700/70 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    No, continue conversation
                  </button>
                </div>
              )}

              {/* Generation Options - Only show if NOT using Presenton.ai (no presenton_path) */}
              {message.role === 'assistant' && 
               message.metadata?.requested_generation && 
               message.metadata.requested_generation.length > 0 &&
               !message.metadata?.presenton_path && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {generationOptions
                    .filter(option => {
                      // Hide "Generate Video" option - video generation is disabled
                      if (option.type === 'mp4') {
                        return false
                      }
                      // Hide "Generate Video" option if videos are already available in metadata
                      if (option.type === 'mp4' && message.metadata?.videos && message.metadata.videos.length > 0) {
                        return false
                      }
                      return message.metadata?.requested_generation?.includes(option.type)
                    })
                    .map((option) => {
                      const isGenerating = generating?.messageId === message.id && generating?.type === option.type
                      const isGenerated = message.metadata?.generated?.includes(option.type)
                      
                      return (
                        <button
                          key={option.type}
                          onClick={() => generateDocument(message.id, option.type)}
                          disabled={isGenerating}
                          className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                            isGenerated
                              ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                              : 'bg-slate-800/70 text-gray-300 border border-slate-700/50 hover:bg-slate-700/70 hover:border-cyan-500/50 shadow-sm'
                          } disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                          {isGenerating ? (
                            <>
                              <Loader2 className="animate-spin" size={16} />
                              <span>Generating...</span>
                            </>
                          ) : (
                            <>
                              {option.icon}
                              <span>
                                {isGenerated ? `Download ${option.label}` : `Generate ${option.label}`}
                              </span>
                              {isGenerated && <Download size={14} />}
                            </>
                          )}
                        </button>
                      )
                    })}
                </div>
              )}

              {/* Video Watch Buttons - Render buttons for demo videos */}
              {message.role === 'assistant' && message.metadata?.videos && message.metadata.videos.length > 0 && (
                <div className="mt-3 flex flex-col gap-2">
                  {message.metadata.videos.map((video: any, index: number) => (
                    <button
                      key={video.video_id || index}
                      onClick={() => {
                        // Open YouTube video in new tab
                        window.open(video.url, '_blank', 'noopener,noreferrer')
                      }}
                      className="flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium bg-gradient-to-r from-red-500/20 to-red-600/20 text-red-400 border border-red-400/30 hover:from-red-500/30 hover:to-red-600/30 transition-all shadow-sm w-fit"
                    >
                      <Video size={16} />
                      <span>Watch Demo Video{message.metadata.videos.length > 1 ? ` ${index + 1}` : ''}</span>
                    </button>
                  ))}
                </div>
              )}

              {/* Presenton.ai Download Button - Single download button */}
              {message.role === 'assistant' && message.metadata?.presenton_path && (
                <div className="mt-3 flex items-center gap-2">
                  <button
                    onClick={async () => {
                      try {
                        const downloadPath = message.metadata.presenton_path
                        // Download directly from Presenton.ai URL
                        const response = await fetch(downloadPath)
                        if (!response.ok) throw new Error('Download failed')
                        const blob = await response.blob()
                        const url = window.URL.createObjectURL(blob)
                        const a = document.createElement('a')
                        a.href = url
                        a.download = message.metadata.presentation_id 
                          ? `presentation_${message.metadata.presentation_id}.pptx`
                          : `presentation_${Date.now()}.pptx`
                        document.body.appendChild(a)
                        a.click()
                        window.URL.revokeObjectURL(url)
                        document.body.removeChild(a)
                      } catch (error) {
                        console.error('Failed to download from Presenton.ai:', error)
                        alert('Failed to download PowerPoint. Please try again.')
                      }
                    }}
                    className="flex items-center space-x-2 px-4 py-2 rounded-lg text-sm font-medium bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-cyan-400 border border-cyan-400/30 hover:from-cyan-500/30 hover:to-blue-600/30 transition-all shadow-sm"
                  >
                    <Download size={16} />
                    <span>Download PowerPoint</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-800/70 rounded-2xl px-5 py-3 border border-slate-700/50 shadow-lg backdrop-blur-sm">
              <Loader2 className="animate-spin text-cyan-400" size={20} />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-slate-700/50 bg-slate-800/30 p-4 backdrop-blur-sm">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            sendMessage()
          }}
          className="flex space-x-3 max-w-4xl mx-auto"
        >
          <button
            type="button"
            className="p-3 text-gray-400 hover:text-white hover:bg-slate-700/50 rounded-lg transition-colors"
            title="Upload to neural database"
          >
            <FileText className="w-5 h-5" />
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Hi! How can I assist you today?"
            className="flex-1 px-4 py-3 bg-slate-800/70 border border-slate-700/50 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/50"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-6 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white rounded-lg hover:from-cyan-400 hover:to-blue-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 font-medium shadow-lg shadow-cyan-500/30"
          >
            <Send size={20} />
            <span>Send</span>
          </button>
        </form>
        
        {/* Quick Action Buttons */}
        <div className="flex items-center justify-center gap-2 mt-3 max-w-4xl mx-auto">
          <button
            onClick={() => setSelectedContentType(selectedContentType === 'doc' ? null : 'doc')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 ${
              selectedContentType === 'doc'
                ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-cyan-400 border border-cyan-400/30'
                : 'bg-slate-800/50 text-gray-300 border border-slate-700/50 hover:bg-slate-700/50 hover:border-cyan-500/30'
            }`}
          >
            <FileText size={16} />
            <span>Document</span>
          </button>
          <button
            onClick={() => setSelectedContentType(selectedContentType === 'ppt' ? null : 'ppt')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 ${
              selectedContentType === 'ppt'
                ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-cyan-400 border border-cyan-400/30'
                : 'bg-slate-800/50 text-gray-300 border border-slate-700/50 hover:bg-slate-700/50 hover:border-cyan-500/30'
            }`}
          >
            <Presentation size={16} />
            <span>Presentation</span>
          </button>
          <button
            onClick={() => setSelectedContentType(selectedContentType === 'mp4' ? null : 'mp4')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 ${
              selectedContentType === 'mp4'
                ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-cyan-400 border border-cyan-400/30'
                : 'bg-slate-800/50 text-gray-300 border border-slate-700/50 hover:bg-slate-700/50 hover:border-cyan-500/30'
            }`}
          >
            <Video size={16} />
            <span>Video</span>
          </button>
          <button
            onClick={() => setSelectedContentType(selectedContentType === 'podcast' ? null : 'podcast')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 ${
              selectedContentType === 'podcast'
                ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-cyan-400 border border-cyan-400/30'
                : 'bg-slate-800/50 text-gray-300 border border-slate-700/50 hover:bg-slate-700/50 hover:border-cyan-500/30'
            }`}
          >
            <Users size={16} />
            <span>Podcast</span>
          </button>
          <button
            onClick={() => setSelectedContentType(selectedContentType === 'speech' ? null : 'speech')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center space-x-2 ${
              selectedContentType === 'speech'
                ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-cyan-400 border border-cyan-400/30'
                : 'bg-slate-800/50 text-gray-300 border border-slate-700/50 hover:bg-slate-700/50 hover:border-cyan-500/30'
            }`}
          >
            <Mic2 size={16} />
            <span>Speech</span>
          </button>
        </div>
        
        {/* Disclaimer and Feedback */}
        <div className="flex items-center justify-center gap-3 mt-2 max-w-4xl mx-auto text-xs text-gray-400">
          <span>AGENT strives for accuracy but can be wrong. Please review results carefully.</span>
          <button
            onClick={() => {
              // Placeholder for feedback functionality
              console.log('Share feedback clicked')
            }}
            className="text-cyan-400 hover:text-cyan-300 underline transition-colors"
          >
            Share feedback
          </button>
        </div>
      </div>
    </div>
  )
}
