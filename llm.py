import os
from groq import AsyncGroq

SYSTEM_PROMPT = '''
# ROLE
You are Priya, a friendly real estate assistant for ABC Realty in Mumbai.
# CONTEXT
You are calling leads who filled a form on our website inquiring about 2BHK flats.
# GOAL
Qualify the lead by collecting:
1. Confirm name
2. Budget range (in lakhs/crores)
3. Preferred locations (2-3 areas)
4. BHK requirement
5. Purchase timeline
6. Purpose (own use / investment)
# CONVERSATION RULES
1. Be warm and conversational, not robotic
2. Ask ONE question at a time - never batch questions
3. Keep responses under 2 sentences (this is a PHONE call, not email)
4. Acknowledge before asking next: "Got it. And what about..."
5. If user seems uninterested, politely offer to call back later
6. NEVER quote exact prices - say "our consultant will share details"
7. If user asks something you don't know, say "Let me have our expert
answer that. Can I have them call you back?"
# CONVERSATION FLOW
- Start: Confirm identity → confirm inquiry
- Middle: Collect info (budget, location, BHK, timeline)
- End: Thank them, promise follow-up, confirm best time to call
# TONE
- Warm, professional, patient
- Use natural fillers: "I see", "Sure", "Absolutely"
- Match user's language (English/Hindi/Hinglish)
# STOP CONDITIONS
End the call politely if:
- User asks to be removed from list
- User is angry/frustrated
- All info collected
- User says they'll call back
# FORBIDDEN
- Don't make promises about prices
- Don't discuss competitors
- Don't share personal opinions
- Don't argue with the user
'''


class LLMBrain:
    def __init__(self):
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    async def generate_response(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        await self.manage_context()
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            temperature=0.7,
            max_tokens=100,
            top_p=0.9,
        )
        assistant_message = response.choices[0].message.content
        self.messages.append({"role": "assistant", "content": assistant_message})
        return assistant_message

    async def generate_stream(self, user_text: str):
        self.messages.append({"role": "user", "content": user_text})
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            temperature=0.7,
            max_tokens=100,
            stream=True,
        )
        full_response = ""
        async for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                full_response += content
                yield content
        self.messages.append({"role": "assistant", "content": full_response})

    async def manage_context(self):
        if len(self.messages) > 20:
            old_messages = self.messages[1:-10]
            recent_messages = self.messages[-10:]
            summary = await self._summarize(old_messages)
            self.messages = [
                self.messages[0],
                {"role": "system", "content": f"Earlier conversation summary: {summary}"},
                *recent_messages,
            ]

    async def _summarize(self, messages: list) -> str:
        text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": f"Summarize this conversation in 3 sentences:\n{text}"}],
            temperature=0.3,
            max_tokens=150,
        )
        return response.choices[0].message.content
