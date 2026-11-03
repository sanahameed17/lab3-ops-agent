"""
Unit tests for RobustStructuredChatOutputParser (our own test cases).
Run with:  uv run python tests/test_output_parser.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.exceptions import OutputParserException

from core.helper.output_parser import RobustStructuredChatOutputParser

p = RobustStructuredChatOutputParser()

# TC1: DeepSeek native tool-call markup (copied from Run 3a, 30 Oct 22:04)
dsml = (
    '<｜｜DSML｜｜ calls>\n<｜｜DSML｜｜ invoke name="file_read_tool">\n'
    '<｜｜DSML｜｜ parameter name="action_input" string="false">'
    '{"file_path": "vue-paper-dashboard/README.md"}</｜｜DSML｜｜ parameter>\n'
    '</｜｜DSML｜｜ invoke>\n</｜｜DSML｜｜ calls>'
)
r = p.parse(dsml)
assert isinstance(r, AgentAction), r
assert r.tool == "file_read_tool" and r.tool_input == {"file_path": "vue-paper-dashboard/README.md"}, r
print("PASS TC1: DSML markup -> AgentAction:", r.tool, r.tool_input)

# TC2: normal LangChain JSON action blob
blob = 'Action:\n```\n{"action": "file_read_tool", "action_input": {"file_path": "output/test.txt"}}\n```'
r = p.parse(blob)
assert isinstance(r, AgentAction) and r.tool == "file_read_tool", r
print("PASS TC2: JSON blob -> AgentAction:", r.tool)

# TC3: normal final answer
fin = 'Action:\n```\n{"action": "Final Answer", "action_input": "done"}\n```'
r = p.parse(fin)
assert isinstance(r, AgentFinish) and r.return_values["output"] == "done", r
print("PASS TC3: Final Answer -> AgentFinish")

# TC4: broken DSML must NOT become a fake final answer
try:
    p.parse('<｜｜DSML｜｜ invoke name="file_read_tool"> broken')
    raise AssertionError("expected OutputParserException")
except OutputParserException:
    print("PASS TC4: broken DSML -> OutputParserException (sent back to the LLM)")

# TC12: whole input sent as ONE string parameter (seen in Run K1a, 31 Oct 00:16)
dsml_str = (
    '<｜｜DSML｜｜ invoke name="k8s_namespace_tool">\n'
    '<｜｜DSML｜｜ parameter name="action_input" string="true">'
    '{"namespace": "lab3-agent"}</｜｜DSML｜｜ parameter>\n</｜｜DSML｜｜ invoke>'
)
r = p.parse(dsml_str)
assert isinstance(r, AgentAction) and r.tool_input == {"namespace": "lab3-agent"}, r
print("PASS TC12: action_input string=\"true\" decoded as JSON:", r.tool_input)

# TC19: bare JSON action without ``` (seen in chat demo 1, 31 Oct 15:59)
bare = '\n\n{\n  "action": "k8s_pod_logs_tool",\n  "action_input": {"namespace": "lab3-agent", "deployment": "vue-paper-dashboard", "tail": 10}\n}'
r = p.parse(bare)
assert isinstance(r, AgentAction) and r.tool == "k8s_pod_logs_tool" and r.tool_input["tail"] == 10, r
print("PASS TC19: bare JSON action -> AgentAction:", r.tool)

# TC20: plain "Final Answer: ..." text (seen in chat demo 1)
r = p.parse("Final Answer:\n\nThe deployment is Healthy.")
assert isinstance(r, AgentFinish) and r.return_values["output"] == "The deployment is Healthy.", r
print("PASS TC20: plain 'Final Answer:' text -> AgentFinish")

print("ALL 7 TESTS PASSED")