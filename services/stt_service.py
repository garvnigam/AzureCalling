import os
import io
import wave
import struct
import math
import aiohttp
from .logger import get_logger

log = get_logger("stt")

SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "centralindia")
SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "")

# mulaw decode table (ITU-T G.711)
_MULAW_DECODE = None

def _build_mulaw_table():
    global _MULAW_DECODE
    if _MULAW_DECODE is not None:
        return
    table = []
    for u in range(256):
        u = ~u & 0xFF
        sign = u & 0x80
        exp = (u >> 4) & 0x07
        mantissa = u & 0x0F
        linear = (mantissa << 1 | 0x21) << exp
        linear -= 33
        table.append(-linear if sign else linear)
    _MULAW_DECODE = table

def _ulaw2lin(mulaw_bytes: bytes) -> bytes:
    _build_mulaw_table()
    samples = [_MULAW_DECODE[b] for b in mulaw_bytes]
    return struct.pack(f"<{len(samples)}h", *samples)

def _rms(pcm_bytes: bytes) -> int:
    if len(pcm_bytes) < 2:
        return 0
    samples = struct.unpack(f"<{len(pcm_bytes) // 2}h", pcm_bytes[:len(pcm_bytes) & ~1])
    mean_sq = sum(s * s for s in samples) / len(samples)
    return int(math.sqrt(mean_sq))


def mulaw_to_wav(mulaw_bytes: bytes) -> bytes:
    pcm = _ulaw2lin(mulaw_bytes)
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
        pcm = _ulaw2lin(mulaw_bytes)
        return _rms(pcm)
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
