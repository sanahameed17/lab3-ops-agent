"""
Logger helper. The guide calls get_logger(save_dir, task_name) but does not show it - written by us (O).
Writes messages to the console and to output/logs/<task>_<time>.log, and reserves a
<task>_<time>_trace.log file for the agent's full Thought/Action/Observation trace.
"""
import logging
import os
from datetime import datetime


def get_logger(save_dir: str, task_name: str) -> logging.Logger:
    os.makedirs(save_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(save_dir, f"{task_name}_{stamp}.log")

    logger = logging.getLogger(task_name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    for handler in (logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()):
        handler.setFormatter(fmt)
        logger.addHandler(handler)

    logger.trace_file = os.path.join(save_dir, f"{task_name}_{stamp}_trace.log")
    logger.info("Log file: %s", log_file)
    logger.info("Trace file: %s", logger.trace_file)
    return logger