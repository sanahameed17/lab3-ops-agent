"""
Loop guard (circuit breaker) - our own (O), Lab 3 Discussion Q5.

Finding (31 Oct 16:11, chat demo 2, question 2): the agent already had the answer
(ready_replicas = 2) but called k8s_status_report_tool 10 times in a row with the same
input until max_iterations stopped it. The guard blocks an IDENTICAL consecutive call
(same tool, same input) and tells the agent to use the result it already has.
k8s_wait_ready_tool is exempt, because calling it again while an image is pulling is correct.
"""
import functools
import json

EXEMPT_TOOLS = {"k8s_wait_ready_tool"}


class LoopGuard:
    def __init__(self):
        self.last_call = None
        self.blocked = 0

    def reset(self):
        self.last_call = None

    def wrap(self, tool_name, func):
        @functools.wraps(func)
        def guarded(*args, **kwargs):
            key = (tool_name, json.dumps(kwargs, sort_keys=True, default=str), repr(args))
            if tool_name not in EXEMPT_TOOLS and key == self.last_call:
                self.blocked += 1
                return (f"LOOP GUARD: you just called {tool_name} with exactly the same input and "
                        "already have its result above. Do not call it again - use that result "
                        "and give the Final Answer (or choose a different action).")
            self.last_call = key
            return func(*args, **kwargs)
        return guarded