"""
Kubernetes tools for the Ops Agent - our extension (O), answering Lab 3 Discussion Q1 /
Scenario 3 ("deploy the service automatically to a Kubernetes cluster").

Design decisions:
 - kubectl is called through subprocess with argument lists (never through a shell), so tool
   inputs cannot inject extra commands. `kubectl apply` is idempotent and handles multi-document
   YAML; the kubernetes Python client has no apply operation.
 - SAFETY: only namespaces starting with "lab3-" (or "bookinfo-agent", the name used in
   Scenario 3) are allowed; Lab 2 namespaces are refused. Only Deployment, Service and ConfigMap
   objects may be applied, every manifest gets a server-side dry run first, and there is no
   delete tool.
 - Local images are used directly: on 31 Oct a test pod in namespace lab3-imgtest pulled
   vue-paper-dashboard:latest from Docker Desktop's built-in mirror in 1m44s, so no registry
   push is needed.
 - [after Run K1b] two parallel pulls of the 436 MB image took ~16 min, so the wait limit is
   30 min; the service check now also counts READY endpoints (port-forward alone reached a pod
   while the Service had no ready endpoints).
"""
import os
import re
import socket
import subprocess
import time
import urllib.request

import yaml
from langchain_core.tools import tool

from core.helper.io_util import diagnosis_sentence
from core.prompts.k8s_manifest_prompt import manifest_prompt_template
from core.tools.file_tools import write_file

ALLOWED_NAMESPACE = re.compile(r"^(lab3-[a-z0-9]([-a-z0-9]*[a-z0-9])?|bookinfo-agent)$")
ALLOWED_KINDS = {"Deployment", "Service", "ConfigMap"}


def check_namespace(namespace):
    """Return None if the namespace is allowed, otherwise the reason for refusal."""
    if not ALLOWED_NAMESPACE.match(namespace or ""):
        return (f"Refused: namespace '{namespace}' is not allowed. The agent may only use "
                "namespaces that start with 'lab3-' (or 'bookinfo-agent').")
    return None


def check_manifest(text, namespace):
    """Return None if the YAML is acceptable, otherwise the reason for refusal."""
    try:
        docs = [d for d in yaml.safe_load_all(text) if d]
    except yaml.YAMLError as e:
        return f"Invalid YAML: {e}"
    if not docs:
        return "Manifest is empty."
    for d in docs:
        if not isinstance(d, dict):
            return "Invalid manifest document."
        kind = d.get("kind")
        if kind not in ALLOWED_KINDS:
            return f"Refused: kind '{kind}' is not allowed (allowed: {sorted(ALLOWED_KINDS)})."
        meta = d.get("metadata") or {}
        ns = meta.get("namespace")
        if ns not in (None, namespace):
            return (f"Refused: object '{meta.get('name')}' targets namespace '{ns}', "
                    f"expected '{namespace}'.")
    return None


def _run(args, timeout=600):
    try:
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except subprocess.TimeoutExpired:
        return 1, f"Command timed out after {timeout} s: {' '.join(args)}"
    except FileNotFoundError:
        return 1, "kubectl was not found on PATH"


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@tool("k8s_manifest_generate_tool")
def k8s_manifest_generate_tool(app_name: str, image: str, container_port: int, replicas: int,
                               namespace: str, service_port: int, save_path: str):
    """
    Generate Kubernetes Deployment + Service YAML for an application with the LLM,
    check it (allowed kinds and namespace) and save it to a file.

    Args:
        app_name: Name for the Deployment, the Service and the app label.
        image: Container image, e.g. vue-paper-dashboard:latest (local images are allowed).
        container_port: Port the application listens on inside the container.
        replicas: Number of Pod replicas.
        namespace: Target namespace (must start with lab3-).
        service_port: Port exposed by the ClusterIP Service.
        save_path: Where to save the YAML, e.g. k8s/vue-paper-dashboard.yaml
    """
    refusal = check_namespace(namespace)
    if refusal:
        return refusal

    from core.helper.llm_util import init_llm
    llm = init_llm()
    prompt = manifest_prompt_template.format(
        app_name=app_name, image=image, container_port=container_port, replicas=replicas,
        namespace=namespace, service_port=service_port,
    )
    text = llm.invoke(prompt).content.strip()
    text = re.sub(r"^```(?:yaml|yml)?\s*|\s*```$", "", text).strip()

    problem = check_manifest(text, namespace)
    if problem:
        return f"Generated manifest rejected: {problem}\n---\n{text}" + diagnosis_sentence

    os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
    return f"{write_file(text + chr(10), save_path)}\n---\n{text}" + diagnosis_sentence


@tool("k8s_namespace_tool")
def k8s_namespace_tool(namespace: str):
    """
    Create a Kubernetes namespace if it does not exist yet.
    Only namespaces starting with lab3- are allowed.

    Args:
        namespace: Name of the namespace.
    """
    refusal = check_namespace(namespace)
    if refusal:
        return refusal
    code, _ = _run(["kubectl", "get", "namespace", namespace])
    if code == 0:
        return f"Namespace '{namespace}' already exists."
    _, out = _run(["kubectl", "create", "namespace", namespace])
    return out + diagnosis_sentence


@tool("k8s_apply_tool")
def k8s_apply_tool(manifest_path: str, namespace: str):
    """
    Check a YAML manifest (allowed kinds, namespace, server-side dry run) and apply it with kubectl.

    Args:
        manifest_path: Path of the YAML file.
        namespace: Target namespace (must start with lab3-).
    """
    refusal = check_namespace(namespace)
    if refusal:
        return refusal
    try:
        with open(manifest_path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return f"{manifest_path} doesn't exist" + diagnosis_sentence

    problem = check_manifest(text, namespace)
    if problem:
        return problem + diagnosis_sentence

    code, out = _run(["kubectl", "apply", "-n", namespace, "--dry-run=server", "-f", manifest_path])
    if code != 0:
        return "Server-side dry run failed, nothing was applied:\n" + out + diagnosis_sentence
    _, out = _run(["kubectl", "apply", "-n", namespace, "-f", manifest_path])
    return out + diagnosis_sentence


@tool("k8s_wait_ready_tool")
def k8s_wait_ready_tool(namespace: str, deployment: str, timeout_seconds: int = 900):
    """
    Wait until all Pods of a Deployment are Ready (kubectl rollout status), then list the Pods.
    Pulling a large local image can take 15 minutes or more per node; while Pods are
    'ContainerCreating' or events say 'Pulling', simply call this tool again.

    Args:
        namespace: Namespace of the Deployment.
        deployment: Name of the Deployment.
        timeout_seconds: Maximum time to wait (30-1800 seconds, default 900).
    """
    refusal = check_namespace(namespace)
    if refusal:
        return refusal
    t = max(30, min(int(timeout_seconds), 1800))
    _, out = _run(["kubectl", "rollout", "status", f"deployment/{deployment}", "-n", namespace,
                   f"--timeout={t}s"], timeout=t + 30)
    _, pods = _run(["kubectl", "get", "pods", "-n", namespace, "-o", "wide"])
    return f"{out}\n\nPods:\n{pods}" + diagnosis_sentence


@tool("k8s_pod_logs_tool")
def k8s_pod_logs_tool(namespace: str, deployment: str, tail: int = 40):
    """
    Show recent logs of a Deployment's Pods and the latest namespace events,
    to find out why Pods are not Ready or why the application fails.

    Args:
        namespace: Namespace of the Deployment.
        deployment: Name of the Deployment.
        tail: Number of log lines to return.
    """
    refusal = check_namespace(namespace)
    if refusal:
        return refusal
    _, logs = _run(["kubectl", "logs", f"deployment/{deployment}", "-n", namespace, f"--tail={int(tail)}"])
    _, events = _run(["kubectl", "get", "events", "-n", namespace, "--sort-by=.lastTimestamp"])
    events = "\n".join(events.splitlines()[-15:])
    return f"Logs:\n{logs}\n\nRecent events:\n{events}" + diagnosis_sentence


@tool("k8s_service_check_tool")
def k8s_service_check_tool(namespace: str, service: str, service_port: int, path: str = "/"):
    """
    Check that a Service really works: count its READY endpoints, then open a temporary
    kubectl port-forward and send an HTTP GET request. The check only PASSES when the
    Service has at least one ready endpoint AND the request returns HTTP 200.

    Args:
        namespace: Namespace of the Service.
        service: Name of the Service.
        service_port: Port of the Service.
        path: URL path to request, default "/".
    """
    refusal = check_namespace(namespace)
    if refusal:
        return refusal
    _, svc = _run(["kubectl", "get", "svc", service, "-n", namespace, "-o", "wide"])
    _, ready_list = _run([
        "kubectl", "get", "endpointslices", "-n", namespace,
        "-l", f"kubernetes.io/service-name={service}",
        "-o", "jsonpath={range .items[*].endpoints[*]}{.addresses[0]} ready={.conditions.ready}{'\\n'}{end}",
    ])
    ready_count = ready_list.count("ready=true")

    local_port = _free_port()
    pf = subprocess.Popen(
        ["kubectl", "port-forward", "-n", namespace, f"svc/{service}", f"{local_port}:{service_port}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    status = None
    try:
        time.sleep(4)
        # Bypass the Windows system proxy (Clash) for this local request.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(f"http://127.0.0.1:{local_port}{path}", timeout=20) as resp:
                status = resp.status
                body = resp.read(300).decode("utf-8", errors="replace")
                http = f"HTTP {status} via port-forward 127.0.0.1:{local_port}:\n{body}"
        except Exception as e:
            http = f"HTTP check failed: {e}"
    finally:
        pf.terminate()
        try:
            pf.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pf.kill()

    verdict = "PASS" if (ready_count >= 1 and status == 200) else "FAIL"
    reason = f"ready endpoints = {ready_count}, HTTP status = {status}"
    return (f"VERDICT: {verdict} ({reason})\n\nService:\n{svc}\n\nEndpoints:\n{ready_list or '(none)'}"
            f"\n\n{http}" + diagnosis_sentence)


K8S_TOOLS = [
    k8s_manifest_generate_tool,
    k8s_namespace_tool,
    k8s_apply_tool,
    k8s_wait_ready_tool,
    k8s_pod_logs_tool,
    k8s_service_check_tool,
]