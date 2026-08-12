import os
from groq import AsyncGroq
from prompts.realestate import REAL_ESTATE_PROMPT


class LLMBrain:
    def __init__(self):
        self.client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.1-70b-versatile"
        system_prompt = REAL_ESTATE_PROMPT.safe_substitute(
            COMPANY_NAME=os.getenv("COMPANY_NAME", "our company"),
            LANGUAGE=os.getenv("LANGUAGE", "English"),
        )
        self.messages = [
            {"role": "system", "content": system_prompt}
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
