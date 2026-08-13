import io
import re
import asyncio
import audioop
from gtts import gTTS
from pydub import AudioSegment


class EdgeTTS:
    def __init__(self, voice="en-IN-NeerjaNeural"):
        # voice param kept for API compatibility
        pass

    async def synthesize(self, text: str) -> bytes:
        # gTTS is blocking (network call) — run in thread
        return await asyncio.to_thread(self._synthesize_sync, text)

    def _synthesize_sync(self, text: str) -> bytes:
        # Step 1: gTTS -> MP3 bytes
        mp3_buffer = io.BytesIO()
        gTTS(text, lang="en", tld="co.in").write_to_fp(mp3_buffer)
        mp3_buffer.seek(0)

        # Step 2: MP3 -> PCM 8kHz mono 16-bit (Twilio requirement)
        audio = AudioSegment.from_mp3(mp3_buffer)
        audio = audio.set_frame_rate(8000).set_channels(1).set_sample_width(2)

        # Step 3: PCM -> mulaw (Twilio media stream format)
        return audioop.lin2ulaw(audio.raw_data, 2)

    async def stream_synthesis(self, text_stream):
        buffer = ""
        async for text_chunk in text_stream:
            buffer += text_chunk
            sentences = re.split(r'(?<=[.!?])\s+', buffer)
            for sentence in sentences[:-1]:
                if sentence.strip():
                    yield await self.synthesize(sentence)
            buffer = sentences[-1]
        if buffer.strip():
            yield await self.synthesize(buffer)
