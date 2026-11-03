"""
Robust output parser for the structured-chat ReAct agent - written by us (O).

Fix 1 (30 Oct, Run 3a): DeepSeek sometimes answers with its own native tool-call markup
("<｜｜DSML｜｜ invoke name=...>"); the default parser treated it as the FINAL ANSWER.
Fix 2 (31 Oct, Run K1a): action_input sent as ONE JSON string (string="true") is decoded as JSON.
Fix 3 (31 Oct, chat demo 1): a bare JSON action without the ``` code block, and a plain
"Final Answer: ..." text, were mis-handled (the first ended the run as a fake answer, the
second caused a parsing error). Both are now recognised.

Unreadable output raises OutputParserException so the error is sent back to the LLM
(handle_parsing_errors=True) instead of ending the run with a fake answer.
"""
import json
import re

from langchain_classic.agents.structured_chat.output_parser import StructuredChatOutputParser
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.exceptions import OutputParserException

INVOKE_RE = re.compile(r'invoke name="([^"]+)"(.*?)(?:</[^>]*invoke>|$)', re.S)
PARAM_RE = re.compile(r'parameter name="([^"]+)"(?:\s+string="(true|false)")?\s*>(.*?)</', re.S)

FORMAT_HINT = (
    "Invalid format. Reply with exactly ONE action as a JSON blob inside ``` "
    'with the keys "action" and "action_input".'
)


def _parse_dsml(text):
    match = INVOKE_RE.search(text)
    if not match:
        return None
    tool, body = match.group(1), match.group(2)
    params = {}
    for name, is_string, raw in PARAM_RE.findall(body):
        raw = raw.strip()
        if name == "action_input" or is_string != "true":
            try:
                params[name] = json.loads(raw)
            except json.JSONDecodeError:
                params[name] = raw
        else:
            params[name] = raw
    if not params:
        return None
    tool_input = params["action_input"] if set(params) == {"action_input"} else params
    return tool, tool_input


def _parse_bare(text):
    """Bare JSON action (no ``` block) or plain 'Final Answer: ...' text."""
    s = text.strip()
    if s.lower().startswith("final answer:"):
        return AgentFinish({"output": s[len("final answer:"):].strip()}, text)
    body = re.sub(r"^```(?:json)?\s*|\s*```$", "", s).strip()
    if body.startswith("{") and body.endswith("}"):
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return None
        if isinstance(data, dict) and "action" in data:
            if data["action"] == "Final Answer":
                return AgentFinish({"output": str(data.get("action_input", ""))}, text)
            return AgentAction(data["action"], data.get("action_input", {}), text)
    return None


class RobustStructuredChatOutputParser(StructuredChatOutputParser):
    def parse(self, text):
        if "DSML" in text or "invoke name=" in text:
            parsed = _parse_dsml(text)
            if parsed is None:
                raise OutputParserException(
                    f"Could not parse LLM output: {text}",
                    observation=FORMAT_HINT,
                    llm_output=text,
                    send_to_llm=True,
                )
            tool, tool_input = parsed
            if tool == "Final Answer":
                return AgentFinish({"output": str(tool_input)}, text)
            return AgentAction(tool, tool_input, text)

        bare = _parse_bare(text)
        if bare is not None:
            return bare
        return super().parse(text)