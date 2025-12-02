import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User {
  id: number
  email: string
  full_name: string
  role: string
}

interface AuthState {
  isAuthenticated: boolean
  user: User | null
  token: string | null
  login: (token: string, user: User) => void
  logout: () => void
  setUser: (user: User) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      user: null,
      token: null,
      login: (token: string, user: User) => {
        localStorage.setItem('auth_token', token)
        set({ isAuthenticated: true, token, user })
      },
      logout: () => {
        localStorage.removeItem('auth_token')
        set({ isAuthenticated: false, token: null, user: null })
      },
      setUser: (user: User) => set({ user }),
    }),
    {
      name: 'auth-storage',
    }
  )
)

