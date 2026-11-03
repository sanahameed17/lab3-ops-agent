"""
Entry point. Source: Lab 3 guide §4.7 (task text verbatim).
Note: the guide's text later says to open port 8002, but the task itself asks for
external port 8080 and the README runs the app on 8080, so 8080 is used.
"""
import random

import numpy as np

from core.agent_builder import OpsAgent
from core.helper.logger import get_logger


def random_seed(seed):
    random.seed(seed)
    np.random.seed(seed)


def main():
    random_seed(42)
    log_dir = "./output/logs"

    logger = get_logger(save_dir=log_dir, task_name="gitAgent")

    ops_agent = OpsAgent(logger)
    user_input = """1. Read the requirements in vue-paper-dashboard/README.md and outputs a Dockerfile for the project
    2. Runs the Dockerfile to build a Docker image named vue-paper-dashboard and runs a container (exposing external port 8080) based on the image.
    """
    # 3. Executes the test command npx jest tests/unit/utils/validate.spec.js inside the container my-vue-container.

    ops_agent.invoke(user_input)


if __name__ == "__main__":
    main()