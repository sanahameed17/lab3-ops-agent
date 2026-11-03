"""
Structured output - Lab 3 guide §3.4 step 4, implemented by us (O).
The LLM must answer with a fixed JSON schema (Pydantic model), so other programs can read it.

Finding (31 Oct, chat demo 1): with_structured_output(method="function_calling") forces a
tool_choice, which DeepSeek's thinking mode rejects with HTTP 400. We therefore use
method="json_mode" (DeepSeek supports JSON output) and, if the provider rejects that too,
fall back to a plain call whose JSON is validated with the same Pydantic model.
"""
import json
import re
from typing import Literal

from pydantic import BaseModel, Field

from core.helper.llm_util import init_llm


class ServiceStatus(BaseModel):
    """Machine-readable health report of one Kubernetes Deployment."""
    service_name: str = Field(description="Name of the Deployment / Service")
    namespace: str = Field(description="Kubernetes namespace")
    status: Literal["Healthy", "Degraded", "Down", "Unknown"] = Field(
        description="Healthy = all replicas ready; Degraded = some ready; Down = none ready")
    ready_replicas: int = Field(ge=0, description="Number of ready replicas")
    desired_replicas: int = Field(ge=0, description="Number of desired replicas")
    error_log: str = Field(description="Most relevant warning or error lines, empty string if none")
    recommendation: str = Field(description="One short recommended next action")


STATUS_PROMPT = """You are a Kubernetes operations expert. Fill in the status report from the facts below.
Rules: status is Healthy only if ready_replicas == desired_replicas and desired_replicas > 0;
Down if ready_replicas == 0; otherwise Degraded. Copy numbers exactly from the facts.
Do not invent errors - use an empty error_log if the facts show no current problem.

Facts:
{facts}
"""


def build_status_report(facts: str) -> ServiceStatus:
    llm = init_llm()
    prompt = (STATUS_PROMPT.format(facts=facts)
              + "\nReturn ONLY one json object (no markdown) that matches this JSON schema:\n"
              + json.dumps(ServiceStatus.model_json_schema()))
    try:
        result = llm.with_structured_output(ServiceStatus, method="json_mode").invoke(prompt)
        print("[structured_output] method = json_mode")
        return result
    except Exception as e:
        print(f"[structured_output] json_mode failed ({type(e).__name__}); using plain call + Pydantic validation")
        text = llm.invoke(prompt).content
        match = re.search(r"\{.*\}", text, re.S)
        return ServiceStatus.model_validate_json(match.group(0) if match else text)