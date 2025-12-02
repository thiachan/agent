'use client'

import { useState } from 'react'
import { useAuthStore } from '@/stores/authStore'
import api from '@/lib/api'

export function LoginForm() {
  const [isSignUp, setIsSignUp] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [showForgotPassword, setShowForgotPassword] = useState(false)
  const [forgotPasswordEmail, setForgotPasswordEmail] = useState('')
  const [forgotPasswordLoading, setForgotPasswordLoading] = useState(false)
  const { login } = useAuthStore()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccessMessage('')
    setLoading(true)

    try {
      if (isSignUp) {
        // Sign up - now requires email verification
        const response = await api.post('/api/auth/register', { 
          email, 
          password, 
          full_name: fullName,
          role: 'employee' // Default role for new users
        })
        const { message, email_sent } = response.data
        setSuccessMessage(message)
        // Don't auto-login - user needs to verify email first
        setIsSignUp(false) // Switch to login view
        setEmail('') // Clear form
        setPassword('')
        setFullName('')
      } else {
        // Sign in
        const response = await api.post('/api/auth/login', { email, password })
        const { access_token, user } = response.data
        login(access_token, user)
      }
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail || (isSignUp ? 'Sign up failed' : 'Login failed')
      setError(errorDetail)
      
      // If email not verified, show helpful message
      if (errorDetail.includes('Email not verified')) {
        setError(`${errorDetail} Click "Resend Verification" below to receive a new email.`)
      }
    } finally {
      setLoading(false)
    }
  }

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccessMessage('')
    setForgotPasswordLoading(true)

    try {
      await api.post('/api/auth/forgot-password', { email: forgotPasswordEmail })
      setSuccessMessage('If the email exists, a password reset link has been sent to your email.')
      setShowForgotPassword(false)
      setForgotPasswordEmail('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to send password reset email')
    } finally {
      setForgotPasswordLoading(false)
    }
  }

  const handleResendVerification = async () => {
    if (!email) {
      setError('Please enter your email address first')
      return
    }
    
    setError('')
    setSuccessMessage('')
    setLoading(true)

    try {
      await api.post('/api/auth/resend-verification', { email })
      setSuccessMessage('If the email exists and is not verified, a verification email has been sent.')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to resend verification email')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      {showForgotPassword ? (
        <form onSubmit={handleForgotPassword} className="space-y-4">
          <h2 className="text-xl font-semibold text-white mb-4">Reset Password</h2>
          {error && (
            <div className="bg-red-500/20 border border-red-500/50 text-red-300 px-4 py-3 rounded">
              {error}
            </div>
          )}
          {successMessage && (
            <div className="bg-green-500/20 border border-green-500/50 text-green-300 px-4 py-3 rounded">
              {successMessage}
            </div>
          )}
          <div>
            <label htmlFor="forgotEmail" className="block text-sm font-medium text-gray-300 mb-1">
              Email
            </label>
            <input
              id="forgotEmail"
              type="email"
              value={forgotPasswordEmail}
              onChange={(e) => setForgotPasswordEmail(e.target.value)}
              required
              className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600/50 rounded-md text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500/50"
              placeholder="you@company.com"
            />
          </div>
          <button
            type="submit"
            disabled={forgotPasswordLoading}
            className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 text-white py-2 px-4 rounded-md hover:from-cyan-400 hover:to-blue-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-lg shadow-cyan-500/30"
          >
            {forgotPasswordLoading ? 'Sending...' : 'Send Reset Link'}
          </button>
          <button
            type="button"
            onClick={() => {
              setShowForgotPassword(false)
              setError('')
              setSuccessMessage('')
            }}
            className="w-full text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            Back to Login
          </button>
        </form>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-500/20 border border-red-500/50 text-red-300 px-4 py-3 rounded">
              {error}
            </div>
          )}
          {successMessage && (
            <div className="bg-green-500/20 border border-green-500/50 text-green-300 px-4 py-3 rounded">
              {successMessage}
            </div>
          )}
      {isSignUp && (
        <div>
          <label htmlFor="fullName" className="block text-sm font-medium text-gray-300 mb-1">
            Full Name
          </label>
          <input
            id="fullName"
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
            className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600/50 rounded-md text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500/50"
            placeholder="John Doe"
          />
        </div>
      )}
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-1">
          Email
        </label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600/50 rounded-md text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500/50"
          placeholder="you@company.com"
        />
      </div>
      <div>
        <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-1">
          Password
        </label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="w-full px-3 py-2 bg-slate-700/50 border border-slate-600/50 rounded-md text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-cyan-500/50"
          placeholder="••••••••"
        />
      </div>
      <button
        type="submit"
        disabled={loading}
        className="w-full bg-gradient-to-r from-cyan-500 to-blue-600 text-white py-2 px-4 rounded-md hover:from-cyan-400 hover:to-blue-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed font-medium shadow-lg shadow-cyan-500/30"
      >
        {loading ? (isSignUp ? 'Signing up...' : 'Logging in...') : (isSignUp ? 'Sign Up' : 'Sign In')}
      </button>
          {!isSignUp && (
            <div className="text-center">
              <button
                type="button"
                onClick={handleResendVerification}
                className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors mr-4"
              >
                Resend Verification Email
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowForgotPassword(true)
                  setError('')
                  setSuccessMessage('')
                }}
                className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
              >
                Forgot Password?
              </button>
            </div>
          )}
          <div className="text-center">
            <button
              type="button"
              onClick={() => {
                setIsSignUp(!isSignUp)
                setError('')
                setSuccessMessage('')
              }}
              className="text-sm text-cyan-400 hover:text-cyan-300 transition-colors"
            >
              {isSignUp ? 'Already have an account? Sign in' : "Don't have an account? Sign up"}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}

