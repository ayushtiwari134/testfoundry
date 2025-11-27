import typer
import os
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from ai_tester.utils import get_file_tree
from ai_tester.llm import get_llm_response

# Initialize the application
app = typer.Typer()
console = Console()


@app.command()
def analyze(path: str = "."):
    """
    Agent 1: Analyzes the codebase structure and creates a summary.
    """
    console.print(
        Panel.fit(
            f"[bold blue]Agent 1: Code Analyzer[/bold blue]\nTarget: {path}",
            border_style="blue",
        )
    )

    # Step 1: Scan the file system
    with console.status(
        "[bold blue]Scanning file system...[/bold blue]", spinner="dots"
    ):
        file_tree = get_file_tree(path)

    console.print(f"[dim]Found file structure. Sending to AI...[/dim]")

    # Step 2: Ask the AI to analyze the structure
    prompt = (
        f"You are an expert Lead Developer. Analyze this project structure and tell me "
        f"what kind of project this is, what the tech stack likely is, and what the key files are.\n\n"
        f"Project Structure:\n{file_tree}"
    )

    with console.status(
        "[bold yellow]Analyzing project architecture...[/bold yellow]",
        spinner="aesthetic",
    ):
        analysis = get_llm_response(prompt)

    # Step 3: Display the report
    console.print(
        Panel(Markdown(analysis), title="Project Analysis Report", border_style="green")
    )

    # Save the context for the next agent
    with open("project_context.md", "w") as f:
        f.write(analysis)
    console.print("\n[bold green]✓ Analysis saved to project_context.md[/bold green]")


@app.command()
def plan():
    """
    Agent 2: Reads the analysis and generates a detailed Test Plan.
    """
    console.print(
        Panel.fit(
            "[bold magenta]Agent 2: Test Architect[/bold magenta]",
            border_style="magenta",
        )
    )

    # Check if Agent 1 has done its job
    if not os.path.exists("project_context.md"):
        console.print("[bold red]Error:[/bold red] 'project_context.md' not found.")
        console.print("Please run [bold blue]ai-tester analyze[/bold blue] first.")
        raise typer.Exit(code=1)

    # Step 1: Read the context
    with open("project_context.md", "r") as f:
        context = f.read()

    # Step 2: Ask AI to generate a plan
    prompt = (
        f"You are a QA Architect. Based on the following project analysis, create a comprehensive Test Plan.\n"
        f"The plan should include:\n"
        f"1. Recommended Testing Frameworks (e.g. pytest for Python, Jest for JS)\n"
        f"2. Unit Test Strategy (Key functions to test)\n"
        f"3. Integration Test Strategy (How modules interact)\n"
        f"4. Edge Cases (What could go wrong?)\n\n"
        f"Project Analysis:\n{context}"
    )

    with console.status(
        "[bold magenta]Drafting test strategy...[/bold magenta]", spinner="material"
    ):
        test_plan = get_llm_response(prompt)

    # Step 3: Display and Save
    console.print(
        Panel(Markdown(test_plan), title="Test Strategy Plan", border_style="cyan")
    )

    with open("test_plan.md", "w") as f:
        f.write(test_plan)

    console.print("\n[bold green]✓ Test Plan saved to test_plan.md[/bold green]")


@app.command()
def run_tests():
    """
    Placeholder for Agent 3: Runs tests and reports.
    """
    console.print("[bold red]Agent 3 initialized![/bold red] Running tests...")


if __name__ == "__main__":
    app()
