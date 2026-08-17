from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from fastapi.responses import Response, HTMLResponse, FileResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from llm import LLMBrain
from extractor import extract_lead_info
from database import Database
import json
import os
import traceback
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="AI Calling Agent")
db = Database()

# In-memory conversation state keyed by CallSid
_calls: dict[str, dict] = {}


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


def _build_gather_response(text: str, base_url: str) -> Response:
    """Say text, then listen for speech via <Gather>."""
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action=f"{base_url}/handle-speech",
        method="POST",
        speech_timeout="auto",
        language="en-IN",
    )
    gather.say(text, voice="Polly.Aditi", language="en-IN")
    response.append(gather)
    # If caller stays silent, re-prompt
    response.say("Are you still there?", voice="Polly.Aditi", language="en-IN")
    response.redirect(f"{base_url}/incoming-call", method="POST")
    twiml = str(response)
    print(f"[twiml] {twiml[:300]}")
    return Response(content=twiml, media_type="application/xml")


@app.get("/")
async def root():
    return {"status": "AI Calling Agent Running"}


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    return FileResponse("dashboard.html")


@app.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/calls")
async def get_calls():
    try:
        user_id = os.getenv("DEFAULT_USER_ID", "default")
        data = await db.get_user_calls(user_id, limit=50)
        return data or []
    except Exception as e:
        print(f"get_calls error: {e}")
        return []


@app.post("/incoming-call")
async def handle_incoming_call(request: Request):
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")
    base_url = _get_base_url(request)

    # Only initialize on first hit (not on silence-redirect)
    if call_sid not in _calls:
        try:
            call_id = await db.create_call(
                user_id=os.getenv("DEFAULT_USER_ID", "default"),
                agent_id=os.getenv("DEFAULT_AGENT_ID", "default"),
                twilio_sid=call_sid,
                direction="inbound",
            )
        except Exception as e:
            print(f"DB create_call error (continuing): {e}")
            import uuid
            call_id = str(uuid.uuid4())

        llm = LLMBrain()
        _calls[call_sid] = {
            "call_id": call_id,
            "llm": llm,
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
        print(f"[incoming-call] CallSid={call_sid} — greeting")
        return _build_gather_response(greeting, base_url)

    # Silence re-prompt
    print(f"[incoming-call] CallSid={call_sid} — silence re-prompt")
    return _build_gather_response("Hello? Are you there?", base_url)


@app.post("/handle-speech")
async def handle_speech(request: Request):
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")
    speech_result = form_data.get("SpeechResult", "")
    base_url = _get_base_url(request)

    print(f"[speech] CallSid={call_sid} | User: {speech_result}")

    state = _calls.get(call_sid)
    if not state:
        response = VoiceResponse()
        response.say("Sorry, something went wrong. Goodbye.", voice="Polly.Aditi")
        response.hangup()
        return Response(content=str(response), media_type="application/xml")

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
        print(f"[llm] Error: {e}")
        agent_response = "I'm sorry, could you please repeat that?"

    print(f"[speech] Agent: {agent_response}")
    state["turn_count"] += 1
    state["transcript"].append(f"Agent: {agent_response}")

    await manager.broadcast({"type": "transcript", "call_id": call_id,
                              "speaker": "agent", "text": agent_response,
                              "timestamp": datetime.now(timezone.utc).isoformat()})
    try:
        await db.save_turn(call_id, state["turn_count"], "agent", agent_response)
    except Exception:
        pass

    return _build_gather_response(agent_response, base_url)


@app.post("/call-status")
async def call_status(request: Request):
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")
    call_status = form_data.get("CallStatus", "")
    print(f"[status] CallSid={call_sid} | Status={call_status}")

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
                print(f"Extraction error: {e}")
            try:
                await db.end_call(
                    call_id=state["call_id"],
                    transcript=full_transcript,
                    extracted_data=extracted,
                    duration=duration,
                )
            except Exception as e:
                print(f"[db] end_call skipped: {e}")
            await manager.broadcast({"type": "call_ended", "call_id": state["call_id"],
                                      "duration": duration, "lead": extracted,
                                      "timestamp": datetime.now(timezone.utc).isoformat()})
            print(f"Call ended. Duration: {duration}s")
    return Response(content="", status_code=204)


@app.get("/api/numbers")
async def get_numbers():
    try:
        twilio = await db.get_phone_numbers("twilio")
        target = await db.get_phone_numbers("target")
        return {"twilio": twilio, "target": target}
    except Exception as e:
        print(f"get_numbers error: {e}")
        return {"twilio": [], "target": []}


@app.post("/api/numbers")
async def add_number(request: Request):
    body = await request.json()
    type_ = body.get("type")
    label = body.get("label", "").strip()
    number = body.get("number", "").strip()
    if type_ not in ("twilio", "target") or not label or not number:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="type, label, and number are required")
    id = await db.add_phone_number(type_, label, number)
    return {"id": id, "type": type_, "label": label, "number": number}


@app.delete("/api/numbers/{num_id}")
async def delete_number(num_id: str):
    await db.delete_phone_number(num_id)
    return {"status": "deleted"}


@app.post("/outbound-call")
async def make_outbound_call(request: Request):
    from twilio.rest import Client
    from fastapi import HTTPException
    body = await request.json()
    phone = body.get("phone_number")
    base_url = body.get("base_url", "").rstrip("/")
    if not base_url:
        base_url = _get_base_url(request)
    client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN"),
    )
    from_number = body.get("from_number") or os.getenv("TWILIO_PHONE_NUMBER")
    try:
        call = client.calls.create(
            to=phone,
            from_=from_number,
            url=f"{base_url}/incoming-call",
            status_callback=f"{base_url}/call-status",
            status_callback_event=["completed"],
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"call_sid": call.sid, "status": "initiated"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
