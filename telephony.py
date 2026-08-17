import os
import sys
from dotenv import load_dotenv
from services.call_service import make_outbound_call

load_dotenv()

public_url = os.getenv("PUBLIC_URL", "").rstrip("/")
if not public_url:
    raise RuntimeError("PUBLIC_URL is not set in .env")

phone = sys.argv[1] if len(sys.argv) > 1 else "+919131405229"

sid = make_outbound_call(
    to=phone,
    from_number=os.getenv("TWILIO_PHONE_NUMBER"),
    base_url=public_url,
)

print("Call SID:", sid)
print("Status:  initiated")