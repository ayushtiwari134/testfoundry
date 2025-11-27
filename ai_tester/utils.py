import os
from typing import List, Set
from pathlib import Path
from file_types import BINARY_EXTENSIONS, IGNORED_DIRS, IGNORED_FILES


def is_binary_file(filepath: str) -> bool:
    """
    Determines if a file is binary based on extension or content sniffing.

    Args:
        filepath (str): Path to the file.

    Returns:
        bool: True if binary, False if text.
    """
    # Fast check by extension
    if any(filepath.lower().endswith(ext) for ext in BINARY_EXTENSIONS):
        return True

    # Slow check by reading first 1024 bytes for null characters
    try:
        with open(filepath, "rb") as f:
            return b"\x00" in f.read(1024)
    except Exception:
        return True


def get_file_tree(start_path: str = ".") -> str:
    """
    Recursively walks the directory to create a visual string representation.
    Useful for giving the Agent a high-level map of the project.

    Args:
        start_path (str): Root directory to start from.

    Returns:
        str: ASCII tree diagram of the folder structure.
    """
    tree_str = ""
    for root, dirs, files in os.walk(start_path):
        # Filter directories in-place
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        level = root.replace(start_path, "").count(os.sep)
        indent = " " * 4 * (level)
        tree_str += f"{indent}{os.path.basename(root)}/\n"

        subindent = " " * 4 * (level + 1)
        for f in files:
            if f not in IGNORED_FILES:
                tree_str += f"{subindent}{f}\n"
    return tree_str


def get_all_files_list(start_path: str = ".") -> List[str]:
    """
    Returns a list of all readable text source files in the project.

    Args:
        start_path (str): Root directory.

    Returns:
        List[str]: Relative paths to valid source files.
    """
    file_paths = []
    for root, dirs, files in os.walk(start_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        for file in files:
            if file in IGNORED_FILES:
                continue

            full_path = os.path.join(root, file)

            if is_binary_file(full_path):
                continue

            file_paths.append(os.path.relpath(full_path, start_path))

    return file_paths


def read_file_content(filepath: str) -> str:
    """
    Safely reads file content, replacing errors for encoding issues.
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        return f"[Error reading {filepath}: {e}]"


def save_test_file(content: str, output_path: str):
    """
    Writes generated test code to a file, ensuring parent directories exist.
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)


def save_report(content: str, output_path: str = "test_report.txt"):
    """
    Saves the final execution report to a text file.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
