import typer
import os
import time
from .graph import build_graph
from .ui import console, print_header, print_success, print_error, print_step
from .logger import logger

app = typer.Typer()


@app.command()
def demo():
    """
    Showcases the CLI UI components (Hello World).
    Run this to see the ASCII art and spinners without invoking LLMs.
    """
    print_header()

    print_step("Initializing System Core")
    with console.status("[bold green]Booting up AI Agents...[/]", spinner="dots"):
        time.sleep(1.5)
        console.log("Agents loaded.")
        time.sleep(0.5)
        console.log("LLM Connection established.")

    print_step("Analyzing Dummy Data")
    with console.status("[bold cyan]Reading file structure...[/]", spinner="weather"):
        time.sleep(2)
        console.log("Found 12 Python files.")
        console.log("Found 3 Config files.")

    print_success(
        "Demo initialization complete! Run 'python -m ai_tester.main run .' to start."
    )


@app.command()
def run(path: str = typer.Argument(..., help="Path to the codebase to test")):
    """
    Runs the AI Agentic Tester on the specified repository path.
    """
    print_header()

    if not os.path.exists(path):
        print_error(f"Path '{path}' does not exist.")
        raise typer.Exit(code=1)

    print_step(f"Target Acquired: {path}")

    app_graph = build_graph()

    # Initialize the state dictionary
    initial_state = {
        "target_dir": path,
        "file_list": [],
        "project_context": "",
        "test_plan": "",
        "generated_test_code": "",
        "test_results": "",
        "final_report": "",
    }

    # Execute the graph
    # We wrap execution in a status spinner, but nodes also log their own rich progress.
    try:
        with console.status(
            "[bold white]TestFoundry is working...[/]", spinner="earth"
        ):
            app_graph.invoke(initial_state)

        print_success("Mission Accomplished!")
        console.print(f"[dim]Report generated at: {os.getcwd()}/test_report.txt[/]")
        console.print(f"[dim]Tests generated at: tests/test_generated.py[/]")

    except Exception as e:
        print_error(f"Critical Failure: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
