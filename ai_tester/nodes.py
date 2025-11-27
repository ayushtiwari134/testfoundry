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


def plan_tests(state: AgentState) -> AgentState:
    """
    Node 2: Generates a test plan based on the analyzed context.
    """
    logger.info("[bold magenta]Constructing Test Plan...[/]", extra={"markup": True})
    context = state["project_context"]

    planner_prompt = (
        "You are a QA Lead. Analyze the Context. "
        "1. Identify the language/framework. "
        "2. Choose the best test runner (pytest, jest, gotest). "
        "3. Create a detailed test plan covering unit and integration scenarios. "
        "4. Return the plan in Markdown."
    )
    response = resilient_invoke(
        [SystemMessage(content=planner_prompt), HumanMessage(content=context)]
    )

    return {"test_plan": response.content}


def generate_tests(state: AgentState) -> AgentState:
    """
    Node 3: Writes the actual test code.
    """
    logger.info("[bold green]Writing Test Code...[/]", extra={"markup": True})
    context = state["project_context"]
    plan = state["test_plan"]

    generator_prompt = (
        "You are a Test Automation Engineer. Write the actual test code based on the plan. "
        "Return ONLY the code block. Ensure imports match the structure."
    )

    response = resilient_invoke(
        [
            SystemMessage(content=generator_prompt),
            HumanMessage(content=f"Context:\n{context}\n\nPlan:\n{plan}"),
        ]
    )

    # Strip markdown code blocks if LLM adds them
    code = (
        response.content.replace("```python", "")
        .replace("```javascript", "")
        .replace("```", "")
        .strip()
    )

    # NOTE: Defaulting to a python file for now.
    # In a fully dynamic version, we'd ask the LLM for the filename/extension.
    save_test_file(code, "tests/test_generated.py")

    return {"generated_test_code": code}


def run_tests_and_report(state: AgentState) -> AgentState:
    """
    Node 4: Runs the generated tests and creates a report.
    """
    logger.info("[bold blue]Running Tests...[/]", extra={"markup": True})

    try:
        # TODO: This command should ideally be dynamic based on the plan (e.g., 'npm test')
        result = subprocess.run(
            ["pytest", "tests/test_generated.py"], capture_output=True, text=True
        )
        output = result.stdout + result.stderr
    except Exception as e:
        output = f"Execution Error: {str(e)}"

    logger.info("[bold yellow]Generating Report...[/]", extra={"markup": True})

    report_prompt = "You are a CI/CD Reporter. Summarize these test results in a professional report."

    response = resilient_invoke(
        [SystemMessage(content=report_prompt), HumanMessage(content=output)]
    )

    save_report(response.content)

    return {"test_results": output, "final_report": response.content}
