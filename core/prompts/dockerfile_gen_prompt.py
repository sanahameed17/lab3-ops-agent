# Source: Lab 3 guide §4.5.2 (prompt verbatim).
prompt_template = """
generate a complete and functional Dockerfile for a project based on the following requirements.

Note the content:
- Only use the simplest method mentioned in requirements to run app
- Only use the image required in requirements

requirements:
{requirement}


Output ONLY the Dockerfile content, no explanation or extra text.
"""