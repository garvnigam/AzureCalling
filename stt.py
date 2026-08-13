from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions


class DeepgramSTT:
    def __init__(self, api_key: str):
        self.client = DeepgramClient(api_key)
        self.connection = None
        self.transcript_callback = None

    async def start_stream(self, on_transcript):
        self.transcript_callback = on_transcript
        self.connection = self.client.listen.asynclive.v("1")

        async def on_message(self_, result, **kwargs):
            sentence = result.channel.alternatives[0].transcript
            if not sentence:
                return
            await self.transcript_callback(sentence, is_final=result.is_final)

        self.connection.on(LiveTranscriptionEvents.Transcript, on_message)
        options = LiveOptions(
            model="nova-2",
            language="en-IN",
            smart_format=True,
            interim_results=True,
            utterance_end_ms=1000,
            vad_events=True,
            encoding="mulaw",
            sample_rate=8000,
            channels=1,
        )
        await self.connection.start(options)

    async def send_audio(self, audio_bytes: bytes):
        await self.connection.send(audio_bytes)

    async def stop(self):
        if self.connection:
            await self.connection.finish()
