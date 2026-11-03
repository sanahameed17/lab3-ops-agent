"""
Unit tests for the Kubernetes safety guards (our own test cases TC5-TC11, TC13-TC14).
Run with:  uv run python tests/test_k8s_guards.py      (no cluster or LLM needed)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tools.docker_tools import container_exec_cmd_tool, container_logs_tool
from core.tools.k8s_tools import check_manifest, check_namespace

assert check_namespace("lab3-agent") is None
print("PASS TC5: lab3-agent namespace allowed")

assert check_namespace("bookinfo") is not None
print("PASS TC6: Lab 2 namespace 'bookinfo' refused")

assert check_namespace("kube-system") is not None and check_namespace("default") is not None
print("PASS TC7: kube-system and default refused")

role = "apiVersion: rbac.authorization.k8s.io/v1\nkind: ClusterRole\nmetadata:\n  name: x\n"
assert "not allowed" in check_manifest(role, "lab3-agent")
print("PASS TC8: ClusterRole manifest refused")

other_ns = "apiVersion: v1\nkind: Service\nmetadata:\n  name: x\n  namespace: bookinfo\n"
assert "expected 'lab3-agent'" in check_manifest(other_ns, "lab3-agent")
print("PASS TC9: object aimed at another namespace refused")

ok = (
    "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web\n  namespace: lab3-agent\n"
    "---\n"
    "apiVersion: v1\nkind: Service\nmetadata:\n  name: web\n  namespace: lab3-agent\n"
)
assert check_manifest(ok, "lab3-agent") is None
print("PASS TC10: valid Deployment + Service accepted")

assert check_manifest("kind: [unclosed", "lab3-agent").startswith("Invalid YAML")
print("PASS TC11: invalid YAML reported")

# TC13/TC14: regression tests for Run K1b (agent entered Kubernetes node containers via exec)
for name in ("desktop-worker", "desktop-control-plane", "kind-registry-mirror"):
    r = container_exec_cmd_tool.invoke({"container_name": name, "command": "ls"})
    assert r.startswith("Refused"), r
print("PASS TC13: exec into Kubernetes node / registry containers refused")

r = container_logs_tool.invoke({"container_name": "desktop-worker", "wait_seconds": 0})
assert r.startswith("Refused"), r
print("PASS TC14: logs of Kubernetes node container refused")

print("ALL 9 TESTS PASSED")