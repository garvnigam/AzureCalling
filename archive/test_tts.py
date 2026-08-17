from gtts import gTTS

print("Synthesizing audio...")
tts = gTTS("Hello! This is Priya from ABC Real Estate. How can I help you today?", lang="en", tld="co.in")
tts.save("test_output.mp3")
print("Done. Saved to test_output.mp3")
