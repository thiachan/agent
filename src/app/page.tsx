'use client'

import Image from 'next/image'
import { useAuthStore } from '@/stores/authStore'
import { useThemeStore } from '@/stores/themeStore'
import { LoginForm } from '@/components/auth/LoginForm'
import { MainPortal } from '@/components/portal/MainPortal'
import { Sun, Moon } from 'lucide-react'

export default function Home() {
  const { isAuthenticated } = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#07182D] relative">
        {/* Theme toggle — top-right corner */}
        <button
          onClick={toggleTheme}
          className="absolute top-4 right-4 p-2 rounded-lg bg-slate-800/50 border border-slate-700/50 text-gray-400 hover:text-white hover:bg-slate-700/50 transition-colors backdrop-blur-sm"
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        <div className="w-full max-w-md">
          <div className="bg-slate-800/70 backdrop-blur-sm rounded-lg shadow-2xl p-8 border border-slate-700/50">
            <div className="flex flex-col items-center justify-center mb-6">
              <div className="flex items-center justify-center space-x-3 mb-3">
                <Image 
                  src="/gsse_logo.png" 
                  alt="AGENT Logo" 
                  width={56} 
                  height={56} 
                  className="object-contain"
                />
                <h1 className="text-5xl font-bold text-white">
                  AGENT
                </h1>
              </div>
              <p className="text-xs text-gray-400">AI for GSSO Engineering Team</p>
            </div>
            <LoginForm />
          </div>
        </div>
      </div>
    )
  }

  return <MainPortal />
}


