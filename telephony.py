from twilio.rest import Client
from dotenv import load_dotenv
import os

load_dotenv()

client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

call = client.calls.create(
    to="+919131405229",
    from_=os.getenv("TWILIO_PHONE_NUMBER"),
    url="https://webhooks.twilio.com/v1/Voice/Template/voice_speech_recognition"
)

print("Call SID:", call.sid)
print("Status:  ", call.status)
