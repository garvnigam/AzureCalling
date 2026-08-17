from supabase import create_client, Client
import os
from datetime import datetime
from typing import Optional
import uuid


class Database:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        self.client: Client = create_client(url, key)

    # ── Users ───────────────────────────────────────────────────────────────

    async def create_user(self, email: str, name: str, password_hash: str) -> str:
        user_id = str(uuid.uuid4())
        self.client.table("users").insert({
            "id": user_id, "email": email.lower(), "name": name,
            "password_hash": password_hash,
        }).execute()
        return user_id

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        result = self.client.table("users").select("*").eq(
            "email", email.lower()).maybe_single().execute()
        if result is None:
            return None
        return result.data

    async def list_users(self) -> list[dict]:
        result = self.client.table("users").select("id,email,name").order("email").execute()
        return result.data or []

    # ── Settings ────────────────────────────────────────────────────────────

    async def get_setting(self, key: str) -> Optional[str]:
        result = self.client.table("settings").select("value").eq("key", key).maybe_single().execute()
        if result is None or result.data is None:
            return None
        return result.data.get("value")

    async def set_setting(self, key: str, value: str):
        self.client.table("settings").upsert({
            "key": key, "value": value,
        }, on_conflict="key").execute()

    async def create_call(self, user_id: str, agent_id: str,
                          twilio_sid: str, direction: str) -> str:
        call_id = str(uuid.uuid4())
        data = {
            "id": call_id,
            "user_id": user_id,
            "agent_id": agent_id,
            "twilio_call_sid": twilio_sid,
            "direction": direction,
            "status": "initiated",
            "started_at": datetime.utcnow().isoformat(),
        }
        self.client.table("calls").insert(data).execute()
        return call_id

    async def save_turn(self, call_id: str, turn_num: int,
                        speaker: str, text: str):
        self.client.table("conversation_turns").insert({
            "call_id": call_id,
            "turn_number": turn_num,
            "speaker": speaker,
            "text": text,
        }).execute()

    async def end_call(self, call_id: str, transcript: str,
                       extracted_data: dict, duration: int):
        self.client.table("calls").update({
            "status": "completed",
            "transcript": transcript,
            "extracted_data": extracted_data,
            "lead_score": extracted_data.get("lead_score", 0),
            "duration_seconds": duration,
            "ended_at": datetime.utcnow().isoformat(),
            # individual lead columns
            "lead_name": extracted_data.get("name"),
            "lead_phone": extracted_data.get("phone"),
            "lead_email": extracted_data.get("email"),
            "budget_min": extracted_data.get("budget_min"),
            "budget_max": extracted_data.get("budget_max"),
            "locations": extracted_data.get("locations") or [],
            "bhk": extracted_data.get("bhk"),
            "property_type": extracted_data.get("property_type"),
            "timeline": extracted_data.get("timeline"),
            "purpose": extracted_data.get("purpose"),
            "interested": extracted_data.get("interested", True),
            "call_summary": extracted_data.get("call_summary"),
            "next_action": extracted_data.get("next_action"),
        }).eq("id", call_id).execute()

    async def get_agent(self, agent_id: str):
        result = self.client.table("agents").select("*").eq(
            "id", agent_id).single().execute()
        return result.data

    async def get_user_calls(self, user_id: str, limit: int = 50):
        result = self.client.table("calls").select("*").eq(
            "user_id", user_id).order(
            "created_at", desc=True).limit(limit).execute()
        return result.data

    async def get_phone_numbers(self, type: str):
        result = self.client.table("phone_numbers").select("*").eq(
            "type", type).order("created_at").execute()
        return result.data or []

    async def add_phone_number(self, type: str, label: str, number: str) -> str:
        id = str(uuid.uuid4())
        self.client.table("phone_numbers").insert({
            "id": id, "type": type, "label": label, "number": number,
        }).execute()
        return id

    async def delete_phone_number(self, id: str):
        self.client.table("phone_numbers").delete().eq("id", id).execute()
