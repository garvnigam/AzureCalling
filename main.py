from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from fastapi.responses import Response, HTMLResponse, FileResponse
from twilio.twiml.voice_response import VoiceResponse, Connect
from conversation import ConversationOrchestrator
from database import Database
import json
import base64
import os
import traceback
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="AI Calling Agent")
db = Database()  # safe — load_dotenv() already ran above


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
    public_url = os.getenv("PUBLIC_URL", "").rstrip("/")
    if public_url:
        host = public_url.replace("https://", "").replace("http://", "")
    else:
        host = request.headers.get("x-forwarded-host") or request.headers["host"]
    ws_url = f"wss://{host}/media-stream"
    print(f"[incoming-call] CallSid={call_sid} | ws_url={ws_url}")
    response = VoiceResponse()
    connect = Connect()
    stream = connect.stream(url=ws_url)
    stream.parameter(name="call_id", value=call_id)
    response.append(connect)
    twiml = str(response)
    print(f"[incoming-call] TwiML returned:\n{twiml}")
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    print(f"[media-stream] WebSocket connecting from {websocket.client}")
    await websocket.accept()
    print("[media-stream] WebSocket accepted")
    orchestrator = None
    try:
        async for message in websocket.iter_text():
            data = json.loads(message)
            event = data.get("event")
            if event == "start":
                stream_sid = data["start"]["streamSid"]
                call_id = data["start"].get("customParameters", {}).get("call_id")
                orchestrator = ConversationOrchestrator(
                    call_id=call_id,
                    websocket=websocket,
                    stream_sid=stream_sid,
                    broadcast=manager.broadcast,
                )
                await orchestrator.start()
            elif event == "media":
                audio_bytes = base64.b64decode(data["media"]["payload"])
                if orchestrator:
                    await orchestrator.process_audio(audio_bytes)
            elif event == "stop":
                if orchestrator:
                    await orchestrator.end_call()
                break
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"[media-stream] Error: {e}")
        traceback.print_exc()
    finally:
        if orchestrator:
            await orchestrator.cleanup()


@app.post("/outbound-call")
async def make_outbound_call(request: Request):
    from twilio.rest import Client
    from fastapi import HTTPException
    body = await request.json()
    phone = body.get("phone_number")
    base_url = body.get("base_url", "").rstrip("/")
    if not base_url:
        host = request.headers.get("x-forwarded-host") or request.headers["host"]
        proto = request.headers.get("x-forwarded-proto", "https")
        base_url = f"{proto}://{host}"
    client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN"),
    )
    try:
        call = client.calls.create(
            to=phone,
            from_=os.getenv("TWILIO_PHONE_NUMBER"),
            url=f"{base_url}/incoming-call",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"call_sid": call.sid, "status": "initiated"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
