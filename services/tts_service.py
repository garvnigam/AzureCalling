import os
import aiohttp
from .logger import get_logger

log = get_logger("tts")

SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "centralindia")
SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")
TTS_VOICE = os.getenv("AZURE_TTS_VOICE", "en-IN-NeerjaNeural")


def _escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
    )


async def synthesize_to_mulaw(text: str) -> bytes:
    """Convert text to mulaw 8kHz audio via Azure Speech TTS REST API."""
    if not text.strip() or not SPEECH_KEY:
        if not SPEECH_KEY:
            log.warning("AZURE_SPEECH_KEY not set — TTS skipped")
        return b""

    url = f"https://{SPEECH_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": SPEECH_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "raw-8khz-8bit-mono-mulaw",
        "User-Agent": "realtysiksha-voice-bot",
    }
    ssml = (
        f"<speak version='1.0' xml:lang='en-IN'>"
        f"<voice name='{TTS_VOICE}'>{_escape_xml(text)}</voice>"
        f"</speak>"
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=headers, data=ssml.encode(),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 200:
                    audio = await resp.read()
                    log.info("tts: %d chars → %d bytes mulaw", len(text), len(audio))
                    return audio
                body = await resp.text()
                log.warning("tts http %s: %s", resp.status, body[:200])
    except Exception as e:
        log.warning("tts request failed: %s", e)
    return b""
