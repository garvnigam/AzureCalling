import os
import io
import wave
import audioop
import aiohttp
from .logger import get_logger

log = get_logger("stt")

SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "centralindia")
SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")


def mulaw_to_wav(mulaw_bytes: bytes) -> bytes:
    pcm = audioop.ulaw2lin(mulaw_bytes, 2)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(pcm)
    return buf.getvalue()


def chunk_energy(mulaw_bytes: bytes) -> int:
    if not mulaw_bytes:
        return 0
    try:
        pcm = audioop.ulaw2lin(mulaw_bytes, 2)
        return audioop.rms(pcm, 2)
    except Exception:
        return 0


async def transcribe_audio(mulaw_bytes: bytes) -> str:
    if not mulaw_bytes or len(mulaw_bytes) < 320:
        return ""
    if not SPEECH_KEY:
        log.warning("AZURE_SPEECH_KEY not set — STT skipped")
        return ""

    wav_bytes = mulaw_to_wav(mulaw_bytes)
    url = (
        f"https://{SPEECH_REGION}.stt.speech.microsoft.com"
        f"/speech/recognition/conversation/cognitiveservices/v1"
        f"?language=en-IN&format=simple"
    )
    headers = {
        "Ocp-Apim-Subscription-Key": SPEECH_KEY,
        "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=8000",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url, headers=headers, data=wav_bytes,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    status = data.get("RecognitionStatus", "")
                    if status == "Success":
                        text = data.get("DisplayText", "").strip()
                        log.info("stt: %s", text)
                        return text
                    log.info("stt non-success status: %s", status)
                else:
                    body = await resp.text()
                    log.warning("stt http %s: %s", resp.status, body[:200])
    except Exception as e:
        log.warning("stt request failed: %s", e)
    return ""
