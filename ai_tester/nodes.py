import subprocess
from langchain_core.messages import SystemMessage, HumanMessage
from .state import AgentState
from .utils import (
    get_file_tree,
    get_all_files_list,
    read_file_content,
    save_test_file,
    save_report,
)
from .llm import resilient_invoke
from .logger import logger


def analyze_codebase(state: AgentState) -> AgentState:
    """
    Node 1: Polyglot Analysis. Reads any text file in the repo.
    """
    logger.info(
        "🔍 [bold cyan]Analyzing Codebase Structure...[/]", extra={"markup": True}
    )

    root_dir = state["target_dir"]
    visual_tree = get_file_tree(root_dir)
    files_list = get_all_files_list(root_dir)

    project_context = f"# Project Structure\n```\n{visual_tree}\n```\n\n"

    analyzer_prompt = (
        "You are a Senior Software Architect. Analyze the following source code file. "
        "Extract key classes, functions, export definitions, and their purpose. "
        "Do NOT include implementation details, just the interface/contract. "
        "Format as Markdown."
    )
    for file_path in files_list:
        logger.info(f"  Reading: [dim]{file_path}[/]", extra={"markup": True})
        content = read_file_content(f"{root_dir}/{file_path}")

        try:
            response = resilient_invoke(
                [
                    SystemMessage(content=analyzer_prompt),
                    HumanMessage(content=f"File: {file_path}\n\nCode:\n{content}"),
                ]
            )
            project_context += f"## File: {file_path}\n{response.content}\n\n"
        except Exception as e:
            logger.error(f"Failed to analyze {file_path}: {e}")
            project_context += f"## File: {file_path}\n[Analysis Failed]\n\n"

    return {"file_list": files_list, "project_context": project_context} 
