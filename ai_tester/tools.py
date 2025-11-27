# tools.py
import os
import json
import shlex
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Tuple, Callable, Union

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ----------------- Optional @tool decorator shim -----------------
# Some run-time environments / langchain versions provide `@tool` decorator.
# Try to import it; otherwise define a no-op that attaches metadata to the function.
try:
    # langchain changeover: some versions use langchain.tools import tool
    from langchain.tools import tool as _real_tool  # type: ignore

    tool = _real_tool
except Exception:
    # Fallback no-op decorator that stores metadata on the function for introspection
    def tool(name: str = None, description: str = None):
        def deco(fn):
            try:
                fn._tool_name = name or fn.__name__
                fn._tool_description = description or ""
            except Exception:
                pass
            return fn

        return deco


# ----------------- File type configuration (adjust as needed) -----------------
BINARY_EXTENSIONS = [
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".mp4",
    ".mov",
    ".pdf",
    ".exe",
    ".dll",
    ".so",
    ".bin",
    ".class",
    ".jar",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
]

IGNORED_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".idea",
    ".pytest_cache",
}
IGNORED_FILES = {".DS_Store", "thumbs.db"}


# ----------------- Utility functions (IO / helpers) -----------------


def is_binary_file(filepath: str) -> bool:
    """
    Quick heuristic: extension check then content sniffing.
    """
    if any(filepath.lower().endswith(ext) for ext in BINARY_EXTENSIONS):
        return True
    try:
        with open(filepath, "rb") as f:
            return b"\x00" in f.read(1024)
    except Exception:
        # If we cannot read, treat as binary to be safe
        return True


def get_file_tree(start_path: str = ".") -> str:
    """
    Produce an ASCII-ish tree of start_path.
    """
    tree_str = ""
    start_path = str(start_path)
    for root, dirs, files in os.walk(start_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        level = root.replace(start_path, "").count(os.sep)
        indent = " " * 4 * (level)
        tree_str += f"{indent}{os.path.basename(root) or root}/\n"
        subindent = " " * 4 * (level + 1)
        for f in files:
            if f not in IGNORED_FILES:
                tree_str += f"{subindent}{f}\n"
    return tree_str


def get_all_files_list(start_path: str = ".") -> List[str]:
    """
    Walk and return non-binary, non-ignored file paths relative to start_path.
    """
    file_paths = []
    start_path = str(start_path)
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
    Read file safely with utf-8 and fallback; return error string on failure.
    """
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        logger.exception("Error reading file %s", filepath)
        return f"[Error reading {filepath}: {e}]"


def save_test_file(content: str, output_path: str):
    """
    Save test file content; create parent dirs if needed.
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)


def save_report(content: str, output_path: str = "test_report.txt"):
    """
    Save final report.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(content)


def save_intermediate(path: str, content: Any):
    """
    Save intermediate artifacts under outputs/ for auditing.
    Accepts str, dict, list; dumps JSON for structures.
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, (dict, list)):
        with open(out, "w", encoding="utf-8") as f:
            json.dump(content, f, indent=2)
    else:
        with open(out, "w", encoding="utf-8") as f:
            f.write(str(content))


# ----------------- Compilation / Execution helpers -----------------


def compile_python_code_snippet(code: str) -> Tuple[bool, str]:
    """
    Try to compile Python code snippet to catch SyntaxError before saving/executing.
    Returns (ok, error_message).
    """
    try:
        compile(code, "<generated_test>", "exec")
        return True, ""
    except Exception as e:
        return False, repr(e)


def run_pytest_and_capture(pytest_args: List[str] = None, timeout: int = 300) -> str:
    """
    Run pytest in a subprocess and capture stdout+stderr. Defaults to tests/ dir.
    """
    args = ["pytest"] + (pytest_args or ["-q", "tests/"])
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return proc.stdout + proc.stderr
    except Exception as e:
        logger.exception("Error running pytest")
        return f"Error running pytest: {e}"


# ----------------- Ollama model runner (thin wrapper) -----------------


def run_model_via_ollama(
    prompt: str, model_name: str = "deepseek-r1:14b", timeout: int = 60
) -> str:
    """
    Run ollama locally. This wrapper assumes `ollama` is on PATH and that the model is installed.
    It uses `ollama run <model> --prompt -` style invocation and writes the prompt to stdin.
    If your Ollama version requires different flags, adjust this function.
    """
    cmd = f"ollama run {shlex.quote(model_name)} --prompt -"
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            input=prompt.encode("utf-8"),
            capture_output=True,
            timeout=timeout,
        )
        out = proc.stdout.decode("utf-8", errors="replace")
        if proc.returncode != 0:
            err = proc.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"ollama failed ({proc.returncode}): {err}")
        return out
    except FileNotFoundError:
        raise RuntimeError(
            "Ollama not found on PATH. Install Ollama or update run_model_via_ollama to your runtime."
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Ollama invocation timed out.")


# ----------------- Planner selection validation / cost estimation -----------------


def validate_files_selection(
    selection: List[dict], repo_root: str, max_files: int = 10
) -> List[dict]:
    """
    Validate and sanitize planner's files_to_test list.
    Ensures path is inside repo_root and enforces max_files cap.
    Returns a list of dicts: {"path": rel_path, "reason":..., "test_type":...}
    """
    repo_root_path = Path(repo_root).resolve()
    validated = []
    seen = set()
    for item in selection:
        try:
            path = str(item.get("path", "")).strip()
        except Exception:
            continue
        if not path:
            continue
        cand = (Path(repo_root) / path).resolve()
        # Path must be inside repo root
        try:
            if (
                repo_root_path not in cand.parents
                and repo_root_path != cand
                and repo_root_path != cand.parent
            ):
                logger.debug(
                    "Skipping path outside repo root: %s (resolved: %s)", path, cand
                )
                continue
        except Exception:
            continue
        rel = os.path.relpath(cand, repo_root_path)
        if rel.startswith(".."):
            continue
        if rel in seen:
            continue
        seen.add(rel)
        validated.append(
            {
                "path": rel,
                "reason": (
                    item.get("reason", "")
                    if isinstance(item.get("reason", ""), str)
                    else ""
                ),
                "test_type": (
                    item.get("test_type", "unit")
                    if item.get("test_type") in ("unit", "integration")
                    else "unit"
                ),
            }
        )
        if len(validated) >= max_files:
            break
    return validated


def estimate_cost_for_files(
    files: List[dict],
    runtime_per_test_s: float = 3.0,
    cost_per_second_usd: float = 0.0005,
) -> dict:
    """
    Heuristic cost estimator for chosen tests:
    - runtime_per_test_s: average seconds per test file
    - cost_per_second_usd: infra / CI cost per second
    Returns estimate dict with usd and seconds.
    """
    count = len(files)
    estimated_seconds = int(count * runtime_per_test_s)
    estimate_usd = round(estimated_seconds * cost_per_second_usd, 6)
    return {"estimate_usd": estimate_usd, "estimated_seconds": estimated_seconds}


# ----------------- Tool Implementations -----------------
# Decorate tools with @tool for frameworks that expect it. The decorator above is safe
# (no-op when real decorator is not present).


@tool(
    name="file_reader",
    description="Read the content of a repository file. args: {repo_root, path}",
)
def file_reader_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    args: {"path": "relative/path/to/file", "repo_root": "/abs/path"}
    returns: {"content": "...", "path": "..."}
    """
    repo_root = args.get("repo_root", ".")
    path = args.get("path")
    if not path:
        return {"error": "no path provided"}
    full = Path(repo_root) / path
    try:
        content = read_file_content(str(full))
        save_intermediate(f"outputs/tool_file_read_{Path(path).name}.txt", content)
        return {"content": content, "path": path}
    except Exception as e:
        logger.exception("file_reader_tool error")
        return {"error": str(e)}


@tool(
    name="file_list",
    description="Return the list of files in the repository. args: {repo_root}",
)
def file_list_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    args: {"repo_root": "/abs/path"}
    returns: {"files": [ ... ]}
    """
    repo_root = args.get("repo_root", ".")
    try:
        files = get_all_files_list(repo_root)
        save_intermediate("outputs/tool_file_list.json", files)
        return {"files": files}
    except Exception as e:
        logger.exception("file_list_tool error")
        return {"error": str(e)}


@tool(
    name="cost_estimator",
    description="Estimate test runtime/cost for a list of files. args: {files, runtime_per_test_s, cost_per_second_usd}",
)
def cost_estimator_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    args: {"files": [{"path": "..."}], "runtime_per_test_s": 3.0}
    returns: {"estimate": {"estimate_usd":.., "estimated_seconds":..}}
    """
    files = args.get("files", [])
    runtime_per = args.get("runtime_per_test_s", 3.0)
    cost_per_second = args.get("cost_per_second_usd", 0.0005)
    try:
        estimate = estimate_cost_for_files(
            files, runtime_per_test_s=runtime_per, cost_per_second_usd=cost_per_second
        )
        save_intermediate("outputs/tool_cost_estimate.json", estimate)
        return {"estimate": estimate}
    except Exception as e:
        logger.exception("cost_estimator_tool error")
        return {"error": str(e)}


@tool(
    name="model_runner",
    description="Run a local Ollama model with prompt. args: {prompt, model_name, timeout, as_json}",
)
def model_runner_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    args: {
      "prompt": "...",
      "model_name": "deepseek-r1:14b",
      "timeout": 60,
      "as_json": False
    }
    returns: {"output": "<raw model string>", "json": ...}
    """
    prompt = args.get("prompt", "")
    model_name = args.get("model_name", "deepseek-r1:14b")
    timeout = int(args.get("timeout", 60))
    as_json = bool(args.get("as_json", False))
    try:
        out = run_model_via_ollama(prompt, model_name=model_name, timeout=timeout)
        save_intermediate("outputs/tool_model_output.txt", out)
        if as_json:
            try:
                parsed = json.loads(out)
                return {"output": out, "json": parsed}
            except Exception:
                return {"output": out, "json_error": "failed to parse JSON"}
        return {"output": out}
    except Exception as e:
        logger.exception("model_runner_tool error")
        return {"error": str(e)}


# ----------------- Binding helper -----------------
def _make_tool_descriptor(
    name: str, description: str, fn: Callable[[Dict[str, Any]], Dict[str, Any]]
):
    """
    Minimal descriptor used by certain langchain_ollama versions.
    If your bind_tools expects a different shape, adapt this function.
    """
    return {"name": name, "description": description, "fn": fn}


def tools_for_binding() -> List[Dict[str, Any]]:
    """
    Return tool descriptors ready for binding to an LLM.
    The descriptor format may need adaptation to your `langchain_ollama` version.
    """
    return [
        _make_tool_descriptor(
            "file_reader",
            "Read repository file content. args: {repo_root, path}",
            file_reader_tool,
        ),
        _make_tool_descriptor(
            "file_list", "List files in the repo. args: {repo_root}", file_list_tool
        ),
        _make_tool_descriptor(
            "cost_estimator",
            "Estimate runtime/cost. args: {files, runtime_per_test_s, cost_per_second_usd}",
            cost_estimator_tool,
        ),
        _make_tool_descriptor(
            "model_runner",
            "Run a local Ollama model. args: {prompt, model_name, timeout, as_json}",
            model_runner_tool,
        ),
    ]
