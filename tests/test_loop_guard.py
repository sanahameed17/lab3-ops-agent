"""
Unit tests for LoopGuard (our own test cases TC21-TC23).
Run with:  uv run python tests/test_loop_guard.py      (no LLM or cluster needed)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.helper.loop_guard import LoopGuard

calls = []


def fake_tool(**kwargs):
    calls.append(kwargs)
    return "real result"


g = LoopGuard()
status = g.wrap("k8s_status_report_tool", fake_tool)
wait = g.wrap("k8s_wait_ready_tool", fake_tool)

# TC21: identical consecutive call is blocked (chat demo 2, question 2)
assert status(namespace="lab3-agent", deployment="web") == "real result"
r = status(namespace="lab3-agent", deployment="web")
assert r.startswith("LOOP GUARD") and len(calls) == 1 and g.blocked == 1, r
print("PASS TC21: identical consecutive call blocked")

# TC22: a call with a different input is allowed
assert status(namespace="lab3-agent", deployment="other") == "real result" and len(calls) == 2
print("PASS TC22: call with different input allowed")

# TC23: k8s_wait_ready_tool may be repeated (waiting for a slow image pull is correct)
assert wait(namespace="lab3-agent", deployment="web") == "real result"
assert wait(namespace="lab3-agent", deployment="web") == "real result" and len(calls) == 4
print("PASS TC23: k8s_wait_ready_tool is exempt from the guard")

print("ALL 3 TESTS PASSED")