import json
import os
import time
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field
from groq import AsyncGroq
from .logger import get_logger

log = get_logger("llm")

_AGENT_NAME = os.getenv("AGENT_NAME", "Shyam Dhar Dubey")
_COMPANY = os.getenv("COMPANY_NAME", "GSAssociates")

SYSTEM_PROMPT = f"""
You are {_AGENT_NAME}, a friendly and experienced real estate consultant at {_COMPANY}. You specialize in residential properties in Greater Noida, Uttar Pradesh. You sound like a real person on the phone — warm, natural, and conversational.

## SITUATION
You are calling a potential property buyer. This is a warm outbound call. Your tone should feel like a helpful friend in the real estate business, not a telemarketer reading a script.

## YOUR APPROACH
You have a natural conversation while gathering the information your team needs. NEVER make it feel like a form or survey. Weave your questions into genuine discussion about their property needs, their life situation, and what matters to them.

## HOW TO GATHER INFORMATION NATURALLY
You need these details by the end of the call, but collect them through conversation, not interrogation:

1. **Name** — Start warmly: "May I know your good name, sir/ma'am?" or pick it up naturally if they introduce themselves
2. **Budget** — Don't ask directly. Say something like: "Just so I can show you the right options, are you comfortable in the 50-80 lakh range, or are you looking at something premium?" React to their answer with market insight.
3. **Location preference** — Bring it up with context: "Greater Noida has some fantastic sectors now — Sector 150 is very popular for the greenery, Yamuna Expressway side is great for investment. Do you have any area in mind, or should I suggest based on your needs?"
4. **BHK** — Connect it to their life: "Is it just for you and your family? A 2 BHK works well for a small family, but if you need extra space for parents or a home office, 3 BHK gives that comfort."
5. **Timeline** — Frame it as helping them: "Are you looking to move in soon, or is this more of a planned investment for the next couple of years? I ask because ready-to-move and under-construction have very different pricing."
6. **Purpose** — Make it natural: "And is this mainly for you to live in, or are you also considering it as an investment? Many of our clients from Delhi are buying here for both."

If someone gives a vague answer, don't repeat the question robotically. Share a relevant insight and let them open up: "I understand, many people are still exploring. Let me tell you what's trending right now..."

## GREATER NOIDA EXPERTISE
Areas you know well (share this knowledge naturally in conversation):
- Sector 150 — premium sports city, green belt, metro nearby. "Bahut demand hai yahan, especially among IT professionals."
- Tech Zone IV / Knowledge Park — IT corridor, great for investment returns
- Gaur City (Sector 4/16) — affordable, ready-to-move, near Ghaziabad border
- Yamuna Expressway — Jewar Airport corridor, "yeh toh sone ka area hai for long-term investment"
- Sector 1, 2, 3 — established, schools and hospitals walking distance

Price ranges (share as casual knowledge, not a price list):
- 2 BHK: ₹40L – ₹90L depending on location and builder
- 3 BHK: ₹70L – ₹1.5 Cr
- Ready-to-move is 10-15% more than under-construction

## CONVERSATION STYLE
- Talk like a real person, not a chatbot. Use natural fillers: "So...", "Actually...", "You know what..."
- Mix Hindi naturally: "bilkul sir", "haan ji", "acha", "zaroor", "dekhiye", "shukriya"
- Share mini-stories: "Just last week, one of my clients from Dwarka visited Sector 150 and was amazed by the infrastructure"
- React genuinely to what they say — show you're listening
- If they mention kids, talk about schools nearby. If they mention commute, talk about metro connectivity.
- Keep responses to 2-3 short sentences maximum — this is a phone call, not an email

## CONVERSATION FLOW
- Start with a warm greeting and check if it's a good time
- Have a genuine back-and-forth conversation about their property needs
- Naturally collect name, budget, location, BHK, timeline, and purpose through the discussion
- Once you understand their needs, recommend 1-2 specific options with enthusiasm
- Close by suggesting a weekend site visit — make it easy: "Agar aap Saturday ko free hain, I can arrange a quick visit. No pressure, just see the place and decide."

## STOP CONDITIONS — end gracefully if:
- Person says not interested — "No problem at all, sir. If anything changes in future, please feel free to call me. Have a great day!"
- Person asks to call back — "Bilkul, when would be convenient? I'll call you then."
- Person is rude — stay polite, wrap up quickly

## NEVER DO
- Never sound like you're reading from a script or filling a form
- Never output instructions, notes, or stage directions to yourself — speak only to the customer
- Never wrap your reply in parentheses, quotes, or brackets. Your output is spoken aloud — it must be ONLY the words you say
- Never ask two questions in one response
- Never quote exact per sq ft prices — "hamare sales team se detailed price sheet mil jayegi"
- Never promise possession dates — "as per the developer's timeline"
- Never badmouth any competitor or location
- Never be pushy — you're a consultant, not a salesman
"""


class LLMBrain:
    """Conversational agent with call-turn memory."""

    def __init__(self):
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    async def generate_response(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        if len(self.messages) > 20:
            self.messages = [self.messages[0]] + self.messages[-10:]
        start = time.monotonic()
        try:
            response = await self.client.chat.completions.create(
                model=self.model, messages=self.messages,
                temperature=0.7, max_tokens=250, top_p=0.9,
            )
        except Exception:
            log.exception("chat completion failed")
            raise
        assistant_message = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": assistant_message})
        log.info("chat reply in %.0fms", (time.monotonic() - start) * 1000)
        return assistant_message


# ── Lead extraction ─────────────────────────────────────────────────────────

class Timeline(str, Enum):
    IMMEDIATE = "immediate"
    ONE_MONTH = "1_month"
    THREE_MONTHS = "3_months"
    SIX_MONTHS = "6_months"
    LONGER = "longer"
    UNKNOWN = "unknown"


class Purpose(str, Enum):
    OWN_USE = "own_use"
    INVESTMENT = "investment"
    RENTAL = "rental"
    UNKNOWN = "unknown"


class RealEstateLead(BaseModel):
    name: Optional[str] = Field(None, description="Customer's name")
    phone: Optional[str] = Field(None, description="Contact number")
    email: Optional[str] = None
    budget_min: Optional[int] = Field(None, description="Minimum budget in INR")
    budget_max: Optional[int] = Field(None, description="Maximum budget in INR")
    locations: List[str] = Field(default_factory=list, description="Preferred areas")
    bhk: Optional[int] = Field(None, description="Bedrooms required")
    property_type: Optional[str] = None
    timeline: Timeline = Timeline.UNKNOWN
    purpose: Purpose = Purpose.UNKNOWN
    interested: bool = True
    call_summary: str = Field("", description="2-line summary")
    next_action: str = Field("", description="Follow-up recommendation")
    lead_score: int = Field(0, ge=0, le=100, description="Quality score 0-100")


async def extract_lead_info(transcript: str) -> RealEstateLead:
    client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    extraction_prompt = f"""
Analyze this real estate call transcript and extract information in JSON format.

TRANSCRIPT:
{transcript}

Extract these fields (use null if not mentioned):
- name: Customer name
- phone: Phone number
- budget_min: Minimum budget in INR (convert lakhs/crores to numbers)
- budget_max: Maximum budget in INR
- locations: List of preferred areas
- bhk: Number of bedrooms
- timeline: One of [immediate, 1_month, 3_months, 6_months, longer, unknown]
- purpose: One of [own_use, investment, rental, unknown]
- interested: true/false
- call_summary: 2-sentence summary
- next_action: Recommendation for sales team

Return ONLY valid JSON, no explanation.
"""
    start = time.monotonic()
    try:
        response = await client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
    except Exception:
        log.exception("lead extraction failed")
        raise
    data = json.loads(response.choices[0].message.content)
    # Coerce nulls/None to safe defaults (model sometimes returns null)
    if data.get("locations") is None:
        data["locations"] = []
    if data.get("timeline") is None:
        data["timeline"] = "unknown"
    if data.get("purpose") is None:
        data["purpose"] = "unknown"
    # Coerce list fields to single values
    if isinstance(data.get("bhk"), list):
        data["bhk"] = data["bhk"][0] if data["bhk"] else None
    if isinstance(data.get("locations"), str):
        data["locations"] = [data["locations"]]
    lead = RealEstateLead(**data)
    lead.lead_score = calculate_lead_score(lead)
    log.info("extracted lead in %.0fms (score=%d)", (time.monotonic() - start) * 1000, lead.lead_score)
    return lead


def calculate_lead_score(lead: RealEstateLead) -> int:
    score = 0
    if lead.budget_min and lead.budget_max:
        score += 30
    elif lead.budget_min or lead.budget_max:
        score += 15
    timeline_scores = {
        Timeline.IMMEDIATE: 25,
        Timeline.ONE_MONTH: 20,
        Timeline.THREE_MONTHS: 15,
        Timeline.SIX_MONTHS: 10,
        Timeline.LONGER: 5,
        Timeline.UNKNOWN: 0,
    }
    score += timeline_scores.get(lead.timeline, 0)
    if len(lead.locations) >= 1:
        score += 20
    if lead.bhk:
        score += 15
    if lead.interested:
        score += 10
    return min(score, 100)


# ── WhatsApp message generation ─────────────────────────────────────────────

_FOLLOWUP_PROMPT = """
You are an assistant that writes warm, natural WhatsApp follow-up messages for a
real estate consultant in Greater Noida after a sales call.

Rules:
- Max 3-4 short sentences, friendly and professional, no emojis.
- Reference what the customer discussed (property type, location, budget,
  timeline) naturally — this is a person-to-person follow-up, not a template.
- End with a soft call to action (e.g. a weekend site visit) without pressure.
- Simple English, with a touch of Hindi only if it feels natural (e.g. "ji", "bilkul").
- Return ONLY the message text, no quotes, no placeholders.
"""


async def generate_followup_message(transcript: str, lead: dict) -> str:
    client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    context = {
        "transcript": (transcript or "")[:4000],
        "name": lead.get("name"),
        "locations": ", ".join(lead.get("locations") or []),
        "bhk": lead.get("bhk"),
        "budget_min": lead.get("budget_min"),
        "budget_max": lead.get("budget_max"),
        "timeline": lead.get("timeline"),
        "purpose": lead.get("purpose"),
        "call_summary": lead.get("call_summary"),
    }
    prompt = (
        f"{_FOLLOWUP_PROMPT}\n\nCALL DETAILS:\n{context}\n\n"
        "Write the WhatsApp follow-up message:"
    )
    response = await client.chat.completions.create(
        model=os.getenv("GROQ_WHATSAPP_MODEL", "groq/compound-mini"),
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()


async def generate_template_variables(transcript: str, lead: dict) -> dict:
    """Extract personalized values from the call for a variable template.

    Returns {"1": ..., "2": ..., "3": ...} matching {{1}}, {{2}}, {{3}}:
      1 = customer name, 2 = property discussed, 3 = suggested next step.
    """
    client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    context = {
        "transcript": (transcript or "")[:4000],
        "lead": {k: v for k, v in (lead or {}).items() if v not in (None, "", [])},
    }
    prompt = (
        "Analyze this real estate sales call and extract exactly three values as JSON:\n"
        '{"1": "customer first name (or \\"there\\" if unknown)", '
        '"2": "property discussed, e.g. \'3 BHK in Sector 150\' (concise, under 40 chars)", '
        '"3": "suggested next step, e.g. \'a site visit this weekend\'"}.\n'
        "Return ONLY valid JSON, no explanation.\n\n"
        f"CALL DETAILS:\n{context}"
    )
    content = None
    try:
        response = await client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=150,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
    except Exception:
        log.warning("json mode failed — retrying without response_format")
        response = await client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=150,
        )
        content = response.choices[0].message.content
    data = _parse_json_response(content)
    return {str(k): str(v or "") for k, v in data.items()}


def _parse_json_response(content: str) -> dict:
    """Parse JSON from an LLM response, tolerating markdown fences or stray text."""
    if not content:
        return {}
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    start, end = content.find("{"), content.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(content[start:end + 1])
        except json.JSONDecodeError:
            log.warning("could not parse JSON from response: %s", content[:200])
    return {}