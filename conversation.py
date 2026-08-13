from stt import DeepgramSTT
from llm import LLMBrain
from tts import EdgeTTS
from extractor import extract_lead_info
from database import Database
import asyncio
import base64
import os
from datetime import datetime, timezone


class ConversationOrchestrator:
    def __init__(self, call_id, websocket, stream_sid, broadcast=None):
        self.call_id = call_id
        self.websocket = websocket
        self.stream_sid = stream_sid
        self.broadcast = broadcast
        self.db = Database()
        self.stt = DeepgramSTT(os.getenv("DEEPGRAM_API_KEY"))
        self.llm = LLMBrain()
        self.tts = EdgeTTS(voice="en-IN-NeerjaNeural")
        self.transcript_log = []
        self.turn_count = 0
        self.start_time = datetime.now(timezone.utc)
        self.is_speaking = False

    async def _emit(self, event: dict):
        if self.broadcast:
            await self.broadcast(event)

    async def start(self):
        await self._emit({"type": "call_started", "call_id": self.call_id,
                          "timestamp": datetime.now(timezone.utc).isoformat()})
        await self.stt.start_stream(on_transcript=self.on_user_speech)
        agent = os.getenv("AGENT_NAME", "Shyam Dhar Dubey")
        company = os.getenv("COMPANY_NAME", "Elite Realty")
        greeting = (
            f"Hello! Am I speaking with the right person? "
            f"Hi, I'm {agent} calling from {company}. "
            f"We are a real estate consultancy specializing in properties in Greater Noida. "
            f"Is this a good time to talk?"
        )
        await self.speak(greeting)

    async def process_audio(self, audio_bytes):
        if not self.is_speaking:
            await self.stt.send_audio(audio_bytes)

    async def _save_turn_safe(self, speaker: str, text: str):
        try:
            await self.db.save_turn(self.call_id, self.turn_count, speaker, text)
        except Exception as e:
            print(f"[db] save_turn skipped: {e}")

    async def on_user_speech(self, text: str, is_final: bool):
        if not is_final or not text.strip():
            return
        print(f"User: {text}")
        self.turn_count += 1
        self.transcript_log.append(f"User: {text}")
        await self._save_turn_safe("user", text)
        await self._emit({"type": "transcript", "call_id": self.call_id,
                          "speaker": "user", "text": text,
                          "timestamp": datetime.now(timezone.utc).isoformat()})
        response = await self.llm.generate_response(text)
        await self.speak(response)

    async def speak(self, text: str):
        print(f"Agent: {text}")
        self.is_speaking = True
        self.turn_count += 1
        self.transcript_log.append(f"Agent: {text}")
        await self._save_turn_safe("agent", text)
        await self._emit({"type": "transcript", "call_id": self.call_id,
                          "speaker": "agent", "text": text,
                          "timestamp": datetime.now(timezone.utc).isoformat()})
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
        duration = (datetime.now(timezone.utc) - self.start_time).seconds
        full_transcript = "\n".join(self.transcript_log)
        extracted = {}
        try:
            lead_data = await extract_lead_info(full_transcript)
            extracted = lead_data.model_dump()
        except Exception as e:
            print(f"Extraction error: {e}")
        try:
            await self.db.end_call(
                call_id=self.call_id,
                transcript=full_transcript,
                extracted_data=extracted,
                duration=duration,
            )
        except Exception as e:
            print(f"[db] end_call skipped: {e}")
        await self._emit({"type": "call_ended", "call_id": self.call_id,
                          "duration": duration, "lead": extracted,
                          "timestamp": datetime.now(timezone.utc).isoformat()})
        print(f"Call ended. Duration: {duration}s")

    async def cleanup(self):
        await self.stt.stop()
