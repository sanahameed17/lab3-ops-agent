"""
LLM setup. Source: Lab 3 guide §4.3 (environment-variable version).
Our changes (O):
 - key, URL and model are read from the .env file (python-dotenv), never written in code;
 - guide sets OPENAI_BASE_URL but reads OPENAI_API_BASE_URL (mismatch) -> we read OPENAI_BASE_URL;
 - timeout and max_tokens added, as recommended in guide §3.4 step 3;
 - provider: DeepSeek (OpenAI-compatible), allowed by the professor ("any API is fine").
"""
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def init_llm():
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    model = os.getenv("MODEL_NAME", "deepseek-flash")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set - check the .env file")

    llm = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=0,
        max_retries=2,
        timeout=60,
        max_tokens=2048,
    )
    return llm