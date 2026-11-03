"""
Web-search helper for failure_diagnosis_tool.
The guide calls init_search_util() but does not show it - written by us (O).
Uses GoogleSerperAPIWrapper (imported in guide §4.6). If SERPER_API_KEY is missing,
a fallback object is returned so the diagnosis still works with the LLM only.
"""
import os

from dotenv import load_dotenv
from langchain_community.utilities import GoogleSerperAPIWrapper

load_dotenv()


class _NoSearch:
    def run(self, query: str) -> str:
        return "Web search not available (SERPER_API_KEY not set)."


def init_search_util():
    if os.getenv("SERPER_API_KEY"):
        return GoogleSerperAPIWrapper(k=5)
    return _NoSearch()