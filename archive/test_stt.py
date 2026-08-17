import asyncio
import audioop
import os
import numpy as np
import sounddevice as sd
from dotenv import load_dotenv

load_dotenv()

from stt import DeepgramSTT

RECORD_SECONDS = 5
SAMPLE_RATE = 8000

transcripts = []

async def on_transcript(text: str, is_final: bool):
    label = "FINAL" if is_final else "interim"
    print(f"  [{label}] {text}")
    if is_final:
        transcripts.append(text)

async def main():
    print(f"Recording for {RECORD_SECONDS} seconds... Speak now!")
    recording = sd.rec(
        int(RECORD_SECONDS * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16"
    )
    sd.wait()
    print("Recording done.\n")

    # Convert PCM int16 -> mulaw
    pcm_bytes = recording.tobytes()
    mulaw_bytes = audioop.lin2ulaw(pcm_bytes, 2)

    print("Starting Deepgram stream...")
    stt = DeepgramSTT(os.getenv("DEEPGRAM_API_KEY"))
    await stt.start_stream(on_transcript=on_transcript)

    print("Sending audio...\n")
    chunk_size = 320
    for i in range(0, len(mulaw_bytes), chunk_size):
        await stt.send_audio(mulaw_bytes[i:i + chunk_size])
        await asyncio.sleep(0.02)

    await asyncio.sleep(3)
    await stt.stop()

    print("\n--- Result ---")
    if transcripts:
        print("Transcribed:", " ".join(transcripts))
    else:
        print("No transcript received.")

asyncio.run(main())
