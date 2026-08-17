from twilio.rest import Client
from dotenv import load_dotenv
import os
import sys

load_dotenv()

public_url = os.getenv("PUBLIC_URL", "").rstrip("/")
if not public_url:
    raise RuntimeError("PUBLIC_URL is not set in .env")

phone = sys.argv[1] if len(sys.argv) > 1 else "+919131405229"

client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

call = client.calls.create(
    to=phone,
    from_=os.getenv("TWILIO_PHONE_NUMBER"),
    url=f"{public_url}/incoming-call",
    status_callback=f"{public_url}/call-status",
    status_callback_event=["completed"],
)

print("Call SID:", call.sid)
print("Status:  ", call.status)
