import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_URL,
})

// Add auth token to requests and handle Content-Type
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    // Ensure we set the Authorization header correctly
    config.headers.Authorization = `Bearer ${token}`
    // Debug logging (remove in production)
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API] Adding Authorization header for ${config.method?.toUpperCase()} ${config.url}`)
    }
  } else {
    // Log warning if token is missing for protected endpoints
    const protectedEndpoints = ['/api/models', '/api/upload', '/api/chat', '/api/generate', '/api/documents']
    const isProtected = protectedEndpoints.some(endpoint => config.url?.includes(endpoint))
    if (isProtected && process.env.NODE_ENV === 'development') {
      console.warn(`[API] No auth token found for protected endpoint: ${config.url}`)
    }
  }
  
  // Only set Content-Type for non-FormData requests
  // FormData needs to set Content-Type with boundary automatically
  if (!(config.data instanceof FormData) && !config.headers['Content-Type']) {
    config.headers['Content-Type'] = 'application/json'
  }
  
  return config
})

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only redirect on 401 if we have a token (meaning token expired)
    // Don't redirect on login failures (no token yet)
    if (error.response?.status === 401 && localStorage.getItem('auth_token')) {
      localStorage.removeItem('auth_token')
      window.location.href = '/'
    }
    return Promise.reject(error)
  }
)

export default api

