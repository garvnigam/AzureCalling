import React from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import CallTab from '../components/CallTab'
import WhatsAppTab from '../components/WhatsAppTab'

export default function AppShell() {
  const { user, ready, logout } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = React.useState('calls')

  if (!ready) return <div className="min-h-screen flex items-center justify-center text-slate-400">Loading…</div>
  if (!user) return <Navigate to="/login" replace />

  const tabs = [
    { id: 'calls', label: 'Calls' },
    { id: 'whatsapp', label: 'WhatsApp' },
  ]

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 flex items-center justify-between px-6 py-3 border-b border-border bg-surface/80 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <span className="logo-mark" style={{ width: 32, height: 32 }}>
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 11.5 12 4l9 7.5" />
              <path d="M5 10v9h14v-9" />
              <path d="M10 19v-5h4v5" />
            </svg>
          </span>
          <div>
            <h1 className="font-display font-semibold text-sm leading-tight tracking-tightest">Realty Siksha</h1>
            <p className="text-[11px] text-slate-500 leading-tight">{user?.name || user?.email}</p>
          </div>
        </div>
        <div className="flex items-center gap-1 p-1 rounded-xl bg-surface-2 border border-border">
          {tabs.map((t) => (
            <button key={t.id} onClick={() => setTab(t.id)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition ${tab === t.id ? 'bg-gradient-to-r from-accent to-accent-2 text-white shadow-glow' : 'text-slate-400 hover:text-white'}`}>
              {t.label}
            </button>
          ))}
        </div>
        <button onClick={() => { logout(); navigate('/login') }}
          className="px-3.5 py-1.5 rounded-lg text-xs text-slate-400 border border-border hover:text-white hover:border-accent/40 transition">
          Logout
        </button>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-6">
        {tab === 'calls' && <CallTab />}
        {tab === 'whatsapp' && <WhatsAppTab />}
      </main>
    </div>
  )
}