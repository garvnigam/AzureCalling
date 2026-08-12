from stt import DeepgramSTT
from llm import LLMBrain
from tts import EdgeTTS
from extractor import extract_lead_info
from database import Database
import asyncio
import base64
import os
from datetime import datetime


class ConversationOrchestrator:
    def __init__(self, call_id, websocket, stream_sid):
        self.call_id = call_id
        self.websocket = websocket
        self.stream_sid = stream_sid
        self.db = Database()
        self.stt = DeepgramSTT(os.getenv("DEEPGRAM_API_KEY"))
        self.llm = LLMBrain()
        self.tts = EdgeTTS(voice="en-IN-NeerjaNeural")
        self.transcript_log = []
        self.turn_count = 0
        self.start_time = datetime.utcnow()
        self.is_speaking = False

    async def start(self):
        await self.stt.start_stream(on_transcript=self.on_user_speech)
        greeting = "Hello! This is Priya from ABC Real Estate. Am I speaking with the right person?"
        await self.speak(greeting)

    async def process_audio(self, audio_bytes):
        if not self.is_speaking:
            await self.stt.send_audio(audio_bytes)

    async def on_user_speech(self, text: str, is_final: bool):
        if not is_final or not text.strip():
            return
        print(f"User: {text}")
        self.turn_count += 1
        self.transcript_log.append(f"User: {text}")
        await self.db.save_turn(self.call_id, self.turn_count, "user", text)
        response = await self.llm.generate_response(text)
        await self.speak(response)

    async def speak(self, text: str):
        print(f"Agent: {text}")
        self.is_speaking = True
        self.turn_count += 1
        self.transcript_log.append(f"Agent: {text}")
        await self.db.save_turn(self.call_id, self.turn_count, "agent", text)
        try:
            audio_bytes = await self.tts.synthesize(text)
            chunk_size = 320
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i:i + chunk_size]
                payload = base64.b64encode(chunk).decode()
                await self.websocket.send_json({
                    "event": "media",
                    "streamSid": self.stream_sid,
                    "media": {"payload": payload},
                })
                await asyncio.sleep(0.02)
        finally:
            self.is_speaking = False

    async def end_call(self):
        duration = (datetime.utcnow() - self.start_time).seconds
        full_transcript = "\n".join(self.transcript_log)
        try:
            lead_data = await extract_lead_info(full_transcript)
            extracted = lead_data.model_dump()
        except Exception as e:
            print(f"Extraction error: {e}")
            extracted = {}
        await self.db.end_call(
            call_id=self.call_id,
            transcript=full_transcript,
            extracted_data=extracted,
            duration=duration,
        )
        print(f"Call ended. Duration: {duration}s")

    async def cleanup(self):
        await self.stt.stop()
