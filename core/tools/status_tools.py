"""
k8s_status_report_tool - our own (O). Collects real facts with kubectl (read-only) and asks the
LLM to turn them into the structured ServiceStatus JSON (guide §3.4 step 4).
"""
import json

from langchain_core.tools import tool

from core.helper.io_util import diagnosis_sentence
from core.helper.structured_output import build_status_report
from core.tools.k8s_tools import _run, check_namespace


def collect_facts(namespace, deployment):
    code, out = _run(["kubectl", "get", "deployment", deployment, "-n", namespace, "-o", "json"])
    if code != 0:
        return None, out
    d = json.loads(out)
    spec, st = d.get("spec", {}), d.get("status", {})
    facts = [
        f"deployment: {deployment}",
        f"namespace: {namespace}",
        f"desired_replicas: {spec.get('replicas', 0)}",
        f"ready_replicas: {st.get('readyReplicas', 0)}",
        f"available_replicas: {st.get('availableReplicas', 0)}",
    ]
    for c in st.get("conditions", []):
        facts.append(f"condition {c.get('type')}={c.get('status')}: {c.get('message', '')}")
    _, pods = _run(["kubectl", "get", "pods", "-n", namespace, "-l", f"app={deployment}", "--no-headers"])
    facts.append("pods:\n" + pods)
    _, events = _run(["kubectl", "get", "events", "-n", namespace,
                      "--field-selector", "type=Warning", "--sort-by=.lastTimestamp"])
    facts.append("recent warning events:\n" + "\n".join(events.splitlines()[-5:]))
    return "\n".join(facts), None


@tool("k8s_status_report_tool")
def k8s_status_report_tool(namespace: str, deployment: str):
    """
    Return a STRUCTURED JSON health report of a Deployment with the fields
    service_name, namespace, status (Healthy/Degraded/Down/Unknown), ready_replicas,
    desired_replicas, error_log and recommendation. Use it for any status or health question.

    Args:
        namespace: Namespace of the Deployment (must start with lab3-).
        deployment: Name of the Deployment.
    """
    refusal = check_namespace(namespace)
    if refusal:
        return refusal
    facts, err = collect_facts(namespace, deployment)
    if facts is None:
        return f"Could not read deployment: {err}" + diagnosis_sentence
    try:
        return build_status_report(facts).model_dump_json(indent=2)
    except Exception as e:
        return f"Structured report failed: {e}" + diagnosis_sentence