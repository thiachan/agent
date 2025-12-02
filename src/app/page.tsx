'use client'

import Image from 'next/image'
import { useAuthStore } from '@/stores/authStore'
import { LoginForm } from '@/components/auth/LoginForm'
import { MainPortal } from '@/components/portal/MainPortal'

export default function Home() {
  const { isAuthenticated } = useAuthStore()

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#07182D]">
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
              <p className="text-base text-gray-400">AI for GSSO Engineering Team</p>
            </div>
            <LoginForm />
          </div>
        </div>
      </div>
    )
  }

  return <MainPortal />
}

