"""
Helper functions used by the Docker tools.
NOT given in the Lab 3 guide (the guide calls them but does not define them) - written by us.
"""
import subprocess

# Appended to every tool result so the agent knows what to do after an error.
diagnosis_sentence = (
    "\nIf the output above shows an error, call failure_diagnosis_tool "
    "with the error message before retrying."
)


def remove_image(image_tag: str) -> str:
    """Remove an existing image with the same tag so the rebuild starts clean.
    Only this one tag is removed; 'No such image' is harmless and ignored."""
    result = subprocess.run(
        ["docker", "image", "rm", "-f", image_tag],
        capture_output=True,
        text=True,
    )
    return (result.stdout + result.stderr).strip()