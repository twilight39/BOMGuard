import { createContext, useContext, useEffect, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface AuthUser {
  id: string
  email: string
  name: string | null
  avatar_url: string | null
}

interface AuthContextValue {
  user: AuthUser | null
  isLoading: boolean
  login: () => void
  logout: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refreshUser = async () => {
    const res = await fetch(`${API_BASE}/api/auth/me`, { credentials: 'include' })
    if (res.ok) {
      const data = await res.json()
      setUser(data as AuthUser)
    } else {
      setUser(null)
    }
  }

  useEffect(() => {
    refreshUser()
      .catch(() => {
        // Silently ignore auth check failures
      })
      .finally(() => setIsLoading(false))
  }, [])

  const login = () => {
    window.location.href = `${API_BASE}/api/auth/login`
  }

  const logout = async () => {
    await fetch(`${API_BASE}/api/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    })
    setUser(null)
    window.location.reload()
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used inside an AuthProvider')
  }
  return ctx
}
