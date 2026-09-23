import axios from 'axios'

/**
 * Resolves the appropriate backend API base URL:
 * 1. Environment variables: VITE_API_URL, VITE_API_BASE_URL, or NEXT_PUBLIC_API_URL
 * 2. Hostname check: If running in browser on non-localhost (e.g. smart-land-analysis.vercel.app),
 *    ensure we target https://smart-land-analysis.onrender.com/api/v1 (unless explicit remote env var is set).
 * 3. Local development: http://localhost:8000/api/v1 (when on localhost or 127.0.0.1)
 */
const getApiBaseUrl = () => {
  const rawEnv =
    import.meta.env.VITE_API_URL ||
    import.meta.env.VITE_API_BASE_URL ||
    import.meta.env.NEXT_PUBLIC_API_URL

  const formatUrl = (url) => {
    let cleaned = url.trim().replace(/\/+$/, '')
    if (!cleaned.endsWith('/api/v1')) {
      cleaned = `${cleaned}/api/v1`
    }
    return cleaned
  }

  // Check if running in browser
  if (typeof window !== 'undefined' && window.location) {
    const host = window.location.hostname
    const isLocalhost = host === 'localhost' || host === '127.0.0.1' || host === '0.0.0.0'

    if (!isLocalhost) {
      // Production deployment (e.g. Vercel)
      if (
        rawEnv &&
        typeof rawEnv === 'string' &&
        rawEnv.trim() !== '' &&
        !rawEnv.includes('localhost') &&
        !rawEnv.includes('127.0.0.1')
      ) {
        return formatUrl(rawEnv)
      }
      return 'https://smart-land-analysis.onrender.com/api/v1'
    } else {
      // Local development environment
      if (rawEnv && typeof rawEnv === 'string' && rawEnv.trim() !== '') {
        return formatUrl(rawEnv)
      }
      return `http://${host}:8000/api/v1`
    }
  }

  // Fallback for non-browser / build time
  if (
    rawEnv &&
    typeof rawEnv === 'string' &&
    rawEnv.trim() !== '' &&
    !rawEnv.includes('localhost') &&
    !rawEnv.includes('127.0.0.1')
  ) {
    return formatUrl(rawEnv)
  }

  return 'https://smart-land-analysis.onrender.com/api/v1'
}

const API_BASE_URL = getApiBaseUrl()
if (typeof window !== 'undefined') {
  console.log('[BuildWise AI] API BASE URL:', API_BASE_URL)
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000,
})

// ---- Request interceptor: attach JWT access token if present ----
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ---- Response interceptor: normalize errors, handle 401 ----
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Token expired / invalid — clear it so the UI can react
      localStorage.removeItem('access_token')
    }

    // If response is a Blob (e.g. from failed file download), parse it to extract actual error JSON
    if (error.response?.data instanceof Blob) {
      try {
        const text = await error.response.data.text()
        const parsed = JSON.parse(text)
        error.response.data = parsed
      } catch (e) {
        // Blob is not JSON or could not be parsed
      }
    }

    const message = extractErrorMessage(error)
    return Promise.reject({ ...error, message })
  }
)

/**
 * FastAPI error responses come in two shapes:
 *   - Simple:      { detail: "Land not found" }                         (string)
 *   - Validation:  { detail: [{ loc: [...], msg: "...", type: "..." }] } (422 array)
 * This normalizes both into a single human-readable string so callers
 * can always safely render `err.message` directly in the UI.
 */
function extractErrorMessage(error) {
  const detail = error.response?.data?.detail

  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null
        return field ? `${field}: ${d.msg}` : d.msg
      })
      .join(' | ')
  }

  if (typeof detail === 'string') return detail

  if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
    return 'Connection timed out. The backend server on Render may be waking up from cold start. Please wait 10 seconds and try again.'
  }

  if (error.message === 'Network Error' || error.code === 'ERR_NETWORK') {
    return 'Network Error: Unable to connect to backend server. Please verify backend is active on https://smart-land-analysis.onrender.com'
  }

  return error.response?.data?.message || error.message || 'Something went wrong. Please try again.'
}

export default api
