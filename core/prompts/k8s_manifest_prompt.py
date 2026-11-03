# Prompt for k8s_manifest_generate_tool - our extension (O) for Lab 3 Discussion Q1 / Scenario 3.
# The requirements are written out explicitly so that the same request gives the same manifest
# (prompt stability, Discussion Q2).
# [after Run K1b] readinessProbe timeoutSeconds 5 / failureThreshold 6: the default 1 s timeout
# made the Vue dev server Pods flap between Ready and NotReady.
manifest_prompt_template = """
Generate Kubernetes YAML with exactly two documents separated by a line containing only ---

1. An apps/v1 Deployment named {app_name} in namespace {namespace} with {replicas} replicas,
   label app: {app_name}, and one container named {app_name} that uses image {image}
   with imagePullPolicy: IfNotPresent and containerPort {container_port}.
   Add a readinessProbe (httpGet path / on port {container_port}, initialDelaySeconds 20,
   periodSeconds 10, timeoutSeconds 5, failureThreshold 6) and resources
   (requests: cpu 100m, memory 256Mi; limits: cpu 1, memory 1Gi).

2. A v1 Service named {app_name} in namespace {namespace}, type ClusterIP,
   selector app: {app_name}, port {service_port} with targetPort {container_port}.

Output ONLY the YAML, no explanation and no markdown fences.
"""