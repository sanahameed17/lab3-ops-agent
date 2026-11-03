# Source: Lab 3 guide §4.5.1.
# Our change: in the guide, `return content` in read_file is outside the function
# (Python SyntaxError); it is indented correctly here. Import of @tool added.
from langchain_core.tools import tool


def write_file(content, file_path):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote content to {file_path}"
    except Exception as e:
        return f"Failed to write to file {file_path}: {str(e)}"


def read_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return f"{file_path} doesn't exist"
    return content


@tool("file_read_tool")
def file_read_tool(file_path: str):
    """
    read contents of a file

    Args:
        file_path: the path of this file
    """
    return read_file(file_path)


@tool("file_write_tool")
def file_write_tool(content: str, file_path: str):
    """
    Write content into a file at the specified path.

    Args:
        content: The content to write into the file.
        file_path: The full path of the file to be written.
    """
    return write_file(content, file_path)