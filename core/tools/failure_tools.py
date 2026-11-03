"""
Failure diagnosis tool. Source: Lab 3 guide §4.5.6.
Our changes (O): imports added; LLM created with init_llm(); if the web search
itself fails (network), the error is passed to the LLM instead of crashing the agent.
"""
from langchain_core.tools import tool

from core.helper.llm_util import init_llm
from core.helper.serper_util import init_search_util
from core.prompts.failure_diagnosis_prompt import prompt_template


@tool("failure_diagnosis_tool")
def failure_diagnosis_tool(failure_msg: str):
    """
    identify the failure reason and suggest a solution

    Args:
        failure_msg: details about current failure
    """
    search_tool = init_search_util()
    try:
        search_res = search_tool.run(failure_msg)
    except Exception as e:
        search_res = f"Web search failed: {e}"

    prompt = prompt_template.format(failure_msg=failure_msg, search_res=search_res)
    llm = init_llm()
    response = llm.invoke(prompt)
    return response.content