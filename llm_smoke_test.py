"""Stage 3 smoke test (our own file): checks the API connection and the model name.
It never prints the API key."""
import os

from dotenv import load_dotenv
from openai import OpenAI

from core.helper.llm_util import init_llm

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"))
print("Models available from provider:", [m.id for m in client.models.list()])

llm = init_llm()
reply = llm.invoke("Reply with exactly this sentence: LLM connection OK")
print("Model used:", llm.model_name)
print("Reply:", reply.content)
print("Tokens used:", reply.usage_metadata)