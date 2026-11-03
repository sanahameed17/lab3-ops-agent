"""
Interactive Ops Agent with conversational memory (guide §3.4 step 5) and structured
status reports (guide §3.4 step 4) - our own (O).

Usage:
    uv run chat_agent.py --demo     scripted 3-turn conversation (evidence for the report)
    uv run chat_agent.py            type your own questions, 'exit' to quit
"""
import sys

from core.agent_builder import OpsAgent
from core.helper.logger import get_logger
from core.tools.k8s_tools import K8S_TOOLS
from core.tools.status_tools import k8s_status_report_tool

CHAT_RULES = """
Chat rules:
- Only use namespaces that start with lab3-. Never touch other namespaces and never delete anything.
- Work with the cluster ONLY through the k8s_* tools. Never run commands inside Kubernetes node containers.
- For a question about the health or status of a service, call k8s_status_report_tool and put its JSON in the final answer.
- Use the conversation history to understand words such as "it", "its" or "that service".
- Answer the question that was asked; do not deploy or change anything unless the user asks for it.
"""

DEMO_QUESTIONS = [
    "What is the status of the vue-paper-dashboard deployment in namespace lab3-agent?",
    "How many of its replicas are ready right now?",
    "Show me the last 10 log lines of it.",
]


def main():
    logger = get_logger(save_dir="./output/logs", task_name="chatAgent")
    agent = OpsAgent(
        logger,
        extra_tools=K8S_TOOLS + [k8s_status_report_tool],
        extra_rules=CHAT_RULES,
        max_iterations=10,
        use_memory=True,
    )

    if "--demo" in sys.argv:
        for question in DEMO_QUESTIONS:
            print("\n" + "=" * 80 + f"\nUSER: {question}\n" + "=" * 80)
            agent.invoke(question)
        return

    while True:
        question = input("\nYou> ").strip()
        if question.lower() in ("exit", "quit"):
            break
        if question:
            agent.invoke(question)


if __name__ == "__main__":
    main()