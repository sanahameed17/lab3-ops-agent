"""
Unit tests for the structured-output schema (our own test cases TC15-TC18).
Run with:  uv run python tests/test_structured_output.py      (no LLM call needed)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import ValidationError

from core.helper.structured_output import ServiceStatus

good = dict(service_name="vue-paper-dashboard", namespace="lab3-agent", status="Healthy",
            ready_replicas=2, desired_replicas=2, error_log="", recommendation="No action needed")

r = ServiceStatus(**good)
print("PASS TC15: valid status report accepted:", r.status, f"{r.ready_replicas}/{r.desired_replicas}")

try:
    ServiceStatus(**{**good, "status": "Fine"})
    raise AssertionError("expected ValidationError")
except ValidationError:
    print("PASS TC16: status outside Healthy/Degraded/Down/Unknown rejected")

try:
    ServiceStatus(**{**good, "ready_replicas": -1})
    raise AssertionError("expected ValidationError")
except ValidationError:
    print("PASS TC17: negative replica count rejected")

assert ServiceStatus.model_validate_json(r.model_dump_json()) == r
print("PASS TC18: JSON round-trip keeps the same report")

print("ALL 4 TESTS PASSED")