import React, { useCallback, useEffect, useRef, useState } from 'react'
import { api, wsUrl, clearToken } from '../api'

/* ── helpers ──────────────────────────────────────────────────────────── */

function fmtINR(n) {
  if (n >= 10000000) return '₹' + (n / 10000000).toFixed(1) + ' Cr'
  if (n >= 100000) return '₹' + (n / 100000).toFixed(1) + ' L'
  return '₹' + Number(n).toLocaleString('en-IN')
}
function fmtDuration(s) { return s < 60 ? s + 's' : Math.floor(s / 60) + 'm ' + (s % 60) + 's' }
function fmtTime(iso) { return iso ? new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : '' }
function fmtDateTime(iso) {
  return iso ? new Date(iso).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—'
}

const DEFAULT_NUMS = {
  twilio: [{ label: 'Main', number: '+17372212163' }, { label: 'Trial', number: '+17372508034' }],
  target: [{ label: 'Client 1', number: '+917525027889' }, { label: 'Client 2', number: '+919131405229' }],
}

const Input = ({ label, ...props }) => (
  <div>
    <label className="block text-xs text-gray-400 mb-1.5">{label}</label>
    <input {...props} className="w-full px-3.5 py-2.5 rounded-lg bg-surface-2 border border-border focus:border-accent outline-none text-sm" />
  </div>
)
const Select = ({ label, children, ...props }) => (
  <div>
    <label className="block text-xs text-gray-400 mb-1.5">{label}</label>
    <select {...props} className="w-full px-3 py-2.5 rounded-lg bg-surface-2 border border-border focus:border-accent outline-none text-sm">
      {children}
    </select>
  </div>
)

/* ── Lead card ─────────────────────────────────────────────────────────── */

function LeadCard({ lead, duration }) {
  const row = (k, v) => (
    <div className="flex items-start justify-between gap-4 py-1.5 border-b border-border/60 last:border-0">
      <span className="text-xs text-gray-500 shrink-0 pt-0.5">{k}</span>
      <span className="text-sm text-right">{v || '—'}</span>
    </div>
  )
  const budget = lead?.budget_min || lead?.budget_max
    ? `${lead.budget_min ? fmtINR(lead.budget_min) : ''}${lead.budget_min && lead.budget_max ? ' – ' : ''}${lead.budget_max ? fmtINR(lead.budget_max) : ''}`
    : null
  return (
    <div className="p-5 rounded-2xl bg-surface border border-border">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-sm">Lead Intelligence</h3>
        {lead && <span className={`text-xs px-2 py-0.5 rounded-full ${lead.interested === false ? 'bg-red/15 text-red' : 'bg-green/15 text-green'}`}>
          {lead.interested === false ? '✗ Not interested' : '✓ Interested'}
        </span>}
      </div>
      {!lead ? (
        <p className="text-sm text-gray-500 py-6 text-center">No call data yet</p>
      ) : (
        <div>
          {row('Name', lead.name)}
          {row('Budget', budget)}
          {row('BHK', lead.bhk ? lead.bhk + ' BHK' : null)}
          {row('Locations', lead.locations?.length ? lead.locations.join(', ') : null)}
          {row('Timeline', lead.timeline)}
          {row('Purpose', lead.purpose)}
          <div className="py-2">
            <div className="flex justify-between text-xs mb-1.5">
              <span className="text-gray-500">Lead Score</span>
              <span className="font-semibold">{lead.lead_score ?? 0} / 100</span>
            </div>
            <div className="h-1.5 rounded-full bg-surface-2 overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-accent to-accent-2 transition-all duration-500"
                style={{ width: `${lead.lead_score ?? 0}%` }} />
            </div>
          </div>
          {row('Summary', lead.call_summary)}
          {row('Next Action', lead.next_action)}
          {row('Duration', duration ? fmtDuration(duration) : null)}
        </div>
      )}
    </div>
  )
}

/* ── Live transcript ───────────────────────────────────────────────────── */

function TranscriptBox({ turns, status }) {
  const boxRef = useRef(null)
  useEffect(() => { boxRef.current?.scrollTo({ top: boxRef.current.scrollHeight, behavior: 'smooth' }) }, [turns])
  return (
    <div className="p-5 rounded-2xl bg-surface border border-border flex flex-col min-h-[420px]">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-sm">Live Transcript</h3>
        <span className={`text-xs px-2 py-0.5 rounded-full ${status === 'live' ? 'bg-green/15 text-green' : 'bg-red/15 text-red'}`}>
          {status === 'live' ? '● Live' : '● Reconnecting…'}
        </span>
      </div>
      <div ref={boxRef} className="flex-1 space-y-3 overflow-y-auto max-h-[520px] pr-2">
        {turns.length === 0 && <p className="text-sm text-gray-500 text-center pt-10">Waiting for a call…</p>}
        {turns.map((t, i) => (
          <div key={i} className={`flex ${t.speaker === 'agent' ? 'justify-start' : 'justify-end'}`}>
            <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 ${t.speaker === 'agent' ? 'bg-surface-2 border border-border rounded-tl-sm' : 'bg-gradient-to-br from-accent/25 to-accent-2/25 border border-accent/30 rounded-tr-sm'}`}>
              <div className="text-[10px] text-gray-500 mb-0.5">{t.speaker === 'agent' ? '🤖 Agent' : '👤 Caller'} · {fmtTime(t.timestamp)}</div>
              <p className="text-sm leading-relaxed">{t.text}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── History table ─────────────────────────────────────────────────────── */

function HistoryTable({ calls, onWhatsApp }) {
  if (!calls.length) return <p className="text-sm text-gray-500 text-center py-8">No calls yet</p>
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500 border-b border-border">
            <th className="py-2.5 pr-4 font-medium">Time</th>
            <th className="py-2.5 pr-4 font-medium">Direction</th>
            <th className="py-2.5 pr-4 font-medium">Duration</th>
            <th className="py-2.5 pr-4 font-medium">Score</th>
            <th className="py-2.5 pr-4 font-medium">Status</th>
            <th className="py-2.5 font-medium">WhatsApp</th>
          </tr>
        </thead>
        <tbody>
          {calls.map((c, i) => (
            <tr key={c.id} className="border-b border-border/50 last:border-0 hover:bg-surface-2/40 transition">
              <td className="py-2.5 pr-4 text-gray-400">{fmtDateTime(c.started_at)}</td>
              <td className="py-2.5 pr-4 capitalize">{c.direction || '—'}</td>
              <td className="py-2.5 pr-4">{c.duration_seconds ? fmtDuration(c.duration_seconds) : '—'}</td>
              <td className="py-2.5 pr-4">{c.lead_score != null ? c.lead_score + '/100' : '—'}</td>
              <td className="py-2.5 pr-4">
                <span className={`text-xs px-2 py-0.5 rounded-full capitalize ${c.status === 'completed' ? 'bg-green/15 text-green' : 'bg-yellow-500/15 text-yellow-400'}`}>{c.status || 'unknown'}</span>
              </td>
              <td className="py-2.5">
                {c.lead_phone ? (
                  <button onClick={() => onWhatsApp(i)}
                    className="text-xs px-3 py-1.5 rounded-lg bg-[#25d366] font-semibold text-black hover:opacity-90 transition shadow-glow-green">
                    💬 WhatsApp
                  </button>
                ) : <span className="text-gray-600 text-xs">—</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ── Modals ────────────────────────────────────────────────────────────── */

function Modal({ open, onClose, title, children }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-6" onClick={onClose}>
      <div className="w-full max-w-lg rounded-2xl bg-surface border border-border p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-5">
          <h2 className="font-semibold">{title}</h2>
          <button onClick={onClose} className="text-gray-500 hover:text-white text-lg leading-none">✕</button>
        </div>
        {children}
      </div>
    </div>
  )
}

/* ── Main tab ──────────────────────────────────────────────────────────── */

export default function CallTab() {
  const [turns, setTurns] = useState([])
  const [lead, setLead] = useState(null)
  const [duration, setDuration] = useState(null)
  const [calls, setCalls] = useState([])
  const [numbers, setNumbers] = useState(null)
  const [wsStatus, setWsStatus] = useState('connecting')

  const [showCall, setShowCall] = useState(false)
  const [showNumbers, setShowNumbers] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showWhatsApp, setShowWhatsApp] = useState(false)
  const [waIdx, setWaIdx] = useState(-1)

  const [defaultUserId, setDefaultUserId] = useState('')
  const [users, setUsers] = useState([])

  // base URL for outbound call
  const [baseUrl, setBaseUrl] = useState(window.location.origin)

  const loadHistory = useCallback(async () => {
    try { setCalls(await api('/api/calls')) } catch (e) { console.warn('history load failed', e) }
  }, [])
  const loadNumbers = useCallback(async () => {
    try {
      const n = await api('/api/numbers')
      setNumbers({ twilio: n.twilio || [], target: n.target || [] })
    } catch (e) { console.warn('numbers load failed', e) }
  }, [])
  const loadSettings = useCallback(async () => {
    try {
      const s = await api('/api/settings')
      setDefaultUserId(s.default_user_id)
    } catch (e) { console.warn('settings load failed', e) }
    try { setUsers(await api('/api/users')) } catch (e) { console.warn('users load failed', e) }
  }, [])
  const loadAll = useCallback(() => { loadHistory(); loadNumbers(); loadSettings() }, [loadHistory, loadNumbers, loadSettings])

  useEffect(() => { loadAll() }, [loadAll])

  // WebSocket live feed
  useEffect(() => {
    let ws, timer, wasOpen = false
    const connect = () => {
      ws = new WebSocket(wsUrl('/ws/dashboard'))
      ws.onopen = () => { wasOpen = true; setWsStatus('live'); clearTimeout(timer) }
      ws.onclose = () => {
        if (!wasOpen) {
          // Never connected — token is stale/bad. Log out and reload.
          clearToken()
          window.location.href = '/login'
          return
        }
        setWsStatus('reconnecting')
        timer = setTimeout(connect, 3000)
      }
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data)
        if (msg.type === 'call_started') {
          setTurns([]); setLead(null); setDuration(null)
          setTurns([{ speaker: 'sys', text: `Call started ${fmtTime(msg.timestamp)}`, timestamp: msg.timestamp }])
        } else if (msg.type === 'transcript') {
          setTurns((t) => [...t, { speaker: msg.speaker, text: msg.text, timestamp: msg.timestamp }])
        } else if (msg.type === 'call_ended') {
          setTurns((t) => [...t, { speaker: 'sys', text: `Call ended · ${msg.duration}s`, timestamp: msg.timestamp }])
          setLead(msg.lead); setDuration(msg.duration)
          loadHistory()
        }
      }
    }
    connect()
    return () => { clearTimeout(timer); ws?.close() }
  }, [loadHistory])

  const waCall = waIdx >= 0 ? calls[waIdx] : null

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-bold tracking-tight">Calls</h2>
          <span className={`text-xs px-2 py-0.5 rounded-full ${wsStatus === 'live' ? 'bg-green/15 text-green' : 'bg-red/15 text-red'}`}>
            {wsStatus === 'live' ? '● Live' : '● Reconnecting'}
          </span>
        </div>
        <div className="flex gap-2.5">
          <button onClick={() => setShowSettings(true)} className="px-4 py-2 rounded-lg text-sm border border-border text-gray-300 hover:border-accent/40 transition">⚙ Settings</button>
          <button onClick={() => setShowNumbers(true)} className="px-4 py-2 rounded-lg text-sm border border-border text-gray-300 hover:border-accent/40 transition">Numbers</button>
          <button onClick={() => setShowCall(true)} className="px-5 py-2 rounded-lg text-sm font-semibold bg-gradient-to-r from-accent to-accent-2 shadow-glow hover:opacity-90 transition">+ New Call</button>
        </div>
      </div>

      <div className="grid lg:grid-cols-[1.6fr_1fr] gap-6 items-start">
        <TranscriptBox turns={turns} status={wsStatus} />
        <LeadCard lead={lead} duration={duration} />
      </div>

      <div className="p-5 rounded-2xl bg-surface border border-border">
        <h3 className="font-semibold text-sm mb-3">Call History</h3>
        <HistoryTable calls={calls} onWhatsApp={(i) => { setWaIdx(i); setShowWhatsApp(true) }} />
      </div>

      {/* Make call modal */}
      <Modal open={showCall} onClose={() => setShowCall(false)} title="📞 Make an Outbound Call">
        <div className="space-y-4">
          <Select label="From (Twilio Number)" value={undefined} onChange={() => {}}>
            {(numbers?.twilio?.length ? numbers.twilio : DEFAULT_NUMS.twilio).map((n, i) => (
              <option key={i} value={n.number}>{n.label} — {n.number}</option>
            ))}
          </Select>
          <Select label="To (Target Number)" value={undefined} onChange={() => {}}>
            {(numbers?.target?.length ? numbers.target : DEFAULT_NUMS.target).map((n, i) => (
              <option key={i} value={n.number}>{n.label} — {n.number}</option>
            ))}
          </Select>
          <Input label="Server URL" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
          <MakeCallButton from={(numbers?.twilio || DEFAULT_NUMS.twilio)[0]?.number}
            to={(numbers?.target || DEFAULT_NUMS.target)[0]?.number} baseUrl={baseUrl}
            defaultUserId={defaultUserId} users={users} />
        </div>
      </Modal>

      {/* Settings modal */}
      <Modal open={showSettings} onClose={() => setShowSettings(false)} title="⚙ Settings">
        <SettingsPanel defaultUserId={defaultUserId} users={users}
          onSaved={(id) => { setDefaultUserId(id); setShowSettings(false); loadHistory() }} />
      </Modal>

      {/* Numbers modal */}
      <Modal open={showNumbers} onClose={() => { setShowNumbers(false); loadNumbers() }} title="Manage Numbers">
        <NumbersManager numbers={numbers} onChange={loadNumbers} />
      </Modal>

      {/* WhatsApp modal */}
      <Modal open={showWhatsApp} onClose={() => setShowWhatsApp(false)} title="💬 Send WhatsApp Message">
        <WhatsAppSender call={waCall} onClose={() => setShowWhatsApp(false)} />
      </Modal>
    </div>
  )
}

/* ── Make call action ──────────────────────────────────────────────────── */

function MakeCallButton({ from, to, baseUrl, defaultUserId, users }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const fromSel = useRef(null)
  const toSel = useRef(null)
  const baseSel = useRef(null)
  const userSel = useRef(null)

  async function call() {
    setErr(''); setOk(''); setBusy(true)
    try {
      const data = await api('/outbound-call', {
        method: 'POST',
        body: {
          phone_number: toSel.current?.value || to,
          from_number: fromSel.current?.value || from,
          base_url: baseSel.current?.value || baseUrl,
          user_id: userSel.current?.value || defaultUserId,
        },
      })
      setOk(`✓ Call initiated (${data.call_sid.slice(0, 8)}…)`)
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  return (
    <div>
      <div>
        <label className="block text-xs text-gray-400 mb-1.5">User ID (attributed to this call)</label>
        <select ref={userSel} defaultValue={defaultUserId}
          className="w-full px-3 py-2.5 rounded-lg bg-surface-2 border border-border text-sm outline-none">
          {defaultUserId && <option value={defaultUserId}>Default — {defaultUserId.slice(0, 8)}…</option>}
          {users.map((u) => (
            <option key={u.id} value={u.id}>{u.name} — {u.email}</option>
          ))}
        </select>
        <p className="text-[11px] text-gray-600 mt-1.5">Falls back to the default set in ⚙ Settings if unset.</p>
      </div>
      <div className="flex items-center gap-3 mt-4">
        <select ref={fromSel} className="flex-1 px-3 py-2 rounded-lg bg-surface-2 border border-border text-sm outline-none" defaultValue={from}>
          <option value={from}>{from}</option>
        </select>
        <select ref={toSel} className="flex-1 px-3 py-2 rounded-lg bg-surface-2 border border-border text-sm outline-none" defaultValue={to}>
          <option value={to}>{to}</option>
        </select>
        <input ref={baseSel} defaultValue={baseUrl} className="flex-1 px-3 py-2 rounded-lg bg-surface-2 border border-border text-sm outline-none" />
      </div>
      {err && <p className="text-sm text-red mt-2">{err}</p>}
      {ok && <p className="text-sm text-green mt-2">{ok}</p>}
      <button onClick={call} disabled={busy}
        className="mt-4 w-full py-2.5 rounded-lg bg-gradient-to-r from-accent to-accent-2 font-semibold text-sm shadow-glow hover:opacity-90 transition disabled:opacity-50">
        {busy ? 'Calling…' : 'Start Call'}
      </button>
    </div>
  )
}

/* ── Settings panel ─────────────────────────────────────────────────────── */

function SettingsPanel({ defaultUserId, users, onSaved }) {
  const [value, setValue] = useState(defaultUserId)
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [busy, setBusy] = useState(false)

  async function save() {
    setErr(''); setOk(''); setBusy(true)
    try {
      const res = await api('/api/settings', { method: 'PUT', body: { default_user_id: value.trim() } })
      setOk(`✓ Saved — ${res.default_user_id.slice(0, 8)}…`)
      onSaved(res.default_user_id)
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs text-gray-400 mb-1.5">Pick from known users</label>
        <select value={value} onChange={(e) => setValue(e.target.value)}
          className="w-full px-3 py-2.5 rounded-lg bg-surface-2 border border-border text-sm outline-none">
          {users.map((u) => (
            <option key={u.id} value={u.id}>{u.name} — {u.email}</option>
          ))}
        </select>
      </div>
      <Input label="…or paste any User ID (UUID)" value={value} onChange={(e) => setValue(e.target.value)}
        placeholder="00000000-0000-0000-0000-000000000001" />
      {err && <p className="text-sm text-red">{err}</p>}
      {ok && <p className="text-sm text-green">{ok}</p>}
      <div className="flex justify-end gap-2.5">
        <button onClick={() => onSaved(value)} className="px-4 py-2 rounded-lg text-sm border border-border text-gray-300 hover:border-accent/40 transition">Cancel</button>
        <button onClick={save} disabled={busy || !value.trim()}
          className="px-5 py-2 rounded-lg text-sm font-semibold bg-gradient-to-r from-accent to-accent-2 shadow-glow hover:opacity-90 transition disabled:opacity-50">
          {busy ? 'Saving…' : 'Save Default'}
        </button>
      </div>
      <p className="text-[11px] text-gray-600">The default User ID is used for inbound calls and as the history filter. Outbound calls can override it per-call.</p>
    </div>
  )
}

/* ── Numbers manager ───────────────────────────────────────────────────── */

function NumbersManager({ numbers, onChange }) {
  const [label, setLabel] = useState('')
  const [number, setNumber] = useState('')
  const [type, setType] = useState('twilio')
  const [err, setErr] = useState('')

  async function add() {
    setErr('')
    if (!label || !/^\+\d{8,15}$/.test(number)) { setErr('Enter a label and valid number, e.g. +917525027889'); return }
    try {
      await api('/api/numbers', { method: 'POST', body: { type, label, number } })
      setLabel(''); setNumber(''); onChange()
    } catch (e) { setErr(e.message) }
  }
  async function del(id) {
    try { await api(`/api/numbers/${id}`, { method: 'DELETE' }); onChange() } catch (e) { setErr(e.message) }
  }

  const list = (t) => (numbers?.[t] || []).map((n) => (
    <div key={n.id} className="flex items-center justify-between px-3 py-2 rounded-lg bg-surface-2/60 border border-border/60 mb-1.5">
      <div>
        <div className="text-xs font-medium">{n.label}</div>
        <div className="text-[11px] text-gray-500 font-mono">{n.number}</div>
      </div>
      <button onClick={() => del(n.id)} className="text-gray-500 hover:text-red text-sm px-1">✕</button>
    </div>
  ))

  return (
    <div className="space-y-4">
      <div>
        <div className="text-xs text-gray-400 mb-1.5 uppercase tracking-wide">Twilio Numbers (From)</div>
        {list('twilio')}
        {!numbers?.twilio?.length && <p className="text-xs text-gray-600 mb-2">No saved numbers</p>}
      </div>
      <div>
        <div className="text-xs text-gray-400 mb-1.5 uppercase tracking-wide">Target Numbers (To)</div>
        {list('target')}
        {!numbers?.target?.length && <p className="text-xs text-gray-600 mb-2">No saved numbers</p>}
      </div>
      <div className="flex gap-2 items-end">
        <select value={type} onChange={(e) => setType(e.target.value)}
          className="px-3 py-2 rounded-lg bg-surface-2 border border-border text-sm outline-none">
          <option value="twilio">Twilio</option>
          <option value="target">Target</option>
        </select>
        <Input label="Label" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="e.g. Client 1" />
        <Input label="Number" value={number} onChange={(e) => setNumber(e.target.value)} placeholder="+917525027889" />
        <button onClick={add} className="px-4 py-2.5 rounded-lg bg-gradient-to-r from-accent to-accent-2 text-sm font-semibold shadow-glow hover:opacity-90 transition">Add</button>
      </div>
      {err && <p className="text-sm text-red">{err}</p>}
    </div>
  )
}

/* ── WhatsApp sender ───────────────────────────────────────────────────── */

function WhatsAppSender({ call, onClose }) {
  const [phone, setPhone] = useState(call?.lead_phone || '')
  const [message, setMessage] = useState('')
  const [err, setErr] = useState('')
  const [ok, setOk] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => { setPhone(call?.lead_phone || ''); setMessage(''); setErr(''); setOk('') }, [call])

  async function generate() {
    setErr(''); setOk(''); setBusy(true)
    try {
      const data = await api('/api/generate-whatsapp', { method: 'POST', body: { transcript: call?.transcript, lead: call } })
      setMessage(data.message)
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  async function send() {
    setErr(''); setOk('')
    if (!phone) { setErr('Enter a phone number'); return }
    if (!message) { setErr('Type a message or generate one with AI'); return }
    setBusy(true)
    try {
      const data = await api('/api/send-whatsapp', { method: 'POST', body: { phone, message } })
      setOk(`✓ Sent (${data.sid.slice(0, 8)}…)`)
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-4">
      <Input label="To (Phone)" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+919131405229" />
      <div>
        <label className="block text-xs text-gray-400 mb-1.5">Message</label>
        <textarea rows={4} value={message} onChange={(e) => setMessage(e.target.value)}
          placeholder="Type a message, or click ✨ Generate with AI"
          className="w-full px-3.5 py-2.5 rounded-lg bg-surface-2 border border-border focus:border-accent outline-none text-sm resize-y" />
      </div>
      {err && <p className="text-sm text-red">{err}</p>}
      {ok && <p className="text-sm text-green">{ok}</p>}
      <div className="flex justify-end gap-2.5">
        <button onClick={generate} disabled={busy}
          className="px-4 py-2 rounded-lg text-sm border border-border text-gray-300 hover:border-accent/40 transition disabled:opacity-50">
          ✨ Generate with AI
        </button>
        <button onClick={send} disabled={busy}
          className="px-5 py-2 rounded-lg text-sm font-semibold bg-[#25d366] text-black shadow-glow-green hover:opacity-90 transition disabled:opacity-50">
          {busy ? 'Sending…' : 'Send'}
        </button>
      </div>
    </div>
  )
}