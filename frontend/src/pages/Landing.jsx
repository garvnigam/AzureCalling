import React from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth'

function LogoMark({ size = 36 }) {
  return (
    <span className="logo-mark" style={{ width: size, height: size }}>
      <svg viewBox="0 0 24 24" width={size * 0.6} height={size * 0.6} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 11.5 12 4l9 7.5" />
        <path d="M5 10v9h14v-9" />
        <path d="M10 19v-5h4v5" />
      </svg>
    </span>
  )
}

const features = [
  { title: 'AI Voice Agent', desc: 'Warm, natural Hinglish conversations that qualify leads on budget, location, BHK and timeline.' },
  { title: 'Outbound Calling', desc: 'One-click calling from the dashboard with live transcript streaming in real time.' },
  { title: 'Lead Intelligence', desc: 'Every call is scored 0–100 with extracted name, budget, preferences and next action.' },
  { title: 'WhatsApp Follow-ups', desc: 'Personalized follow-up messages sent automatically after each conversation.' },
]

const stats = [
  { k: '24/7', v: 'Always-on calling' },
  { k: '<2s', v: 'First-response latency' },
  { k: '0–100', v: 'Lead scoring' },
]

export default function Landing() {
  const { user } = useAuth()
  return (
    <div className="min-h-screen relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-grid opacity-60" />
      <div className="pointer-events-none absolute inset-0"
        style={{ background: 'radial-gradient(circle at 30% 15%, rgba(37,99,235,0.14) 0%, transparent 55%), radial-gradient(circle at 75% 80%, rgba(14,165,233,0.10) 0%, transparent 55%)' }} />

      <header className="relative z-10 flex items-center justify-between px-8 py-4 border-b border-border bg-surface/70 backdrop-blur-xl">
        <div className="flex items-center gap-3">
          <LogoMark size={36} />
          <div className="leading-tight">
            <h1 className="font-display font-semibold text-[17px] tracking-tightest">Realty Siksha</h1>
            <p className="text-[11px] text-slate-400">AI Calling Agent for Real Estate</p>
          </div>
        </div>
        <nav className="hidden md:flex items-center gap-8 text-sm text-slate-300">
          <a href="#features" className="hover:text-white transition">Features</a>
          <a href="#platform" className="hover:text-white transition">Platform</a>
        </nav>
        <Link to={user ? '/app' : '/login'}
          className="px-5 py-2 rounded-lg bg-gradient-to-r from-accent to-accent-2 font-semibold text-sm hover:opacity-90 transition shadow-glow">
          {user ? 'Open Dashboard' : 'Sign In'}
        </Link>
      </header>

      <main className="relative z-10 max-w-6xl mx-auto px-6 pt-24 pb-20">
        <div className="text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs border border-accent/40 text-accent-2 bg-accent/10 mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-accent-2" />
            Greater Noida Real Estate · 24/7 AI Concierge
          </div>
          <h2 className="font-display text-5xl md:text-6xl font-bold tracking-tightest leading-[1.05]">
            Your AI agent calls,
            <br />
            <span className="bg-gradient-to-r from-accent to-accent-2 bg-clip-text text-transparent">you close the deal.</span>
          </h2>
          <p className="mt-6 text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed">
            Realty Siksha speaks with every lead like a seasoned consultant — qualifying budget,
            preferences and timelines naturally, and handing you a fully scored lead after every call.
          </p>
          <div className="mt-10 flex items-center justify-center gap-3">
            <Link to="/login"
              className="px-7 py-3 rounded-xl bg-gradient-to-r from-accent to-accent-2 font-semibold shadow-glow hover:opacity-90 transition">
              Get Started
            </Link>
            <a href="#features"
              className="px-7 py-3 rounded-xl border border-border text-slate-200 hover:border-accent/40 hover:text-white transition">
              Learn more
            </a>
          </div>
        </div>

        <div id="platform" className="mt-16 grid grid-cols-3 gap-3 max-w-3xl mx-auto">
          {stats.map((s) => (
            <div key={s.v} className="p-5 rounded-xl bg-surface/80 border border-border text-center shadow-card">
              <div className="font-display text-2xl font-semibold tracking-tightest text-white">{s.k}</div>
              <div className="text-[11px] uppercase tracking-wider text-slate-500 mt-1">{s.v}</div>
            </div>
          ))}
        </div>

        <div id="features" className="mt-20 grid md:grid-cols-2 lg:grid-cols-4 gap-4 text-left">
          {features.map((f, i) => (
            <div key={f.title} className="p-6 rounded-2xl bg-surface border border-border hover:border-accent/40 hover:-translate-y-0.5 transition shadow-card">
              <div className="w-8 h-8 rounded-lg bg-accent/15 border border-accent/30 text-accent-2 flex items-center justify-center text-xs font-semibold mb-4">
                {String(i + 1).padStart(2, '0')}
              </div>
              <h3 className="font-semibold mb-1.5 text-[15px]">{f.title}</h3>
              <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </main>

      <footer className="relative z-10 border-t border-border">
        <div className="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <LogoMark size={22} />
            <span>&copy; {new Date().getFullYear()} Realty Siksha. All rights reserved.</span>
          </div>
          <div>Built for real estate professionals.</div>
        </div>
      </footer>
    </div>
  )
}
