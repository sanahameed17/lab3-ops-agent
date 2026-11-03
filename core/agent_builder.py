"""
Ops Agent construction. Source: Lab 3 guide §4.6.
Our changes (O):
 1. LangChain 1.x moved initialize_agent / AgentType out of `langchain.agents`; they are in
    `langchain_classic` (installed together with langchain 1.4.7), so they are imported from there.
 2. The guide passes prompt=prompt, but initialize_agent() builds its own structured-chat ReAct
    prompt. Our DevOps instructions (guide §4.4) are therefore given as the prompt prefix via
    agent_kwargs; LangChain adds the tool list and descriptions itself.
 3. handle_parsing_errors=True: a badly formatted LLM reply is sent back to the LLM instead of
    crashing the run.
 4. Each run's full Thought/Action/Observation trace is saved in output/logs (evidence).
 5. clean_final_answer(): extracts the answer if the LLM returned the final step as a JSON blob.
 6. [after Run 2] two extra tools: container_logs_tool and container_remove_tool.
 7. [after Run 3a] RobustStructuredChatOutputParser (DeepSeek DSML / bare JSON / plain final answer).
 8. [K8s extension] extra_tools, extra_rules and max_iterations can be passed in.
 9. [after Run K1a] wrong tool inputs become an Observation instead of crashing the run.
10. [guide §3.4 step 5] use_memory=True adds ConversationBufferMemory (the guide imports it but
    never uses it), so follow-up questions such as "what is its status now?" can be resolved.
11. [after chat demo 2] LoopGuard (circuit breaker, Discussion Q5) blocks identical consecutive
    tool calls.
"""
import json
import re
import time

from langchain_classic.agents import AgentType, initialize_agent
from langchain_core.prompts import MessagesPlaceholder

from core.helper.llm_util import init_llm
from core.helper.loop_guard import LoopGuard
from core.helper.output_parser import RobustStructuredChatOutputParser
from core.prompts.ops_agent_prompt import system_template
from core.tools.docker_tools import (
    container_exec_cmd_tool,
    container_logs_tool,
    container_remove_tool,
    container_run_tool,
    dockerfile_generate_tool,
    image_build_tool,
)
from core.tools.failure_tools import failure_diagnosis_tool
from core.tools.file_tools import file_read_tool, file_write_tool

# Guide §4.4 system prompt without the {tool_names}/{tools} lines,
# because the structured-chat agent inserts the tool list itself.
BASE_PREFIX = "\n".join(
    line for line in system_template.strip().splitlines()
    if "{tool_names}" not in line and "{tools}" not in line
)


def clean_final_answer(text):
    """Extract the answer if the LLM returned the final step as a JSON blob."""
    try:
        data = json.loads(re.sub(r"^```(json)?|```$", "", str(text).strip()).strip())
        if isinstance(data, dict) and data.get("action") == "Final Answer":
            return str(data.get("action_input", text))
    except (ValueError, TypeError):
        pass
    return text


class OpsAgent:
    def __init__(self, logger, extra_tools=None, extra_rules="", max_iterations=30, use_memory=False):
        self.logger = logger
        self.llm = init_llm()
        self.loop_guard = LoopGuard()

        tools = [
            dockerfile_generate_tool,
            file_read_tool,
            file_write_tool,
            image_build_tool,
            container_run_tool,
            container_exec_cmd_tool,
            failure_diagnosis_tool,
            container_logs_tool,
            container_remove_tool,
        ] + list(extra_tools or [])
        for t in tools:
            t.handle_validation_error = True  # (O) wrong inputs become an Observation, not a crash
            t.handle_tool_error = True
            if not getattr(t.func, "_loop_guarded", False):
                t.func = self.loop_guard.wrap(t.name, t.func)
                t.func._loop_guarded = True

        prefix = BASE_PREFIX + "\n" + extra_rules.strip() + "\n\nYou have access to the following tools:"
        agent_kwargs = {
            "prefix": prefix,
            "output_parser": RobustStructuredChatOutputParser(),
        }

        self.memory = None
        if use_memory:
            from langchain_classic.memory import ConversationBufferMemory
            self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
            agent_kwargs["memory_prompts"] = [MessagesPlaceholder(variable_name="chat_history")]
            agent_kwargs["input_variables"] = ["input", "agent_scratchpad", "chat_history"]

        self.agent = initialize_agent(
            tools=tools,
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            agent_kwargs=agent_kwargs,
            memory=self.memory,
            verbose=True,
            max_iterations=max_iterations,
            handle_parsing_errors=True,
        )

    def invoke(self, query):
        self.logger.info("TASK: %s", query)
        start = time.time()
        self.loop_guard.reset()
        blocked_before = self.loop_guard.blocked

        trace_file = getattr(self.logger, "trace_file", None)
        if trace_file:
            from langchain_core.callbacks import FileCallbackHandler
            with FileCallbackHandler(trace_file, mode="a") as handler:
                response = self.agent.invoke({"input": query}, config={"callbacks": [handler]})
        else:
            response = self.agent.invoke({"input": query})

        response["output"] = clean_final_answer(response.get("output", ""))
        self.logger.info("FINISHED in %.1f s (loop guard blocked %d repeated call(s))",
                         time.time() - start, self.loop_guard.blocked - blocked_before)
        self.logger.info("FINAL ANSWER: %s", response["output"])
        print(f"Final Answer: {response['output']}")
        return response