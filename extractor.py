import json
import os
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
from groq import AsyncGroq


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
    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": extraction_prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    data = json.loads(response.choices[0].message.content)
    lead = RealEstateLead(**data)
    lead.lead_score = calculate_lead_score(lead)
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
