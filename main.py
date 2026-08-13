from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Connect
from conversation import ConversationOrchestrator
from database import Database
import json
import base64
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="AI Calling Agent")
db = Database()  # safe — load_dotenv() already ran above


@app.get("/")
async def root():
    return {"status": "AI Calling Agent Running"}


@app.post("/incoming-call")
async def handle_incoming_call(request: Request):
    form_data = await request.form()
    call_sid = form_data.get("CallSid")
    call_id = await db.create_call(
        user_id=os.getenv("DEFAULT_USER_ID"),
        agent_id=os.getenv("DEFAULT_AGENT_ID"),
        twilio_sid=call_sid,
        direction="inbound",
    )
    response = VoiceResponse()
    response.say("Please wait while I connect you.", voice="alice")
    connect = Connect()
    stream = connect.stream(url=f"wss://{request.headers['host']}/media-stream")
    stream.parameter(name="call_id", value=call_id)
    response.append(connect)
    return Response(content=str(response), media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    await websocket.accept()
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
        print(f"Error: {e}")
    finally:
        if orchestrator:
            await orchestrator.cleanup()


@app.post("/outbound-call")
async def make_outbound_call(request: Request):
    from twilio.rest import Client
    body = await request.json()
    client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN"),
    )
    call = client.calls.create(
        to=body["phone_number"],
        from_=os.getenv("TWILIO_PHONE_NUMBER"),
        url=f"https://{request.headers['host']}/incoming-call",
    )
    return {"call_sid": call.sid, "status": "initiated"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
