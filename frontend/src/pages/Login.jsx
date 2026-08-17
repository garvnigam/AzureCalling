import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/app')
    } catch (err) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-6 relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0"
        style={{ background: 'radial-gradient(circle at 50% 30%, rgba(124,92,252,0.1) 0%, transparent 55%)' }} />
      <div className="relative z-10 w-full max-w-sm">
        <div className="flex justify-center mb-6">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center text-2xl shadow-glow">🏠</div>
        </div>
        <h1 className="text-center text-2xl font-bold tracking-tight mb-1">Welcome back</h1>
        <p className="text-center text-gray-400 text-sm mb-8">Sign in to your dashboard</p>
        <form onSubmit={onSubmit} className="p-6 rounded-2xl bg-surface border border-border space-y-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Username</label>
            <input
              type="text" value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus
              className="w-full px-3.5 py-2.5 rounded-lg bg-surface-2 border border-border focus:border-accent outline-none text-sm"
              placeholder="your username" autoComplete="username" />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Password</label>
            <input
              type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
              className="w-full px-3.5 py-2.5 rounded-lg bg-surface-2 border border-border focus:border-accent outline-none text-sm"
              placeholder="••••••••" autoComplete="current-password" />
          </div>
          {error && <p className="text-sm text-red px-1">{error}</p>}
          <button type="submit" disabled={loading}
            className="w-full py-2.5 rounded-lg bg-gradient-to-r from-accent to-accent-2 font-semibold text-sm shadow-glow hover:opacity-90 transition disabled:opacity-50">
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
        <p className="text-center text-xs text-gray-500 mt-6">
          Access is provided by your organization. <Link to="/" className="text-accent-2 hover:underline">← Back</Link>
        </p>
      </div>
    </div>
  )
}