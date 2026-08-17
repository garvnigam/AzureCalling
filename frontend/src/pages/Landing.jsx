import React from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth'

const features = [
  { icon: '🤖', title: 'AI Voice Agent', desc: 'Warm, natural Hinglish conversations that qualify leads — budget, location, BHK, timeline.' },
  { icon: '📞', title: 'Outbound Calls', desc: 'One-click calling from the dashboard with live transcript streaming in real time.' },
  { icon: '📊', title: 'Lead Intelligence', desc: 'Every call is scored 0–100 with extracted name, budget, preferences, and next action.' },
  { icon: '💬', title: 'WhatsApp Follow-ups', desc: 'Personalized follow-up messages sent automatically after each conversation.' },
]

export default function Landing() {
  const { user } = useAuth()
  return (
    <div className="min-h-screen relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0"
        style={{ background: 'radial-gradient(circle at 30% 20%, rgba(124,92,252,0.08) 0%, transparent 50%), radial-gradient(circle at 70% 80%, rgba(91,141,239,0.06) 0%, transparent 50%)' }} />

      <header className="relative z-10 flex items-center justify-between px-8 py-5 border-b border-border bg-surface/70 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-accent to-accent-2 flex items-center justify-center text-lg shadow-glow">🏠</div>
          <h1 className="font-semibold text-lg tracking-tight">GS Associates <span className="text-gray-400 font-normal text-sm">AI Calling Agent</span></h1>
        </div>
        <Link to={user ? '/app' : '/login'}
          className="px-5 py-2 rounded-lg bg-gradient-to-r from-accent to-accent-2 font-semibold text-sm hover:opacity-90 transition shadow-glow">
          {user ? 'Open Dashboard' : 'Login'}
        </Link>
      </header>

      <main className="relative z-10 max-w-5xl mx-auto px-6 pt-24 pb-16 text-center">
        <div className="inline-block px-3 py-1 rounded-full text-xs border border-accent/40 text-accent-2 bg-accent/10 mb-6">
          Greater Noida Real Estate · 24/7
        </div>
        <h2 className="text-5xl md:text-6xl font-bold tracking-tight leading-tight">
          Your AI agent calls,<br />
          <span className="bg-gradient-to-r from-accent to-accent-2 bg-clip-text text-transparent">you close the deal.</span>
        </h2>
        <p className="mt-6 text-lg text-gray-400 max-w-2xl mx-auto">
          Shyam speaks with every lead like a seasoned consultant — qualifying budget,
          preferences, and timelines naturally, and handing you a scored lead after every call.
        </p>
        <div className="mt-10 flex items-center justify-center gap-4">
          <Link to="/login"
            className="px-8 py-3 rounded-xl bg-gradient-to-r from-accent to-accent-2 font-semibold shadow-glow hover:opacity-90 transition">
            Get Started
          </Link>
        </div>

        <div className="mt-20 grid md:grid-cols-2 lg:grid-cols-4 gap-5 text-left">
          {features.map((f) => (
            <div key={f.title} className="p-6 rounded-2xl bg-surface border border-border hover:border-accent/40 transition">
              <div className="text-3xl mb-3">{f.icon}</div>
              <h3 className="font-semibold mb-1">{f.title}</h3>
              <p className="text-sm text-gray-400 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}