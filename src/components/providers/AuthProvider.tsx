'use client'

import { useEffect, useState } from 'react'
import { useAuthStore } from '@/stores/authStore'
import api from '@/lib/api'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { login, setUser } = useAuthStore()
  const [isInitialized, setIsInitialized] = useState(false)

  useEffect(() => {
    const initializeAuth = async () => {
      const token = localStorage.getItem('auth_token')
      if (token) {
        try {
          // Verify token and get user info
          const response = await api.get('/api/auth/me')
          const user = response.data
          login(token, user)
        } catch (error) {
          // Token is invalid, remove it
          localStorage.removeItem('auth_token')
        }
      }
      setIsInitialized(true)
    }
    
    initializeAuth()
  }, [login])

  // Don't render children until auth state is initialized
  if (!isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  return <>{children}</>
}

