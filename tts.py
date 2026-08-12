import edge_tts
import re


class EdgeTTS:
    def __init__(self, voice="en-IN-NeerjaNeural"):
        self.voice = voice

    async def synthesize(self, text: str) -> bytes:
        communicate = edge_tts.Communicate(text, self.voice)
        audio_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
        return audio_bytes

    async def stream_synthesis(self, text_stream):
        buffer = ""
        async for text_chunk in text_stream:
            buffer += text_chunk
            sentences = re.split(r'(?<=[.!?])\s+', buffer)
            for sentence in sentences[:-1]:
                if sentence.strip():
                    audio = await self.synthesize(sentence)
                    yield audio
            buffer = sentences[-1]
        if buffer.strip():
            audio = await self.synthesize(buffer)
            yield audio
