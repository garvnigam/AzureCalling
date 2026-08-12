import os
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import Response
from twilio.twiml.voice_response import VoiceResponse, Connect
from twilio.rest import Client
app = FastAPI()


@app.post("/incoming-call")
async def handle_incoming_call(request: Request):
    # Twilio hits this URL when a call comes in
    response = VoiceResponse()
    response.say("Hello! Connecting you to our AI assistant.")
    connect = Connect()
    connect.stream(url=os.environ["WEBSOCKET_URL"])
    response.append(connect)
    return Response(content=str(response), media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    # Real-time audio streaming endpoint
    await websocket.accept()
    try:
        while True:
            # Receive audio from Twilio
            data = await websocket.receive_json()
            if data["event"] == "media":
                # Base64 encoded audio chunk -> STT -> LLM -> TTS -> back to user
                audio_payload = data["media"]["payload"]
                await process_audio(audio_payload, websocket)
            elif data["event"] == "stop":
                break
    except Exception as e:
        print(f"Error: {e}")
client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])


def make_outbound_call(to_number: str):
    call = client.calls.create(
        to=to_number,
        from_=os.environ["TWILIO_PHONE_NUMBER"],
        url=os.environ["INCOMING_CALL_URL"],
    )
    return call.sid