import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'

const AuthContext = createContext(null)

let cachedUser = null

// Token lifetime is 24 hours; refresh 5 minutes before expiry = 23h55m = 86100000 ms
const TOKEN_LIFETIME_MS = 86_100_000
const RETRY_AFTER_FAILURE_MS = 60_000

export function AuthProvider({ children }) {
  const [token, setToken] = useState(null)
  const [user, setUser] = useState(cachedUser)
  const refreshTimerRef = useRef(null)

  const setUserCached = useCallback((u) => {
    cachedUser = u
    setUser(u)
  }, [])

  const scheduleRefresh = useCallback((delayMs) => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current)
    refreshTimerRef.current = setTimeout(async () => {
      try {
        const res = await fetch('/api/auth/refresh', {
          method: 'POST',
          credentials: 'include',
        })
        if (res.ok) {
          const data = await res.json()
          setToken(data.token)
          if (data.user_id) setUserCached({ id: data.user_id, name: data.name })
          // Schedule the next refresh at 23h55m from now
          scheduleRefresh(TOKEN_LIFETIME_MS)
        } else {
          // Refresh failed — retry in 60 seconds, do NOT log the user out
          scheduleRefresh(RETRY_AFTER_FAILURE_MS)
        }
      } catch {
        // Network error — retry in 60 seconds, do NOT log the user out
        scheduleRefresh(RETRY_AFTER_FAILURE_MS)
      }
    }, delayMs)
  }, [setUserCached])

  const login = useCallback(async (email, password) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Login failed')
    }
    const data = await res.json()
    setToken(data.token)
    setUserCached({ id: data.user_id, name: data.name })
    // Schedule silent refresh 5 minutes before the 24-hour token expires
    scheduleRefresh(TOKEN_LIFETIME_MS)
    return data
  }, [scheduleRefresh, setUserCached])

  const logout = useCallback(() => {
    if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current)
    cachedUser = null
    setToken(null)
    setUser(null)
  }, [])

  // Attempt a silent refresh on mount (in case of a refresh-token cookie)
  useEffect(() => {
    fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' })
      .then((res) => {
        if (res.ok) return res.json()
        return null
      })
      .then((data) => {
        if (data?.token) {
          setToken(data.token)
          setUserCached({ id: data.user_id, name: data.name })
          // Schedule silent refresh 5 minutes before the 24-hour token expires
          scheduleRefresh(TOKEN_LIFETIME_MS)
        }
      })
      .catch(() => {})
  }, [scheduleRefresh, setUserCached])

  return (
    <AuthContext.Provider value={{ token, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
