import asyncio
from dotenv import load_dotenv
load_dotenv()
from services.llm_service import LLMBrain

async def main():
    brain = LLMBrain()
    print("Testing LLM...\n")

    turns = [
        "Hi, yes I did fill a form for a 2BHK flat",
        "My budget is around 80 lakhs",
        "I'm looking in Bandra or Andheri",
    ]

    for user_input in turns:
        print(f"User: {user_input}")
        response = await brain.generate_response(user_input)
        print(f"Priya: {response}\n")

asyncio.run(main())
