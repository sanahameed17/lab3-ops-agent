# Source: Lab 3 guide §4.5.6 (prompt verbatim).
prompt_template = """
You are an expert DevOps engineer.

Failure Details:
----------------
{failure_msg}

Results by searching in internet:
----------------
{search_res}

Please locate the root cause and provide a solution strategy. Your response should:
1. Identify the likely cause of the error and suggest a solution
2. output results in one line, don't exceed 100 words

Only include helpful technical information. Do not ask for user confirmation.
"""