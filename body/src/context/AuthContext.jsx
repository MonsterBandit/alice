import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'

const AuthContext = createContext(null)

let cachedUser = null

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
    // Refresh 2 minutes before expiry, minimum 10 seconds
    const refreshIn = Math.max(delayMs - 2 * 60 * 1000, 10_000)
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
          // Schedule next refresh — assume 15 min token lifetime if not told
          scheduleRefresh(15 * 60 * 1000)
        } else {
          logout()
        }
      } catch {
        logout()
      }
    }, refreshIn)
  }, [])

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
    scheduleRefresh(15 * 60 * 1000)
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
          scheduleRefresh(15 * 60 * 1000)
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
