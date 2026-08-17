import os
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import Response, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from services.logger import setup_logging, get_logger
from services.llm_service import LLMBrain, extract_lead_info
from services.database import Database
from services.auth_service import (
    hash_password, verify_password, create_token, get_current_user,
)
from services.call_service import (
    build_gather_response, build_error_hangup, make_outbound_call,
)
from services.whatsapp_service import send_whatsapp, send_followup_whatsapp
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
setup_logging()
log = get_logger("api")

app = FastAPI(title="AI Calling Agent")
db = Database()

# In-memory conversation state keyed by CallSid
_calls: dict[str, dict] = {}

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")


def _serve_index() -> FileResponse:
    return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))


class ConnectionManager:
    def __init__(self):
        self._connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self._connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self._connections:
            self._connections.remove(websocket)

    async def broadcast(self, event: dict):
        dead = []
        for ws in self._connections:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


def _get_base_url(request: Request) -> str:
    public_url = os.getenv("PUBLIC_URL", "").rstrip("/")
    if public_url:
        return public_url
    host = request.headers.get("x-forwarded-host") or request.headers["host"]
    proto = request.headers.get("x-forwarded-proto", "https")
    return f"{proto}://{host}"


@app.get("/")
async def root():
    return _serve_index()


@app.get("/login")
@app.get("/app")
async def spa_fallback():
    return _serve_index()


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_redirect():
    return _serve_index()


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Auth ───────────────────────────────────────────────────────────────────

@app.post("/api/auth/login")
async def login(request: Request):
    from services.auth_service import authenticate_local
    body = await request.json()
    username = (body.get("username") or body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password are required")
    user = authenticate_local(username, password)
    if user:
        token = create_token(user["id"], user["username"], name=user["name"])
        log.info("login OK: %s (local)", username)
        return {"token": token, "user": user}
    db_user = await db.get_user_by_email(username)
    if not db_user or not verify_password(password, db_user.get("password_hash", "")):
        log.warning("failed login attempt for %s", username)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_token(db_user["id"], db_user["email"], name=db_user.get("name", ""))
    log.info("login OK: %s", username)
    return {"token": token, "user": {"id": db_user["id"], "username": db_user["email"], "name": db_user.get("name"), "source": "db"}}


@app.get("/api/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {"id": user["id"], "username": user.get("email"), "email": user.get("email"), "name": user.get("name")}


@app.post("/api/auth/signup")
async def signup(request: Request):
    import re as _re
    from services.auth_service import hash_password
    body = await request.json()
    username = (body.get("username") or "").strip().lower()
    password = body.get("password") or ""
    confirm = body.get("confirm_password") or ""
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password are required")
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if not _re.match(r"^[a-z0-9._-]+$", username):
        raise HTTPException(status_code=400, detail="Username can only contain letters, numbers, dots, underscores and hyphens")
    if not _re.match(r"^(?=.*[0-9])(?=.*[^A-Za-z0-9]).{8,}$", password):
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters with at least one number and one special character")
    if password != confirm:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    if username in ("gknsngr7", "shyam098"):
        raise HTTPException(status_code=409, detail="Username already taken")
    existing = await db.get_user_by_email(username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")
    try:
        user_id = await db.create_user(username, username, hash_password(password))
    except Exception as e:
        log.error("signup DB error for %s: %s", username, str(e)[:120])
        raise HTTPException(status_code=500, detail="Database error — run supabase_migration.sql in Supabase SQL Editor first")
    token = create_token(user_id, username, name=username)
    log.info("signup OK: %s", username)
    return {"token": token, "user": {"id": user_id, "username": username, "email": username, "name": username, "source": "db"}}


@app.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket, token: str = ""):
    from services.auth_service import verify_token
    if not token:
        log.warning("WS rejected: no token in URL (stale page/dashboard.html or logged-out tab)")
        await websocket.close(code=4401)
        return
    try:
        verify_token(token)
    except Exception as e:
        log.warning("WS rejected: invalid/expired token (%s)", str(e)[:60])
        await websocket.close(code=4401)
        return
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/calls")
async def get_calls(request: Request, user: dict = Depends(get_current_user)):
    user_id = request.query_params.get("user_id") or await _default_user_id()
    try:
        data = await db.get_user_calls(user_id, limit=50)
        return data or []
    except Exception as e:
        log.warning("get_calls error: %s", e)
        return []


async def _default_user_id() -> str:
    try:
        value = await db.get_setting("default_user_id")
        if value:
            return value
    except Exception:
        pass
    return os.getenv("DEFAULT_USER_ID", "default")


@app.post("/incoming-call")
async def handle_incoming_call(request: Request):
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")
    from_number = form_data.get("From", "")
    base_url = _get_base_url(request)

    # Only initialize on first hit (not on silence-redirect)
    if call_sid not in _calls:
        try:
            user_id = request.query_params.get("user_id") or await _default_user_id()
            call_id = await db.create_call(
                user_id=user_id,
                agent_id=os.getenv("DEFAULT_AGENT_ID", "default"),
                twilio_sid=call_sid,
                direction="inbound",
            )
        except Exception as e:
            log.warning("db create_call error (continuing): %s", e)
            import uuid
            call_id = str(uuid.uuid4())

        llm = LLMBrain()
        _calls[call_sid] = {
            "call_id": call_id,
            "llm": llm,
            "from_number": from_number,
            "transcript": [],
            "turn_count": 0,
            "start_time": datetime.now(timezone.utc),
        }
        await manager.broadcast({"type": "call_started", "call_id": call_id,
                                  "timestamp": datetime.now(timezone.utc).isoformat()})
        agent = os.getenv("AGENT_NAME", "Shyam Dhar Dubey")
        company = os.getenv("COMPANY_NAME", "Elite Realty")
        greeting = (
            f"Hello! I'm {agent} calling from {company}. "
            f"We are a real estate consultancy specializing in properties in Greater Noida. "
            f"Is this a good time to talk?"
        )
        _calls[call_sid]["transcript"].append(f"Agent: {greeting}")
        log.info("call %s — greeting", call_sid)
        return build_gather_response(greeting, base_url)

    # Silence re-prompt
    log.info("call %s — silence re-prompt", call_sid)
    return build_gather_response("Hello? Are you there?", base_url)


@app.post("/handle-speech")
async def handle_speech(request: Request):
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")
    speech_result = form_data.get("SpeechResult", "")
    base_url = _get_base_url(request)

    log.info("call %s | User: %s", call_sid, speech_result)

    state = _calls.get(call_sid)
    if not state:
        return build_error_hangup()

    state["turn_count"] += 1
    state["transcript"].append(f"User: {speech_result}")
    call_id = state["call_id"]

    await manager.broadcast({"type": "transcript", "call_id": call_id,
                              "speaker": "user", "text": speech_result,
                              "timestamp": datetime.now(timezone.utc).isoformat()})
    try:
        await db.save_turn(call_id, state["turn_count"], "user", speech_result)
    except Exception:
        pass

    try:
        agent_response = await state["llm"].generate_response(speech_result)
    except Exception as e:
        log.exception("LLM error")
        agent_response = "I'm sorry, could you please repeat that?"

    log.info("call %s | Agent: %s", call_sid, agent_response)
    state["turn_count"] += 1
    state["transcript"].append(f"Agent: {agent_response}")

    await manager.broadcast({"type": "transcript", "call_id": call_id,
                              "speaker": "agent", "text": agent_response,
                              "timestamp": datetime.now(timezone.utc).isoformat()})
    try:
        await db.save_turn(call_id, state["turn_count"], "agent", agent_response)
    except Exception:
        pass

    return build_gather_response(agent_response, base_url)


@app.post("/call-status")
async def call_status(request: Request):
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")
    call_status = form_data.get("CallStatus", "")
    log.info("call %s | Status=%s", call_sid, call_status)

    if call_status in ("completed", "failed", "busy", "no-answer", "canceled"):
        state = _calls.pop(call_sid, None)
        if state:
            duration = (datetime.now(timezone.utc) - state["start_time"]).seconds
            full_transcript = "\n".join(state["transcript"])
            extracted = {}
            try:
                lead_data = await extract_lead_info(full_transcript)
                extracted = lead_data.model_dump()
            except Exception as e:
                log.warning("extraction error: %s", e)
            # Fallback: caller's number from the Twilio webhook (From field)
            if not extracted.get("phone") and state.get("from_number"):
                extracted["phone"] = state["from_number"]
                log.info("using caller From number: %s", extracted["phone"])
            try:
                await db.end_call(
                    call_id=state["call_id"],
                    transcript=full_transcript,
                    extracted_data=extracted,
                    duration=duration,
                )
            except Exception as e:
                log.warning("db end_call skipped: %s", e)
            await manager.broadcast({"type": "call_ended", "call_id": state["call_id"],
                                      "duration": duration, "lead": extracted,
                                      "timestamp": datetime.now(timezone.utc).isoformat()})
            log.info("call ended. duration=%ds", duration)

            # ── Auto WhatsApp follow-up after the call ──────────────────────
            if os.getenv("WHATSAPP_AUTO_SEND", "true").lower() == "true":
                phone = extracted.get("phone")
                if phone:
                    try:
                        await send_followup_whatsapp(phone, full_transcript, extracted)
                    except Exception as e:
                        log.warning("auto whatsapp skipped: %s", e)
                else:
                    log.info("no lead phone extracted — skipping auto follow-up")
    return Response(content="", status_code=204)


@app.get("/api/numbers")
async def get_numbers(user: dict = Depends(get_current_user)):
    try:
        twilio = await db.get_phone_numbers("twilio")
        target = await db.get_phone_numbers("target")
        return {"twilio": twilio, "target": target}
    except Exception as e:
        log.warning("get_numbers error: %s", e)
        return {"twilio": [], "target": []}


@app.post("/api/numbers")
async def add_number(request: Request, user: dict = Depends(get_current_user)):
    from fastapi import HTTPException
    body = await request.json()
    type_ = body.get("type")
    label = body.get("label", "").strip()
    number = body.get("number", "").strip()
    if type_ not in ("twilio", "target") or not label or not number:
        raise HTTPException(status_code=400, detail="type, label, and number are required")
    id = await db.add_phone_number(type_, label, number)
    return {"id": id, "type": type_, "label": label, "number": number}


@app.delete("/api/numbers/{num_id}")
async def delete_number(num_id: str, user: dict = Depends(get_current_user)):
    await db.delete_phone_number(num_id)
    return {"status": "deleted"}


@app.post("/api/send-whatsapp")
async def api_send_whatsapp(request: Request, user: dict = Depends(get_current_user)):
    from fastapi import HTTPException
    body = await request.json()
    phone = (body.get("phone") or "").strip()
    message = (body.get("message") or "").strip()
    content_sid = (body.get("content_sid") or "").strip() or None
    if not phone:
        raise HTTPException(status_code=400, detail="phone is required")
    if not content_sid and not message:
        raise HTTPException(status_code=400, detail="message or content_sid is required")
    try:
        sid = send_whatsapp(phone, message=message, content_sid=content_sid)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"sid": sid, "status": "sent"}


@app.post("/api/generate-whatsapp")
async def api_generate_whatsapp(request: Request, user: dict = Depends(get_current_user)):
    from fastapi import HTTPException
    from services.llm_service import generate_followup_message
    body = await request.json()
    transcript = body.get("transcript") or ""
    lead = body.get("lead") or {}
    if not transcript.strip():
        raise HTTPException(status_code=400, detail="transcript is required")
    try:
        message = await generate_followup_message(transcript, lead)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": message}


@app.get("/api/users")
async def api_list_users(user: dict = Depends(get_current_user)):
    from services.auth_service import list_local_users
    try:
        db_users = await db.list_users()
    except Exception as e:
        log.warning("list_users error: %s", e)
        db_users = []
    return list_local_users() + db_users


@app.get("/api/settings")
async def api_get_settings(user: dict = Depends(get_current_user)):
    return {"default_user_id": await _default_user_id()}


@app.put("/api/settings")
async def api_set_settings(request: Request, user: dict = Depends(get_current_user)):
    from fastapi import HTTPException
    body = await request.json()
    value = (body.get("default_user_id") or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail="default_user_id is required")
    try:
        await db.set_setting("default_user_id", value)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"default_user_id": value}


@app.post("/outbound-call")
async def start_outbound_call(request: Request, user: dict = Depends(get_current_user)):
    from fastapi import HTTPException
    body = await request.json()
    phone = body.get("phone_number")
    base_url = body.get("base_url", "").rstrip("/")
    if not base_url:
        base_url = _get_base_url(request)
    from_number = body.get("from_number") or os.getenv("TWILIO_PHONE_NUMBER")
    user_id = body.get("user_id") or ""
    try:
        sid = make_outbound_call(phone, from_number, base_url, user_id=user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"call_sid": sid, "status": "initiated"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


# ── SPA static assets (React build) ─────────────────────────────────────────
if os.path.isdir(os.path.join(FRONTEND_DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")