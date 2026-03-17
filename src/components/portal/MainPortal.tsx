'use client'

import { useState, useEffect } from 'react'
import Image from 'next/image'
import { useAuthStore } from '@/stores/authStore'
import { useThemeStore } from '@/stores/themeStore'
import { MessageSquare, Plus, LogOut, ChevronLeft, ChevronRight, Bot, FileText, Trash2, Star, Users, BookOpen, PlayCircle, Sun, Moon, Bookmark } from 'lucide-react'
import { ChatWithGeneration } from './ChatWithGeneration'
import { DocumentUpload } from './DocumentUpload'
import { UserManagement } from './UserManagement'
import { Onboarding } from './Onboarding'
import { BookmarkPage } from './BookmarkPage'
import api from '@/lib/api'

interface ChatSession {
  id: number
  title: string
  created_at: string
  updated_at: string
  message_count?: number
  model_name?: string
}

export function MainPortal() {
  const [activeView, setActiveView] = useState<'chat' | 'upload' | 'users' | 'onboarding' | 'onboarding-sim' | 'bookmarks'>('chat')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [recentChats, setRecentChats] = useState<ChatSession[]>([])
  const [selectedChatId, setSelectedChatId] = useState<number | null>(null)
  const { user, logout } = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()

  useEffect(() => {
    fetchRecentChats()
  }, [])

  // Redirect non-admin users away from upload and users view
  useEffect(() => {
    if ((activeView === 'upload' || activeView === 'users') && user?.role !== 'admin') {
      setActiveView('chat')
    }
  }, [activeView, user?.role])


  const fetchRecentChats = async () => {
    try {
      const response = await api.get('/api/chat/sessions?limit=10')
      if (response.data?.items) {
        setRecentChats(response.data.items)
      }
    } catch (error) {
      console.error('Failed to fetch recent chats:', error)
    }
  }

  const createNewChat = () => {
    setSelectedChatId(null)
    setActiveView('chat')
    // Refresh recent chats after a short delay to allow new session to be created
    setTimeout(() => {
      fetchRecentChats()
    }, 1000)
  }

  const selectChat = (chatId: number) => {
    setSelectedChatId(chatId)
    setActiveView('chat')
  }

  const deleteChat = async (chatId: number, e: React.MouseEvent) => {
    e.stopPropagation() // Prevent selecting the chat when clicking delete
    if (!confirm('Are you sure you want to delete this chat?')) {
      return
    }

    try {
      console.log(`[Delete] Attempting to delete chat session ${chatId}`)
      const response = await api.delete(`/api/chat/sessions/${chatId}`)
      console.log('Delete response:', response.data)
      
      // Only update state after successful API call
      // Refresh the list from server to ensure consistency
      await fetchRecentChats()
      
      // If deleted chat was selected, clear selection
      if (selectedChatId === chatId) {
        setSelectedChatId(null)
      }
      
      console.log(`[Delete] Chat ${chatId} deleted successfully`)
    } catch (error: any) {
      console.error('Failed to delete chat:', error)
      console.error('Error details:', {
        status: error.response?.status,
        data: error.response?.data,
        message: error.message
      })
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to delete chat'
      alert(`Failed to delete chat: ${errorMessage}\n\nPlease check the browser console for more details.`)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffTime = Math.abs(now.getTime() - date.getTime())
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))
    
    if (diffDays === 0) return 'Today'
    if (diffDays === 1) return 'Yesterday'
    if (diffDays < 7) return `${diffDays} days ago`
    
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    return `${monthNames[date.getMonth()]} ${date.getDate()}`
  }

  const getModelEmoji = (modelName?: string) => {
    if (!modelName) return '🤖'
    const lower = modelName.toLowerCase()
    if (lower.includes('gpt') || lower.includes('openai')) {
      return '🤖'
    }
    if (lower.includes('claude')) {
      return '🧠'
    }
    return '⚡'
  }

  return (
    <div className="h-screen flex overflow-hidden bg-[#07182D]">
      {/* Sidebar */}
      <div className={`${sidebarOpen ? 'w-64' : 'w-0'} bg-slate-800/50 border-r border-slate-700/50 transition-all duration-300 overflow-hidden flex flex-col h-full`}>
        {/* Header */}
        <div className="p-4 border-b border-slate-700/50 flex-shrink-0">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Image 
                src="/gsse_logo_new.png" 
                alt="GSSO Logo" 
                width={44} 
                height={44} 
                className="object-contain"
              />
              <div>
                <h1 className="text-xl font-bold text-white">AGENT</h1>
              </div>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="p-1 hover:bg-slate-700/50 rounded text-gray-400 hover:text-white transition-colors"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
          </div>
          <button
            onClick={createNewChat}
            className="w-full flex items-center justify-center space-x-2 px-4 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 text-white rounded-lg hover:from-cyan-400 hover:to-blue-500 transition-all font-medium shadow-lg shadow-cyan-500/30 text-sm"
          >
            <Plus className="w-4 h-4" />
            <span>New AGENT</span>
          </button>
        </div>

        {/* Navigation */}
        <div className="px-4 py-2 border-b border-slate-700/50 flex-shrink-0">
          <nav className="space-y-1">
            <button
              onClick={() => setActiveView('chat')}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors text-sm ${
                activeView === 'chat'
                  ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-white border border-cyan-400/30'
                  : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'
              }`}
            >
              <MessageSquare className="w-5 h-5" />
              <span>AGENT</span>
            </button>
            <button
              onClick={() => setActiveView('bookmarks')}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors text-sm ${
                activeView === 'bookmarks'
                  ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-white border border-cyan-400/30'
                  : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'
              }`}
            >
              <Bookmark className="w-5 h-5" />
              <span>Bookmarks</span>
            </button>
            <button
              onClick={() => setActiveView('onboarding')}
              className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors text-sm ${
                activeView === 'onboarding'
                  ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-white border border-cyan-400/30'
                  : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'
              }`}
            >
              <BookOpen className="w-5 h-5" />
              <span>Onboarding</span>
            </button>
            {user?.role === 'admin' && (
              <>
                <button
                  onClick={() => setActiveView('onboarding-sim')}
                  className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors text-sm ${
                    activeView === 'onboarding-sim'
                      ? 'bg-gradient-to-r from-amber-500/20 to-orange-500/20 text-white border border-amber-400/30'
                      : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'
                  }`}
                >
                  <PlayCircle className="w-5 h-5" />
                  <span>Onboard Simulation</span>
                </button>
                <button
                  onClick={() => setActiveView('upload')}
                  className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors text-sm ${
                    activeView === 'upload'
                      ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-white border border-cyan-400/30'
                      : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'
                  }`}
                >
                  <FileText className="w-5 h-5" />
                  <span>Knowledge base</span>
                </button>
                <button
                  onClick={() => setActiveView('users')}
                  className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors text-sm ${
                    activeView === 'users'
                      ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-white border border-cyan-400/30'
                      : 'text-gray-400 hover:bg-slate-700/50 hover:text-white'
                  }`}
                >
                  <Users className="w-5 h-5" />
                  <span>User Management</span>
                </button>
              </>
            )}
          </nav>
        </div>

        {/* Recent Chats - Scrollable */}
        <div className="flex-1 overflow-y-auto px-4 py-4 min-h-0">
          <h2 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-3">
            Recent AGENTs
          </h2>
          <div className="space-y-2">
            {recentChats.length === 0 ? (
              <p className="text-xs text-gray-500 text-center py-4">No recent AGENTs</p>
            ) : (
              recentChats.map((chat) => (
                <div
                  key={chat.id}
                  className={`group relative w-full text-left px-3 py-3 rounded-lg transition-colors pr-10 ${
                    selectedChatId === chat.id
                      ? 'bg-gradient-to-r from-cyan-500/30 to-blue-600/30 text-white border border-cyan-400/40'
                      : 'text-gray-300 hover:bg-slate-700/50'
                  }`}
                >
                  <button
                    onClick={() => selectChat(chat.id)}
                    className="w-full flex items-start space-x-2 text-left"
                  >
                    <span className="text-base mt-0.5 flex-shrink-0">{getModelEmoji(chat.model_name)}</span>
                    <div className="flex-1 min-w-0 text-left">
                      <p className="text-xs font-medium truncate text-left">{chat.title || 'New AGENT'}</p>
                      <p className="text-[10px] text-gray-500 mt-1 text-left">{formatDate(chat.updated_at)}</p>
                    </div>
                    {selectedChatId === chat.id && (
                      <Star className="w-4 h-4 text-yellow-400 fill-yellow-400 flex-shrink-0 mt-0.5" />
                    )}
                  </button>
                  <button
                    onClick={(e) => deleteChat(chat.id, e)}
                    className="absolute right-2 top-2 p-1.5 opacity-0 group-hover:opacity-100 hover:bg-red-500/20 rounded transition-all text-gray-400 hover:text-red-400 z-10"
                    title="Delete chat"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* User Profile - Fixed at bottom */}
        <div className="p-4 border-t border-slate-700/50 flex-shrink-0">
          {/* User Profile */}
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-gradient-to-br from-cyan-400 to-blue-600 rounded-full flex items-center justify-center text-white font-medium text-sm">
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-white truncate">
                {user?.full_name || 'User'}
              </p>
              <p className="text-[10px] text-gray-400 truncate">
                {user?.email || 'user@gsse.com'}
              </p>
            </div>
            <button
              onClick={logout}
              className="p-1.5 hover:bg-slate-700/50 rounded transition-colors text-gray-400 hover:text-white"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
            <button
              onClick={toggleTheme}
              className="p-1.5 hover:bg-slate-700/50 rounded transition-colors text-gray-400 hover:text-white"
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? (
                <Sun className="w-4 h-4" />
              ) : (
                <Moon className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Sidebar Toggle Button (when closed) */}
      {!sidebarOpen && (
        <button
          onClick={() => setSidebarOpen(true)}
          className="fixed left-0 top-1/2 -translate-y-1/2 p-2 bg-slate-800/80 border-r border-slate-700/50 rounded-r-lg shadow-lg hover:bg-slate-700/80 transition-colors z-10 backdrop-blur-sm"
        >
          <ChevronRight className="w-5 h-5 text-gray-300" />
        </button>
      )}

      {/* Main Content - Full height */}
      <div className="flex-1 flex flex-col overflow-hidden h-full">
        {activeView === 'chat' && (
          <ChatWithGeneration 
            sessionId={selectedChatId} 
            onNewChat={createNewChat}
            onSessionCreated={(newSessionId) => {
              setSelectedChatId(newSessionId)
              fetchRecentChats()
            }}
          />
        )}
        {activeView === 'upload' && user?.role === 'admin' && <DocumentUpload />}
        {activeView === 'upload' && user?.role !== 'admin' && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-base font-medium text-white mb-2">Access restricted</p>
              <p className="text-gray-400 text-xs">Document upload and management is only available to administrators</p>
            </div>
          </div>
        )}
        {activeView === 'users' && user?.role === 'admin' && <UserManagement />}
        {activeView === 'users' && user?.role !== 'admin' && (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <p className="text-base font-medium text-white mb-2">Access restricted</p>
              <p className="text-gray-400 text-xs">User management is only available to administrators</p>
            </div>
          </div>
        )}
        {activeView === 'onboarding' && (
          <div className="flex-1 overflow-y-auto h-full">
            <Onboarding />
          </div>
        )}
        {activeView === 'onboarding-sim' && user?.role === 'admin' && (
          <div className="flex-1 overflow-y-auto h-full">
            <Onboarding simulateUser={true} />
          </div>
        )}
        {activeView === 'bookmarks' && <BookmarkPage />}
      </div>
    </div>
  )
}
