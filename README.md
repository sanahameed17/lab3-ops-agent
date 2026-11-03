# Lab 3: Operations Agent with LangChain and ReAct

Source code for Lab 3 (Agent Services) of the Advanced Software Engineering course, Wuhan University.

**Student:** Sana Hameed (2026272110001) · **Instructor:** Jian Wang

The agent uses an LLM (DeepSeek, through an OpenAI-compatible API) and the ReAct pattern of LangChain to:

1. read the README of a front-end project, write a Dockerfile, build the image and run the container (the guide task, `main.py`);
2. deploy the same image to Kubernetes with a Deployment and a Service and verify it (`main_k8s.py`, my extension for Discussion Question 1);
3. answer status questions in a chat with conversational memory and structured JSON output (`chat_agent.py`).

The full report (Labs 1–3) explains the design, every agent run, the problems found and how they were fixed.

## Project structure

```
main.py                  guide task: Dockerfile -> image -> container (port 8080)
main_k8s.py              Kubernetes deployment task (namespace lab3-agent, 2 replicas)
chat_agent.py            chat assistant with memory and structured output (--demo)
llm_smoke_test.py        checks the LLM connection
core/agent_builder.py    OpsAgent: LangChain AgentExecutor (STRUCTURED_CHAT ReAct)
core/helper/             LLM setup, logger, output parser, loop guard, structured output
core/prompts/            system prompt and prompts for Dockerfile, diagnosis and K8s manifests
core/tools/              file, Docker, failure-diagnosis, Kubernetes and status tools
tests/                   23 test cases (no LLM or cluster needed)
k8s/                     Kubernetes manifest written by the agent
vue-paper-dashboard/     the application the agent deployed (Creative Tim, MIT licence) + the Dockerfile written by the agent
lab2_tools/              scripts, YAML files and data of the Lab 2 re-runs (31 Oct 2026)
output/logs/             trace logs of all agent runs
```

## Requirements

- Windows with Docker Desktop (Kubernetes enabled, kind, 5 nodes), `kubectl`
- Python 3.11 and [uv](https://docs.astral.sh/uv/)
- An API key for an OpenAI-compatible LLM (DeepSeek was used) and optionally a Serper key for web search

## Setup

```powershell
uv sync
```

Create a file `.env` in the project folder (it is not in this repository):

```
OPENAI_API_KEY=<your key>
OPENAI_BASE_URL=https://api.deepseek.com
MODEL_NAME=deepseek-flash
SERPER_API_KEY=<your key, optional>
```

If Docker Hub is not reachable, set a proxy in Docker Desktop and use the legacy builder:

```powershell
$env:DOCKER_BUILDKIT = "0"
```

## Run

```powershell
uv run llm_smoke_test.py                  # LLM connection
uv run main.py                            # guide task (Docker)
uv run main_k8s.py                        # Kubernetes deployment
uv run chat_agent.py --demo               # chat with memory and structured output
```

## Tests

```powershell
uv run python tests/test_output_parser.py
uv run python tests/test_k8s_guards.py
uv run python tests/test_structured_output.py
uv run python tests/test_loop_guard.py
```

## Safety

The Kubernetes tools only work in namespaces that start with `lab3-`, only accept Deployment, Service and ConfigMap objects, run a server-side dry run before every apply and offer no delete operation. Docker exec, logs and remove refuse the Kubernetes node and registry containers.

## Notes

- `vue-paper-dashboard/` is the open-source Vue Paper Dashboard by Creative Tim (https://github.com/creativetimofficial/vue-paper-dashboard, MIT licence, see its `LICENSE.md`). Only `vue-paper-dashboard/Dockerfile` was written by the agent.

- `initialize_agent` and `AgentType` are imported from `langchain-classic` because LangChain 1.x moved them there.
- `lab2_tools/bookinfo_monitor_v2.py` was re-implemented on 31 Oct 2026; the original Lab 2 script was not found.
- No API keys are stored in this repository.
