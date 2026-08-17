# AI Calling Agent — Architecture & Study Guide

> Real-estate voice bot for GS Associates (Greater Noida). Twilio (voice) + Groq (LLM) +
> Supabase (Postgres) + FastAPI + React. Runs locally via ngrok; optionally deploys to Azure.

---

## 1. Stack

| Layer | Tech | Why |
|---|---|---|
| Telephony | Twilio (voice + WhatsApp sandbox) | `<Gather>` gives STT + TTS for free during trial |
| Speech | Twilio STT (`SpeechResult`) + Polly TTS (`Polly.Aditi`, en-IN) | Built into `<Gather>`, zero code |
| LLM | Groq — `openai/gpt-oss-120b` | Fast, free tier, JSON mode for extraction |
| Database | Supabase (Postgres) — `diusxnirleqjtppbuydl.supabase.co` | Free tier, REST SDK |
| Auth | Custom: PBKDF2 + JWT (PyJWT) | No external auth service needed |
| Frontend | React 18 + Vite 5 + Tailwind 3 | SPA built to `frontend/dist`, served by FastAPI |
| Server | FastAPI + uvicorn (`--reload`) | Async (WebSockets, webhooks) |
| Tunneling (dev) | ngrok → `https://trinity-eel-nanometer.ngrok-free.dev` | Exposes localhost for Twilio webhooks |

---

## 2. File map

```
PCode/
├─ main.py                    ← THE entry point. All HTTP routes + WS + call state machine
├─ start.sh                   ← dev launcher: kill 8000 → ngrok → PUBLIC_URL in .env → uvicorn
├─ telephony.py               ← CLI: place an outbound call from terminal
├─ test_llm.py                ← manual test of LLM brain + extraction
├─ supabase_migration.sql     ← PENDING: lead columns, phone_numbers, users, settings tables
├─ scripts/create_user.py     ← CLI: create a DB user (email/password)
├─ services/                  ← all business logic (imported by main.py)
│  ├─ logger.py               ← logging → console + /tmp/calling-agent-logs/app.log (rotating)
│  ├─ call_service.py         ← Twilio client, TwiML builders, outbound call
│  ├─ llm_service.py          ← LLMBrain (chat), lead extraction, scoring, WhatsApp text gen
│  ├─ whatsapp_service.py     ← WhatsApp sends (template-only on trial account)
│  ├─ database.py             ← all Supabase queries (calls, turns, users, numbers, settings)
│  └─ auth_service.py         ← PBKDF2 hashing, JWT create/verify, local (hardcoded) users
├─ frontend/                  ← React app (source) → npm run build → dist/
│  ├─ src/api.js              ← fetch wrapper (Bearer token, 401→/login) + wsUrl()
│  ├─ src/auth.jsx            ← AuthProvider / useAuth (login, logout, /me boot check)
│  ├─ src/App.jsx             ← routes: / landing, /login, /app (protected)
│  ├─ src/pages/Landing.jsx   ← public landing page
│  ├─ src/pages/Login.jsx     ← username + password login
│  ├─ src/pages/AppShell.jsx  ← header + tabs (Calls / WhatsApp) + logout
│  └─ src/components/
│     ├─ CallTab.jsx          ← full dashboard: live transcript WS, lead card, history,
│     │                          make-call, numbers manager, settings (default user id),
│     │                          WhatsApp sender modal
│     └─ WhatsAppTab.jsx      ← placeholder "Coming soon"
├─ archive/                   ← DEAD code kept for reference:
│  ├─ conversation.py         ← old media-stream orchestrator (Deepgram STT + TTS loop)
│  ├─ stt.py / tts.py         ← Deepgram streaming STT + gTTS→mulaw TTS (blueprint for future)
│  ├─ test_stt.py / test_tts.py
├─ dashboard.html             ← OLD single-file dashboard (superseded by React; not served)
├─ deploy.sh                  ← (stub) railway deployment helper
├─ requirements.txt           ← pinned Python deps
└─ .env                       ← ALL SECRETS (gitignored) — see §8
```

---

## 3. The call loop (heart of the app)

### Inbound call
```
Caller → Twilio number
  → Twilio POST /incoming-call  (public webhook, no auth)
      1. create_call() row in Supabase (user_id from ?user_id= or settings/env default)
      2. _calls[callSid] = {call_id, llm, from_number, transcript, turn_count, start_time}
      3. broadcast WS "call_started" → dashboard shows live
      4. respond TwiML: <Gather input="speech"> — Polly says greeting, Twilio listens
  → Caller speaks → Twilio POST /handle-speech  (SpeechResult text)
      1. append "User: ..." to state, save_turn(), broadcast WS "transcript"
      2. llm.generate_response(text) → LLMBrain (keeps full history per call)
      3. append "Agent: ...", broadcast, respond TwiML: Polly says reply + <Gather> again
  → loops until hangup
  → Twilio POST /call-status (completed)
      → end_call(): extract_lead_info(transcript) → lead score → save to Supabase
      → broadcast WS "call_ended" (lead + duration)
      → auto WhatsApp follow-up if WHATSAPP_AUTO_SEND=true and lead phone found
```

### Outbound call (from dashboard)
```
Dashboard "Start Call" → POST /outbound-call  (JWT required)
  body: {phone_number, from_number, base_url, user_id?}
  → Twilio calls.create(to, from_, url="{base_url}/incoming-call?user_id=...")
  → everything after = same inbound loop (user_id rides the query string)
```

Key detail: the whole conversation lives in `_calls` (in-memory dict). If the server
restarts mid-call, state is lost (the call just hears silence/error) — the `/call-status`
webhook still fires and ends things gracefully.

---

## 4. Dashboard data flow

```
React SPA (frontend/dist, served by FastAPI)
  ├─ POST /api/auth/login {username, password} → JWT (24h) → localStorage
  ├─ WS  /ws/dashboard?token=JWT  → live events: call_started / transcript / call_ended
  ├─ GET /api/calls?user_id=      → last 50 calls (lead card + history table)
  ├─ GET /api/numbers             → {twilio: [], target: []} (falls back to defaults)
  ├─ GET /api/users               → local users + DB users (for user-ID pickers)
  ├─ GET/PUT /api/settings        → default_user_id (DB settings table → env fallback)
  ├─ POST /api/numbers, DELETE /api/numbers/{id}
  ├─ POST /outbound-call          → start call
  ├─ POST /api/generate-whatsapp  → LLM writes follow-up text
  └─ POST /api/send-whatsapp      → send (template-only on this trial account)
```

Auth guard: every `/api/*` route above depends on `get_current_user` (Bearer JWT).
`frontend/src/api.js` auto-clears the token and redirects to `/login` on 401.
The WS endpoint closes with 4401 on a bad token; CallTab self-heals by logging out.

---

## 5. WhatsApp flow

- `services/whatsapp_service.py`:
  - `send_whatsapp(to, message, content_sid, content_variables)` — kwargs are lowercase
    (`to=`, `from_=`, `body=`, `content_sid=`, `content_variables=`) — **this was a real
    bug source**: mixing `To`/`From` style kwargs silently breaks the send.
  - `send_followup_whatsapp(...)` — auto after call; uses `WHATSAPP_CONTENT_SID` if set
    (sends with template variables `{"1": name, "2": property, "3": next step}`), else
    free-form text.
- **Trial-account constraint**: free-form messages are rejected (`ContentSid Required`).
  The current SID `HXfe5ab5f00277942d4d4200328b4d403c` = Twilio's default "Appointment
  Reminder" template (no variables — wrong content). You must create a custom template
  with variables `{{1}} {{2}} {{3}}` and update `WHATSAPP_CONTENT_SID`.
  Until then `WHATSAPP_AUTO_SEND=false` keeps the wrong message from being sent.

---

## 6. Auth internals

| Concern | Where | Notes |
|---|---|---|
| Hashing | `auth_service.hash_password/verify_password` | PBKDF2-SHA256, 100k iters, format `pbkdf2$iter$salt$hex` |
| Tokens | `create_token/verify_token` | HS256, 24h TTL, claims: sub, email, name |
| Local users | `authenticate_local` | hardcoded: `gknsngr7/1234` (Gaurav Nigam), `shyam098/abcd` (Shyam Dubey); deterministic uuid5 IDs |
| DB users | `database.create_user/get_user_by_email` | via `scripts/create_user.py`; needs migration |
| HTTP guard | `get_current_user` (HTTPBearer) | `Depends(get_current_user)` on every protected route |
| Secret | env `JWT_SECRET` | falls back to `dev-secret-change-me` with a warning — **set it in production** |

---

## 7. Database (Supabase)

Tables you have now:
- `users` — id, email, company_name, plan, created_at (pre-existing; `name`/`password_hash` pending)
- `calls` — id, user_id, agent_id, twilio_call_sid, direction, status, started_at, created_at,
  transcript, extracted_data, lead_score, duration_seconds, ended_at
- `conversation_turns` — per-turn logs
- `agents` — agent profiles

Pending in `supabase_migration.sql` (MUST be run in Supabase SQL Editor):
- `calls` + 13 lead columns (lead_name, lead_phone, lead_email, budget_min/max, locations,
  bhk, property_type, timeline, purpose, interested, call_summary, next_action)
- `phone_numbers` table (with RLS "allow all")
- `users` + name/password_hash columns
- `settings` table (key/value — stores `default_user_id`)

Until the migration runs: login user creation fails, number manager silently empties,
lead columns aren't saved (all errors are caught and logged, app keeps working).

---

## 8. Environment variables (.env — gitignored)

```
TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN   # Twilio credentials
TWILIO_PHONE_NUMBER                      # +17372212163 (voice)
TWILIO_WHATSAPP_FROM                     # whatsapp:+17372508034 (sandbox)
WHATSAPP_AUTO_SEND                       # false until proper template exists
WHATSAPP_CONTENT_SID                     # HXfe5ab5... (default "Appointment Reminder" template)
DEEPGRAM_API_KEY                         # (reserved — streaming STT upgrade path)
GROQ_API_KEY                             # gsk_HITL... (LLM)
GROQ_MODEL / GROQ_WHATSAPP_MODEL         # openai/gpt-oss-120b / groq/compound-mini
SUPABASE_URL / SUPABASE_KEY              # Postgres REST endpoint + anon key
PUBLIC_URL                               # ngrok URL (rewritten by start.sh every boot)
AGENT_NAME / COMPANY_NAME                # "Shyam Dhar Dubey" / "GS Associates"
DEFAULT_USER_ID / DEFAULT_AGENT_ID       # fallback UUIDs for call attribution
JWT_SECRET                               # auth signing key (set!)
```

---

## 9. Debugging guide

**First stop — logs:**
```
tail -f /tmp/calling-agent-logs/app.log      # app-level (svc.* loggers)
tail -f /tmp/calling-agent-logs/server.log   # uvicorn access log
tail -f /tmp/calling-agent-logs/ngrok.log    # tunnel issues
```

**Test endpoints without a phone:**
```bash
# Full TwiML from the webhook (simulate Twilio):
curl -X POST http://localhost:8000/incoming-call -d 'CallSid=test1' -H 'Content-Type: application/x-www-form-urlencoded'
# Health:
curl http://localhost:8000/health
# Login (returns JWT):
curl -X POST http://localhost:8000/api/auth/login -H 'Content-Type: application/json' \
     -d '{"username":"gknsngr7","password":"1234"}'
# Protected route (use the token):
curl http://localhost:8000/api/calls -H "Authorization: Bearer $TOKEN"
```

**Common failures & where to look:**

| Symptom | Cause → Fix |
|---|---|
| WS `/ws/dashboard` 403 loop | stale JWT from before `JWT_SECRET` existed → hard-refresh + re-login |
| From/To dropdowns empty | `phone_numbers` table missing (migration) → falls back to defaults only when arrays are empty; empty `[]` is truthy so defaults were skipped — fixed with `.length` checks |
| WhatsApp send `ContentSid Required` | trial template-only → create custom variable template |
| `PGRST205` / `PGRST204` | Supabase table/column missing → run `supabase_migration.sql` |
| LLM says "could you repeat that" | Groq 404 model → model not on your key; pick from the tested list (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `groq/compound-mini`, `qwen/qwen3.6-27b`) |
| No WhatsApp after call | lead phone not extracted → webhook `From` fallback covers it (verify log line "using caller From number") |
| Call drops mid-sentence | `uvicorn --reload` restarted the server mid-call → in-memory `_calls` state lost |
| Logout on refresh / 401 spree | `JWT_SECRET` changed after tokens were issued → re-login |

**Twilio console** (debug webhook traffic): Active Calls → open SID → "Incoming call"
shows the exact URL Twilio fetched and the TwiML it got back.

---

## 10. Run it

```bash
./start.sh                 # dev: ngrok + uvicorn, prints Local/Public URLs
cd frontend && npm run build   # rebuild React after any frontend change
venv/bin/python scripts/create_user.py email "Name" password   # add a DB user
```

Production (planned): FastAPI behind a real domain (Azure App Service + GoDaddy DNS),
no ngrok. See §2 in the migration research: Twilio is on a trial with ~34 voice minutes
left — the plan is to move STT/TTS off Twilio (Deepgram streaming + edge-tts, blueprint in
`archive/`) and evaluate Telnyx/Exotel for cheaper India telephony.

---

## 11. Quick mental model

```
Twilio number ⇄ TwiML webhooks ⇄ FastAPI ⇄ (Groq LLM · Supabase · JWT) ⇄ React dashboard
                                              ⇅ (WebSocket live feed)
                                    WhatsApp follow-ups (template-only for now)
```

State lives in `_calls` (RAM) per call + `calls` table (Postgres) for history.
The LLM does three jobs: **conversation** (stateful per call), **extraction** (lead JSON →
score), **WhatsApp text** (follow-up copy + template variables).