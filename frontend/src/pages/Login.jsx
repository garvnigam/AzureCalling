import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const PASSWORD_POLICY = 'Password must be at least 8 characters, with at least one number and one special character'

export default function Login() {
  const { login, signup } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function switchMode(m) {
    setMode(m)
    setError('')
  }

  function validateSignup() {
    if (username.trim().length < 3) return 'Username must be at least 3 characters'
    if (!/(?=.*[0-9])(?=.*[^A-Za-z0-9]).{8,}/.test(password)) return PASSWORD_POLICY
    if (password !== confirm) return 'Passwords do not match'
    return ''
  }

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      if (mode === 'login') {
        await login(username, password)
      } else {
        const v = validateSignup()
        if (v) { setError(v); setLoading(false); return }
        await signup(username, password, confirm)
      }
      navigate('/app')
    } catch (err) {
      setError(err.message || 'Something went wrong')
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
        <h1 className="text-center text-2xl font-bold tracking-tight mb-1">
          {mode === 'login' ? 'Welcome back' : 'Create your account'}
        </h1>
        <p className="text-center text-gray-400 text-sm mb-8">
          {mode === 'login' ? 'Sign in to your dashboard' : 'Sign up — your account is saved for future logins'}
        </p>
        <div className="grid grid-cols-2 gap-1 p-1 rounded-xl bg-surface-2 border border-border mb-5">
          <button onClick={() => switchMode('login')}
            className={`py-2 rounded-lg text-sm font-medium transition ${mode === 'login' ? 'bg-accent text-white shadow-glow' : 'text-gray-400 hover:text-gray-200'}`}>
            Existing User
          </button>
          <button onClick={() => switchMode('signup')}
            className={`py-2 rounded-lg text-sm font-medium transition ${mode === 'signup' ? 'bg-accent text-white shadow-glow' : 'text-gray-400 hover:text-gray-200'}`}>
            New User
          </button>
        </div>

        <form onSubmit={onSubmit} className="p-6 rounded-2xl bg-surface border border-border space-y-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">{mode === 'signup' ? 'Username' : 'Username or Email'}</label>
            <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus
              className="w-full px-3.5 py-2.5 rounded-lg bg-surface-2 border border-border focus:border-accent outline-none text-sm"
              placeholder={mode === 'signup' ? 'choose a username' : 'your username or email'}
              autoComplete="username" />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1.5">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
              className="w-full px-3.5 py-2.5 rounded-lg bg-surface-2 border border-border focus:border-accent outline-none text-sm"
              placeholder="••••••••" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />
            {mode === 'signup' && (
              <p className="text-[11px] text-gray-500 mt-1.5">At least 8 characters, one number and one special character</p>
            )}
          </div>
          {mode === 'signup' && (
            <div>
              <label className="block text-xs text-gray-400 mb-1.5">Confirm Password</label>
              <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required
                className="w-full px-3.5 py-2.5 rounded-lg bg-surface-2 border border-border focus:border-accent outline-none text-sm"
                placeholder="••••••••" autoComplete="new-password" />
            </div>
          )}
          {error && <p className="text-sm text-red px-1">{error}</p>}
          <button type="submit" disabled={loading}
            className="w-full py-2.5 rounded-lg bg-gradient-to-r from-accent to-accent-2 font-semibold text-sm shadow-glow hover:opacity-90 transition disabled:opacity-50">
            {loading ? 'Please wait…' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>
        <p className="text-center text-xs text-gray-500 mt-6">
          {mode === 'login'
            ? <>New here? <button onClick={() => switchMode('signup')} className="text-accent-2 hover:underline">Create an account</button></>
            : <>Already registered? <button onClick={() => switchMode('login')} className="text-accent-2 hover:underline">Sign in</button></>}
          {' · '}<Link to="/" className="text-accent-2 hover:underline">← Back</Link>
        </p>
      </div>
    </div>
  )
}