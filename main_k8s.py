"""
Entry point for the Kubernetes extension - our own (O).
Answers Lab 3 Discussion Q1 / Scenario 3: the agent deploys the application to Kubernetes
(namespace, Deployment + Service manifests, apply, wait for Ready, verify the Service).
[after Run K1b] rules added: slow image pulls are not failures; never enter node containers.
"""
import random

import numpy as np

from core.agent_builder import OpsAgent
from core.helper.logger import get_logger
from core.tools.k8s_tools import K8S_TOOLS

K8S_RULES = """
Kubernetes rules:
- Only use namespaces that start with lab3-. Never touch other namespaces and never try to delete anything.
- Work with the cluster ONLY through the k8s_* tools. Never run commands inside Kubernetes node containers (desktop-*, kind-*, registry).
- Create the namespace with k8s_namespace_tool before applying manifests.
- After applying, use k8s_wait_ready_tool. Pulling a large local image can take 15 minutes or more per node: if Pods are ContainerCreating or events say Pulling, that is NOT a failure - call k8s_wait_ready_tool again. Only ErrImagePull, ImagePullBackOff or CrashLoopBackOff are failures.
- If Pods are not Ready, use k8s_pod_logs_tool to find the cause, fix it and apply again.
- Finish only after k8s_service_check_tool returns VERDICT: PASS.
"""


def main():
    random.seed(42)
    np.random.seed(42)
    logger = get_logger(save_dir="./output/logs", task_name="k8sAgent")

    agent = OpsAgent(logger, extra_tools=K8S_TOOLS, extra_rules=K8S_RULES, max_iterations=30)
    user_input = """Deploy the existing Docker image vue-paper-dashboard:latest (the app listens on port 8080)
to the Kubernetes cluster in namespace lab3-agent with 2 replicas.
Expose it with a ClusterIP Service named vue-paper-dashboard on port 80.
Wait until the Pods are Ready and verify that the Service returns the dashboard page.
Save the manifest as k8s/vue-paper-dashboard.yaml."""
    agent.invoke(user_input)


if __name__ == "__main__":
    main()