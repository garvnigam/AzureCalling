import os
import time
from fastapi.responses import Response
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from .logger import get_logger

log = get_logger("call")


def get_twilio_client() -> Client:
    return Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))


def build_gather_response(text: str, base_url: str) -> Response:
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
    log.info("twiml: %s", twiml[:300])
    return Response(content=twiml, media_type="application/xml")


def build_error_hangup() -> Response:
    response = VoiceResponse()
    response.say("Sorry, something went wrong. Goodbye.", voice="Polly.Aditi")
    response.hangup()
    return Response(content=str(response), media_type="application/xml")


def make_outbound_call(to: str, from_number: str, base_url: str, user_id: str = "") -> str:
    client = get_twilio_client()
    url = f"{base_url}/incoming-call"
    if user_id:
        url += f"?user_id={user_id}"
    start = time.monotonic()
    call = client.calls.create(
        to=to,
        from_=from_number,
        url=url,
        status_callback=f"{base_url}/call-status",
        status_callback_event=["completed"],
    )
    log.info("outbound call to %s (sid=%s) in %.0fms", to, call.sid, (time.monotonic() - start) * 1000)
    return call.sid