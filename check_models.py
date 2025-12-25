import os
import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import get_settings

settings = get_settings()
api_key = settings.GOOGLE_API_KEY

models_to_test = [
    "gemini-2.0-flash-exp",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-pro",
    "models/gemini-2.0-flash-exp",
    "models/gemini-pro"
]

async def test():
    print(f"Testing models with API Key ending in ...{api_key[-4:] if api_key else 'None'}")
    for model_name in models_to_test:
        print(f"Testing {model_name}...")
        try:
            llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)
            res = await llm.ainvoke("Hello")
            print(f"SUCCESS: {model_name} response: {res.content}")
            return
        except Exception as e:
            print(f"FAILED: {model_name} error: {e}")

if __name__ == "__main__":
    asyncio.run(test())
