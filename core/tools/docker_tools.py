"""
Docker tools for the Ops Agent. Source: Lab 3 guide §4.5.2 - §4.5.5.
Our changes (O):
 - imports added; remove_image / diagnosis_sentence come from core.helper.io_util;
 - LLM created inside dockerfile_generate_tool (guide uses a global `llm` it never defines);
 - container_run_tool docstring: removed the hard-coded "internal port 9528";
 - subprocess output decoded as UTF-8 (Windows default cp1252 can break on npm output);
 - [after Run 2] container_exec_cmd_tool runs the command through `sh -c`;
 - [after Run 2] NEW container_logs_tool and container_remove_tool;
 - [after Run K1b] exec / logs / remove REFUSE Kubernetes node and system containers
   (in Run K1b the agent used exec to enter desktop-worker, desktop-control-plane and
   kind-registry-mirror, bypassing the namespace guard of the k8s tools).
"""
import os
import subprocess
import time

import docker
from docker.errors import NotFound
from langchain_core.tools import tool

from core.helper.io_util import diagnosis_sentence, remove_image
from core.prompts.dockerfile_gen_prompt import prompt_template
from core.tools.file_tools import read_file, write_file

PROTECTED_NAME_PARTS = ("control-plane", "worker", "kind", "k8s", "kube", "registry", "desktop-")


def is_protected_container(name):
    """True for Kubernetes node / registry / system containers the agent must not touch."""
    lowered = (name or "").lower()
    return any(part in lowered for part in PROTECTED_NAME_PARTS)


def _refusal(name, action):
    return (f"Refused: '{name}' looks like a Kubernetes node or system container; "
            f"the agent may not {action} it. Use the k8s_* tools to work with the cluster.")


@tool("dockerfile_generate_tool")
def dockerfile_generate_tool(readme_path: str, project_path: str, save_path: str):
    """
    Generate contents of a DockerFile based on README.md, and save the DockerFile in a specific path

    Args:
        - readme_path: path of README.md
        - project_path: path of the project where the Dockerfile works
        - save_path: path of the saved Dockerfile
    """
    from core.helper.llm_util import init_llm
    llm = init_llm()

    requirement = read_file(readme_path)
    prompt = prompt_template.format(requirement=requirement, project_path=project_path)
    response = llm.invoke(prompt)
    dockerfile_text = response.content.strip().replace("```dockerfile", "").replace("```", "")

    return write_file(dockerfile_text, save_path) + diagnosis_sentence


@tool("image_build_tool")
def image_build_tool(docker_file_path: str, image_tag: str):
    """
    Build a Docker image from a specific Dockerfile.

    Args:
        docker_file_path (str): Path to the Dockerfile (relative to build context)
        image_tag (str): Tag name for the resulting image
    """
    original_dir = os.getcwd()
    docker_dir = os.path.dirname(docker_file_path)
    dockerfile_name = os.path.basename(docker_file_path)
    os.chdir(docker_dir)
    cmd = ["docker", "build", "-t", image_tag, "-f", dockerfile_name, "."]

    full_log = []
    try:
        remove_image(image_tag)
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True, encoding="utf-8", errors="replace",
        )
        for line in proc.stdout:
            full_log.append(line)
        proc.stdout.close()
    except Exception as e:
        full_log = [f"Exception occurred: {str(e)}"]
    finally:
        os.chdir(original_dir)

    return "".join(full_log) + diagnosis_sentence


@tool("container_run_tool")
def container_run_tool(image_tag: str, container_name: str, internal_port: int, expose_port: int):
    """
    start and run a Docker container from a specified image.

    Args:
        image_tag: The tag of the image to run the container from.
        container_name: The name to assign to the new container.
        internal_port: Port used inside the container.
        expose_port: The host port to map to the container's internal port.
    """
    cmd = ["docker", "run", "-d", "--name", container_name, "-p", f"{expose_port}:{internal_port}", image_tag]

    full_log = []
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True, encoding="utf-8", errors="replace",
        )
        for line in proc.stdout:
            full_log.append(line)
        proc.stdout.close()
    except Exception as e:
        full_log.append(f"Unexpected error during container run: {str(e)}\n")

    return "".join(full_log) + diagnosis_sentence


@tool("container_exec_cmd_tool")
def container_exec_cmd_tool(container_name: str, command: str):
    """
    Execute a shell command inside an already running Docker container that this task created.
    The command is run with `sh -c`, so cd, && and pipes work.
    Kubernetes node and system containers are refused.

    Args:
        container_name: The name of the container.
        command: The command to execute
    """
    if is_protected_container(container_name):
        return _refusal(container_name, "run commands in")
    client = docker.from_env()
    try:
        container = client.containers.get(container_name)
        exit_code, output = container.exec_run(
            cmd=["sh", "-c", command], stdout=True, stderr=True, demux=False, tty=False
        )
        output_text = output.decode(errors="ignore")
        return f"Exit code: {exit_code}\n\n Output:\n{output_text}" + diagnosis_sentence
    except NotFound:
        return f"Container '{container_name}' not found." + diagnosis_sentence
    except Exception as e:
        return f"Failed to execute command: {str(e)}" + diagnosis_sentence


@tool("container_logs_tool")
def container_logs_tool(container_name: str, wait_seconds: int = 20, tail: int = 40):
    """
    Show the latest log lines of a container to check whether the application inside
    started correctly. Use it after container_run_tool, before giving the final answer.

    Args:
        container_name: The name of the container.
        wait_seconds: Seconds to wait before reading the logs (gives the app time to start, max 120).
        tail: Number of last log lines to return.
    """
    if is_protected_container(container_name):
        return _refusal(container_name, "read the logs of")
    time.sleep(max(0, min(int(wait_seconds), 120)))
    result = subprocess.run(
        ["docker", "logs", "--tail", str(tail), container_name],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return (result.stdout + result.stderr).strip() + diagnosis_sentence


@tool("container_remove_tool")
def container_remove_tool(container_name: str):
    """
    Stop and remove ONE container created for this task (for example an old or broken one
    with the same name) so it can be re-created. Kubernetes/kind system containers are refused.

    Args:
        container_name: The name of the container to remove.
    """
    if is_protected_container(container_name):
        return _refusal(container_name, "remove")
    result = subprocess.run(
        ["docker", "rm", "-f", container_name],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return (result.stdout + result.stderr).strip() + diagnosis_sentence