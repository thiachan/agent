'use client'

import { useState, useEffect, useRef } from 'react'
import { Upload, File, Trash2, Loader2, CheckCircle2, XCircle, Plus, X, FileText, Edit, Calendar, User, Folder } from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import api from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'

interface Document {
  id: number
  filename: string
  title: string
  file_type: string
  status: string
  file_size: number
  created_at: string
  tags?: string
  owner: {
    id: number
    full_name: string
  }
}

interface KnowledgeBase {
  id: number
  kb_id: string
  name: string
  description: string
  documents: Document[]
  created_at: string
  updated_at: string
  document_count?: number
}

interface UploadProgress {
  fileName: string
  progress: number
  status: 'uploading' | 'processing' | 'completed' | 'error'
  error?: string
}

// Default KBs will be created on first load if none exist

export function DocumentUpload() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<Map<string, UploadProgress>>(new Map())
  const [selectedKB, setSelectedKB] = useState<string | null>(null)
  const [showNewKBModal, setShowNewKBModal] = useState(false)
  const [editingKB, setEditingKB] = useState<string | null>(null)
  const [newKBName, setNewKBName] = useState('')
  const [newKBDescription, setNewKBDescription] = useState('')
  const [showDocumentsView, setShowDocumentsView] = useState(false)
  const { isAuthenticated } = useAuthStore()
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null)

  const fetchKnowledgeBases = async () => {
    try {
      const response = await api.get('/api/knowledge-bases/')
      let kbs = response.data || []
      
      // If no KBs exist, create default ones
      if (kbs.length === 0) {
        const defaultKBs = [
          { name: 'Financial Reports', description: 'Q1-Q4 financial reports, projections, and analysis.' },
          { name: 'Market Data', description: 'Market research reports and demographic analysis.' },
          { name: 'Legal & Compliance', description: 'Legal documents and compliance guidelines.' }
        ]
        
        for (const kbData of defaultKBs) {
          try {
            await api.post('/api/knowledge-bases/', kbData)
          } catch (error) {
            console.error('Failed to create default KB:', error)
          }
        }
        
        // Fetch again
        const retryResponse = await api.get('/api/knowledge-bases/')
        kbs = retryResponse.data || []
      }
      
      setKnowledgeBases(kbs.map((kb: any) => ({
        ...kb,
        documents: []
      })))
    } catch (error) {
      console.error('Failed to fetch knowledge bases:', error)
    }
  }

  const fetchDocuments = async (showLoading: boolean = true) => {
    if (showLoading) {
      setLoading(true)
    }
    try {
      const response = await api.get('/api/upload/')
      if (response.data && response.data.items) {
        const docs = response.data.items
        setDocuments(docs)
        
        // Organize documents by knowledge base (using tags)
        setKnowledgeBases(prev => {
          // Only organize if we have knowledge bases
          if (prev.length === 0) {
            return prev
          }
          
          const organized: { [key: string]: Document[] } = {}
          prev.forEach(kb => {
            organized[kb.kb_id] = []
          })
          
          docs.forEach((doc: Document) => {
            const tags = doc.tags ? doc.tags.split(',').map(t => t.trim()) : []
            let assigned = false
            
            // Check if document has a KB tag
            prev.forEach(kb => {
              if (tags.includes(kb.kb_id) || tags.includes(kb.name.toLowerCase())) {
                organized[kb.kb_id].push(doc)
                assigned = true
              }
            })
            
            // If not assigned, put in first KB as default
            if (!assigned && prev.length > 0 && organized[prev[0].kb_id]) {
              organized[prev[0].kb_id].push(doc)
            }
          })
          
          return prev.map(kb => ({
            ...kb,
            documents: organized[kb.kb_id] || []
          }))
        })
      } else {
        setDocuments([])
      }
    } catch (error: any) {
      console.error('Failed to fetch documents:', error)
      setDocuments([])
    } finally {
      if (showLoading) {
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    if (!isAuthenticated) return
    fetchKnowledgeBases().then(() => {
      fetchDocuments()
    })
  }, [isAuthenticated])

  useEffect(() => {
    if (refreshIntervalRef.current) {
      clearInterval(refreshIntervalRef.current)
      refreshIntervalRef.current = null
    }
    
    if (!isAuthenticated) return
    
    const hasProcessingDocs = documents.some(doc => 
      doc.status === 'processing' || doc.status === 'uploading'
    )
    
    if (hasProcessingDocs) {
      refreshIntervalRef.current = setInterval(() => {
        const token = localStorage.getItem('auth_token')
        if (token) {
          fetchDocuments()
        }
      }, 10000)
    }
    
    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current)
      }
    }
  }, [isAuthenticated, documents])

  const assignToKnowledgeBase = async (docId: number, kbId: string) => {
    try {
      // Update document tags to include knowledge base
      const doc = documents.find(d => d.id === docId)
      if (!doc) return
      
      const kb = knowledgeBases.find(k => k.kb_id === kbId)
      if (!kb) return
      
      const existingTags = doc.tags ? doc.tags.split(',').map(t => t.trim()) : []
      const newTags = [...existingTags.filter(t => !knowledgeBases.some(k => k.kb_id === t || k.name.toLowerCase() === t)), kb.kb_id]
      
      // Note: This would require a PATCH endpoint to update document tags
      // For now, we'll just update local state
      setKnowledgeBases(prev => prev.map(kb => ({
        ...kb,
        documents: kb.kb_id === kbId 
          ? [...kb.documents, doc]
          : kb.documents.filter(d => d.id !== docId)
      })))
    } catch (error) {
      console.error('Failed to assign document to knowledge base:', error)
    }
  }

  const onDrop = async (acceptedFiles: File[]) => {
    if (!isAuthenticated) {
      alert('Please log in to upload files')
      return
    }
    
    // Use selected KB or default to first KB
    const targetKB = selectedKB || (knowledgeBases.length > 0 ? knowledgeBases[0].kb_id : null)
    
    if (!targetKB) {
      alert('Please create a knowledge base first')
      return
    }
    
    // Auto-select the KB if not already selected
    if (!selectedKB && knowledgeBases.length > 0) {
      setSelectedKB(knowledgeBases[0].kb_id)
    }
    
    for (const file of acceptedFiles) {
      setUploading(true)
      const fileId = `${file.name}-${Date.now()}`
      
      setUploadProgress(prev => {
        const newMap = new Map(prev)
        newMap.set(fileId, {
          fileName: file.name,
          progress: 0,
          status: 'uploading'
        })
        return newMap
      })

      const formData = new FormData()
      formData.append('file', file)
      formData.append('title', file.name)
      formData.append('is_public', 'false')
      // Add knowledge base as tag
      const kb = knowledgeBases.find(k => k.kb_id === targetKB)
      if (kb) {
        formData.append('tags', kb.kb_id)
      }

      try {
        console.log(`[Upload] Starting upload for file: ${file.name} to KB: ${targetKB}`)
        const response = await api.post('/api/upload/', formData, {
          onUploadProgress: (progressEvent) => {
            if (progressEvent.total) {
              const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
              setUploadProgress(prev => {
                const newMap = new Map(prev)
                const current = newMap.get(fileId)
                if (current) {
                  newMap.set(fileId, {
                    ...current,
                    progress: Math.min(progress, 90)
                  })
                }
                return newMap
              })
            }
          }
        })

        console.log(`[Upload] Upload successful for ${file.name}:`, response.data)

        setUploadProgress(prev => {
          const newMap = new Map(prev)
          const current = newMap.get(fileId)
          if (current) {
            newMap.set(fileId, {
              ...current,
              progress: 95,
              status: 'processing'
            })
          }
          return newMap
        })

        // Refresh knowledge bases first, then documents (to ensure KBs are loaded before organizing docs)
        // Don't show loading spinner during upload refresh to avoid UI flicker
        await fetchKnowledgeBases()
        await fetchDocuments(false) // Don't show loading spinner

        const pollForCompletion = async () => {
          let attempts = 0
          const maxAttempts = 60
          
          const checkStatus = async () => {
            try {
              const docsResponse = await api.get('/api/upload/')
              const uploadedDoc = docsResponse.data.items.find(
                (doc: Document) => doc.filename === file.name
              )
              
              if (uploadedDoc) {
                if (uploadedDoc.status === 'processed') {
                  setUploadProgress(prev => {
                    const newMap = new Map(prev)
                    const current = newMap.get(fileId)
                    if (current) {
                      newMap.set(fileId, {
                        ...current,
                        progress: 100,
                        status: 'completed'
                      })
                    }
                    return newMap
                  })
                  
                  setTimeout(() => {
                    setUploadProgress(prev => {
                      const newMap = new Map(prev)
                      newMap.delete(fileId)
                      return newMap
                    })
                  }, 3000)
                  return
                } else if (uploadedDoc.status === 'failed') {
                  setUploadProgress(prev => {
                    const newMap = new Map(prev)
                    const current = newMap.get(fileId)
                    if (current) {
                      newMap.set(fileId, {
                        ...current,
                        status: 'error',
                        error: 'Processing failed'
                      })
                    }
                    return newMap
                  })
                  return
                }
              }
              
              attempts++
              if (attempts < maxAttempts) {
                setTimeout(checkStatus, 3000)
              }
            } catch (error) {
              console.error('Error checking document status:', error)
            }
          }
          
          setTimeout(checkStatus, 2000)
        }
        
        pollForCompletion()

      } catch (error: any) {
        console.error(`[Upload] Failed to upload ${file.name}:`, error)
        console.error('Error details:', {
          status: error.response?.status,
          data: error.response?.data,
          message: error.message
        })
        
        const errorMessage = error.response?.data?.detail || error.message || 'Upload failed'
        setUploadProgress(prev => {
          const newMap = new Map(prev)
          const current = newMap.get(fileId)
          if (current) {
            newMap.set(fileId, {
              ...current,
              status: 'error',
              error: errorMessage
            })
          }
          return newMap
        })
        
        alert(`Upload failed for ${file.name}: ${errorMessage}`)
      } finally {
        setUploading(false)
      }
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxSize: 100 * 1024 * 1024,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.ms-powerpoint': ['.ppt'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'video/mp4': ['.mp4'],
      'video/quicktime': ['.mov'],
      'video/x-msvideo': ['.avi'],
      'audio/mpeg': ['.mp3'],
      'audio/wav': ['.wav'],
      'audio/x-m4a': ['.m4a'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
      'text/csv': ['.csv'],
      'application/json': ['.json'],
      'application/x-ndjson': ['.jsonl'],
    },
  })

  const deleteDocument = async (id: number) => {
    if (!confirm('Are you sure you want to delete this document?')) return

    try {
      await api.delete(`/api/upload/${id}`)
      // Refresh without showing loading spinner
      await fetchDocuments(false)
    } catch (error) {
      alert('Failed to delete document.')
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' })
  }

  const formatDateTime = (dateString: string): string => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getDocumentCategory = (doc: Document): string => {
    // Try to find which KB this document belongs to
    const tags = doc.tags ? doc.tags.split(',').map(t => t.trim()) : []
    for (const kb of knowledgeBases) {
      if (tags.includes(kb.kb_id) || tags.includes(kb.name.toLowerCase())) {
        return kb.name
      }
    }
    // If no KB found, use first tag or "Uncategorized"
    return tags.length > 0 ? tags[0] : 'Uncategorized'
  }

  const getDocumentPermission = (doc: Document): string => {
    // Check if current user is the owner
    const { user } = useAuthStore.getState()
    if (user && doc.owner && user.id === doc.owner.id) {
      return 'Owner'
    }
    return 'Viewer'
  }

  const createKnowledgeBase = async () => {
    if (!newKBName.trim()) return
    
    try {
      const response = await api.post('/api/knowledge-bases/', {
        name: newKBName,
        description: newKBDescription || undefined
      })
      
      setKnowledgeBases(prev => [...prev, {
        ...response.data,
        documents: []
      }])
      setNewKBName('')
      setNewKBDescription('')
      setShowNewKBModal(false)
    } catch (error: any) {
      console.error('Failed to create knowledge base:', error)
      alert(error.response?.data?.detail || 'Failed to create knowledge base')
    }
  }

  const updateKnowledgeBase = async () => {
    if (!editingKB || !newKBName.trim()) return
    
    const oldKB = knowledgeBases.find(kb => kb.kb_id === editingKB)
    if (!oldKB) return
    
    try {
      const response = await api.put(`/api/knowledge-bases/${editingKB}`, {
        name: newKBName,
        description: newKBDescription || undefined
      })
      
      setKnowledgeBases(prev => prev.map(kb => 
        kb.kb_id === editingKB
          ? { ...response.data, documents: kb.documents }
          : kb
      ))
      
      // Update selection if KB ID changed
      if (selectedKB === editingKB && response.data.kb_id !== editingKB) {
        setSelectedKB(response.data.kb_id)
      }
      
      // Refresh documents to get updated tags (without loading spinner)
      await fetchDocuments(false)
      
      setNewKBName('')
      setNewKBDescription('')
      setEditingKB(null)
    } catch (error: any) {
      console.error('Failed to update knowledge base:', error)
      alert(error.response?.data?.detail || 'Failed to update knowledge base')
    }
  }

  const deleteKnowledgeBase = async (kbId: string) => {
    const kb = knowledgeBases.find(k => k.kb_id === kbId)
    if (!kb) return
    
    // Don't allow deleting the last knowledge base
    if (knowledgeBases.length <= 1) {
      alert('Cannot delete the last knowledge base. Please create another one first.')
      return
    }
    
    if (kb.documents.length > 0) {
      if (!confirm(`This knowledge base contains ${kb.documents.length} document(s). Are you sure you want to delete it? Documents will be moved to another knowledge base.`)) {
        return
      }
    } else {
      if (!confirm(`Are you sure you want to delete "${kb.name}"?`)) {
        return
      }
    }
    
    try {
      // Find target KB to move documents to
      const targetKB = knowledgeBases.find(k => k.kb_id !== kbId)
      await api.delete(`/api/knowledge-bases/${kbId}${targetKB ? `?target_kb_id=${targetKB.kb_id}` : ''}`)
      
      setKnowledgeBases(prev => prev.filter(k => k.kb_id !== kbId))
      
      // Clear selection if deleted KB was selected, or select first available KB
      if (selectedKB === kbId) {
        const remainingKB = knowledgeBases.find(k => k.kb_id !== kbId)
        setSelectedKB(remainingKB?.kb_id || null)
      }
      
      // Refresh documents to get updated tags (without loading spinner)
      await fetchDocuments(false)
    } catch (error: any) {
      console.error('Failed to delete knowledge base:', error)
      alert(error.response?.data?.detail || 'Failed to delete knowledge base')
    }
  }

  const startEditKB = (kb: KnowledgeBase) => {
    setEditingKB(kb.kb_id)
    setNewKBName(kb.name)
    setNewKBDescription(kb.description || '')
  }

  return (
    <div className="h-full flex flex-col bg-transparent overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-700/50 bg-slate-800/30 backdrop-blur-sm flex-shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Knowledge Bases</h1>
            <p className="text-sm text-gray-400 mt-1">Manage your document collections and training data.</p>
          </div>
          <div className="flex items-center space-x-3">
            <button 
              onClick={() => setShowDocumentsView(!showDocumentsView)}
              className={`px-4 py-2 text-sm rounded-lg transition-colors flex items-center space-x-2 ${
                showDocumentsView 
                  ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-white border border-cyan-400/30' 
                  : 'text-gray-300 hover:text-white hover:bg-slate-700/50'
              }`}
            >
              <FileText className="w-4 h-4" />
              <span>Documents</span>
            </button>
            <button
              onClick={() => setShowNewKBModal(true)}
              className="px-4 py-2 text-sm bg-gradient-to-r from-pink-500 to-purple-600 text-white rounded-lg hover:from-pink-400 hover:to-purple-500 transition-all font-medium flex items-center space-x-2 shadow-lg shadow-pink-500/20"
            >
              <Plus className="w-4 h-4" />
              <span>New Knowledge Base</span>
            </button>
          </div>
        </div>
      </div>

      {/* Scrollable Content */}
      <div className="flex-1 overflow-y-auto px-6 py-6 min-h-0">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="animate-spin text-cyan-400" size={32} />
          </div>
        ) : showDocumentsView ? (
          /* Documents List View */
          <div className="max-w-7xl mx-auto">
            <div className="bg-slate-800/70 backdrop-blur-sm rounded-lg border border-slate-700/50 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-slate-900/50 border-b border-slate-700/50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">File Name</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">File Size</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Permission</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Category</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Upload Date</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-400 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700/50">
                    {documents.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="px-6 py-8 text-center text-gray-400">
                          No documents uploaded yet
                        </td>
                      </tr>
                    ) : (
                      documents.map((doc) => (
                        <tr key={doc.id} className="hover:bg-slate-800/50 transition-colors">
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center space-x-2">
                              <File className="w-4 h-4 text-cyan-400" />
                              <span className="text-sm text-white" title={doc.filename || doc.title}>
                                {doc.title || doc.filename}
                              </span>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className="text-sm text-gray-300">{formatFileSize(doc.file_size)}</span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center space-x-1">
                              <User className="w-4 h-4 text-gray-400" />
                              <span className="text-sm text-gray-300">{getDocumentPermission(doc)}</span>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center space-x-1">
                              <Folder className="w-4 h-4 text-gray-400" />
                              <span className="text-sm text-gray-300">{getDocumentCategory(doc)}</span>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center space-x-1">
                              <Calendar className="w-4 h-4 text-gray-400" />
                              <span className="text-sm text-gray-300">{formatDateTime(doc.created_at)}</span>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            {doc.status === 'processed' ? (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-500/20 text-green-400">
                                Processed
                              </span>
                            ) : doc.status === 'processing' ? (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-500/20 text-yellow-400">
                                Processing
                              </span>
                            ) : (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-500/20 text-gray-400">
                                {doc.status || 'Pending'}
                              </span>
                            )}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                            <button
                              onClick={() => deleteDocument(doc.id)}
                              className="text-red-400 hover:text-red-300 transition-colors"
                              title="Delete document"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : (
          /* Knowledge Bases Grid View */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {knowledgeBases.map((kb) => (
              <div
                key={kb.kb_id}
                className="bg-slate-800/70 backdrop-blur-sm rounded-lg border border-slate-700/50 p-5 hover:border-cyan-500/50 transition-all group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center space-x-2 flex-1 min-w-0">
                    <CheckCircle2 className="text-green-500 w-5 h-5 flex-shrink-0" />
                    <h3 className="text-lg font-semibold text-white truncate">{kb.name}</h3>
                  </div>
                  <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={(e) => {
                      e.stopPropagation()
                      startEditKB(kb)
                    }}
                      className="p-1.5 hover:bg-slate-700/50 rounded transition-colors text-gray-400 hover:text-cyan-400"
                      title="Rename"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(e) => {
                      e.stopPropagation()
                      deleteKnowledgeBase(kb.kb_id)
                    }}
                      className="p-1.5 hover:bg-red-500/20 rounded transition-colors text-gray-400 hover:text-red-400"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                
                <div className="mb-3">
                  <span className="text-xs text-green-400 font-medium">Processed</span>
                </div>
                
                <p className="text-sm text-gray-400 mb-4">{kb.description}</p>
                
                <div className="mb-4 space-y-2">
                  <div className="text-sm text-gray-300">
                    Documents: <span className="font-medium">{kb.documents.length}</span>
                  </div>
                  <div className="text-sm text-gray-300">
                    Status: <span className={kb.documents.length === 0 ? 'text-gray-500' : 'text-green-400'}>
                      {kb.documents.length === 0 ? 'Empty' : 'Active'}
                    </span>
                  </div>
                </div>
                
                <div className="mb-4">
                  <button
                    onClick={() => setSelectedKB(selectedKB === kb.kb_id ? null : kb.kb_id)}
                    className={`w-full px-3 py-2 text-sm rounded-lg transition-colors ${
                      selectedKB === kb.kb_id
                        ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                        : 'bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 border border-blue-500/30'
                    }`}
                  >
                    ↑ Add Docs
                  </button>
                </div>
                
                {/* Documents Grid */}
                {kb.documents.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-slate-700/50">
                    <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                      {kb.documents.map((doc) => (
                        <div
                          key={doc.id}
                          className="bg-slate-900/50 rounded p-2 border border-slate-700/30 hover:border-cyan-500/50 transition-all group"
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                              <p 
                                className="text-xs font-medium text-white truncate cursor-help" 
                                title={doc.filename || doc.title}
                              >
                                {doc.title}
                              </p>
                              <p className="text-xs text-gray-500 mt-1">{formatFileSize(doc.file_size)}</p>
                            </div>
                            <button
                              onClick={() => deleteDocument(doc.id)}
                              className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-500/20 rounded transition-all"
                            >
                              <Trash2 className="w-3 h-3 text-red-400" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                <div className="mt-4 pt-4 border-t border-slate-700/50">
                  <p className="text-xs text-gray-500">Created: {formatDate(kb.created_at)}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Upload Area - Fixed at bottom (always visible if KBs exist) */}
      {knowledgeBases.length > 0 && (
        <div className="border-t border-slate-700/50 bg-slate-800/50 backdrop-blur-sm p-4 flex-shrink-0">
          <div className="max-w-4xl mx-auto">
            <div className="flex items-center justify-between mb-3">
              <div>
                <p className="text-sm font-medium text-white">
                  {selectedKB ? (
                    <>Uploading to: <span className="text-cyan-400">{knowledgeBases.find(k => k.kb_id === selectedKB)?.name}</span></>
                  ) : (
                    <>Uploading to: <span className="text-cyan-400">{knowledgeBases[0]?.name}</span> (default)</>
                  )}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Drag & drop files here, or click to select
                </p>
              </div>
              {selectedKB && (
                <button
                  onClick={() => setSelectedKB(null)}
                  className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors text-gray-400 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              )}
            </div>
            
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all ${
                isDragActive
                  ? 'border-cyan-500 bg-cyan-500/10'
                  : 'border-slate-600 hover:border-cyan-500/50 hover:bg-slate-700/30'
              }`}
            >
              <input {...getInputProps()} />
              <Upload
                className={`mx-auto mb-3 ${isDragActive ? 'text-cyan-400' : 'text-gray-400'}`}
                size={32}
              />
              <p className="text-sm text-gray-300 mb-2">
                {isDragActive ? 'Drop files here' : 'Click or drag files to upload'}
              </p>
              <p className="text-xs text-gray-500">
                Supports: PDF, DOC, PPT, XLS, MP4, MP3, WAV, JSON, JSONL (Max 100MB)
              </p>
            </div>
            
            {/* Upload Progress */}
            {uploadProgress.size > 0 && (
              <div className="mt-4 space-y-2">
                {Array.from(uploadProgress.entries()).map(([fileId, progress]) => (
                  <div key={fileId} className="bg-slate-900/50 rounded-lg p-3 border border-slate-700/50">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center space-x-2 flex-1 min-w-0">
                        {progress.status === 'uploading' || progress.status === 'processing' ? (
                          <Loader2 className="animate-spin text-cyan-400 flex-shrink-0" size={16} />
                        ) : progress.status === 'completed' ? (
                          <CheckCircle2 className="text-green-400 flex-shrink-0" size={16} />
                        ) : (
                          <XCircle className="text-red-400 flex-shrink-0" size={16} />
                        )}
                        <span className="text-sm text-gray-300 truncate">{progress.fileName}</span>
                      </div>
                      <span className="text-sm text-gray-400 ml-2">{progress.progress}%</span>
                    </div>
                    <div className="w-full bg-slate-700/50 rounded-full h-1.5">
                      <div
                        className={`h-full rounded-full transition-all ${
                          progress.status === 'completed'
                            ? 'bg-green-500'
                            : progress.status === 'error'
                            ? 'bg-red-500'
                            : 'bg-cyan-500'
                        }`}
                        style={{ width: `${progress.progress}%` }}
                      />
                    </div>
                    {progress.error && (
                      <p className="text-xs text-red-400 mt-1">{progress.error}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* New/Edit KB Modal */}
      {(showNewKBModal || editingKB) && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg border border-slate-700/50 p-6 w-full max-w-md">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">
                {editingKB ? 'Edit Knowledge Base' : 'New Knowledge Base'}
              </h3>
              <button
                onClick={() => {
                  setShowNewKBModal(false)
                  setEditingKB(null)
                  setNewKBName('')
                  setNewKBDescription('')
                }}
                className="p-1 hover:bg-slate-700/50 rounded transition-colors text-gray-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Name</label>
                <input
                  type="text"
                  value={newKBName}
                  onChange={(e) => setNewKBName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                  placeholder="Enter knowledge base name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Description</label>
                <textarea
                  value={newKBDescription}
                  onChange={(e) => setNewKBDescription(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/50"
                  placeholder="Enter description"
                  rows={3}
                />
              </div>
              <div className="flex space-x-3">
                <button
                  onClick={editingKB ? updateKnowledgeBase : createKnowledgeBase}
                  className="flex-1 px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 text-white rounded-lg hover:from-cyan-400 hover:to-blue-500 transition-all font-medium"
                >
                  {editingKB ? 'Save' : 'Create'}
                </button>
                <button
                  onClick={() => {
                    setShowNewKBModal(false)
                    setEditingKB(null)
                    setNewKBName('')
                    setNewKBDescription('')
                  }}
                  className="px-4 py-2 bg-slate-700/50 text-gray-300 rounded-lg hover:bg-slate-700 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
