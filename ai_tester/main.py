import typer
from rich.console import Console

app= typer.Typer()
console=Console()

@app.command()
def analyze(path: str ="."):
    """Placeholder for Agent 1: Analyzes the given path."""
    console.print(f"[bold blue]Agent 1 initialized![/bold blue] Analyzing path: {path}")

@app.command()
def plan():
    """Placeholder for Agent 2: Generates the test plan."""
    console.print("[bold green]Agent 2 initialized![/bold green] Generating test plan...")

if __name__ == "__main__":
    app()