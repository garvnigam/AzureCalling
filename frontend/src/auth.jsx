import React, { createContext, useContext, useState } from 'react'
import { api, setToken, clearToken, getToken } from './api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  React.useEffect(() => {
    if (getToken()) {
      fetch('/api/auth/me', { headers: { Authorization: `Bearer ${getToken()}` } })
        .then((r) => (r.ok ? r.json() : Promise.reject()))
        .then((u) => setUser(u))
        .catch(() => clearToken())
        .finally(() => setReady(true))
    } else {
      setReady(true)
    }
  }, [])

  async function login(username, password) {
    const data = await api('/api/auth/login', { method: 'POST', body: { username, password } })
    setToken(data.token)
    setUser(data.user)
    return data.user
  }

  async function signup(username, password, confirm_password) {
    const data = await api('/api/auth/signup', { method: 'POST', body: { username, password, confirm_password } })
    setToken(data.token)
    setUser(data.user)
    return data.user
  }

  function logout() {
    clearToken()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, ready, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}