import json
import os
import time
from twilio.rest import Client
from .logger import get_logger

log = get_logger("whatsapp")

_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+17372508034")


def _twilio_client() -> Client:
    return Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))


def send_whatsapp(to_phone: str, message: str = None, content_sid: str = None,
                  content_variables: dict = None) -> str:
    """Send a WhatsApp message via Twilio.

    - content_sid: pre-approved content template (required for cold/outbound
      messages — this sender is template-only).
    - content_variables: JSON variables for templates that have placeholders.
    - message: free-form text (only allowed within the 24h customer
      service session window).
    """
    kwargs = {
        "to": f"whatsapp:{to_phone}",
        "from_": _WHATSAPP_FROM,
    }
    if content_sid:
        kwargs["content_sid"] = content_sid
        if content_variables:
            kwargs["content_variables"] = json.dumps(content_variables)
    else:
        kwargs["body"] = message
    start = time.monotonic()
    try:
        msg = _twilio_client().messages.create(**kwargs)
    except Exception:
        log.exception("send failed to %s", to_phone)
        raise
    log.info("sent to %s in %.0fms (sid=%s)", to_phone, (time.monotonic() - start) * 1000, msg.sid)
    return msg.sid


async def send_followup_whatsapp(transcript: str, lead: dict, phone: str) -> str:
    """Auto follow-up after a call: uses approved template with LLM-filled
    variables if configured, otherwise generates a free-form message."""
    from .llm_service import generate_followup_message, generate_template_variables

    content_sid = (os.getenv("WHATSAPP_CONTENT_SID") or "").strip() or None
    if content_sid:
        try:
            variables = await generate_template_variables(transcript, lead)
            log.info("template variables: %s", variables)
        except Exception:
            log.exception("variable generation failed — sending template without variables")
            variables = None
        return send_whatsapp(phone, content_sid=content_sid, content_variables=variables)
    message = await generate_followup_message(transcript, lead)
    return send_whatsapp(phone, message=message)