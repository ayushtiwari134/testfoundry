import pyfiglet
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.syntax import Syntax
from .config import (
    APP_NAME,
    APP_SLOGAN,
    APP_VERSION,
    STYLE_PRIMARY,
    STYLE_SECONDARY,
    STYLE_PANEL_BORDER,
)

# Global Console Instance for printing to terminal
console = Console()


def print_header():
    """
    Renders the ASCII logo and welcome panel at the top of the CLI execution.
    Uses pyfiglet for the font and Rich Panel for the subtitle.
    """
    # Generate ASCII Art for the App Name
    ascii_art = pyfiglet.figlet_format(APP_NAME, font="slant")
    ascii_text = Text(ascii_art, style=STYLE_PRIMARY)

    # Create the subtitle panel with version and slogan
    subtitle = f"[bold {STYLE_SECONDARY}]v{APP_VERSION}[/] | {APP_SLOGAN}"
    panel = Panel(
        subtitle,
        title=f"[bold {STYLE_PRIMARY}]{APP_NAME}[/]",
        border_style=STYLE_PANEL_BORDER,
        expand=False,
    )

    console.print(ascii_text)
    console.print(panel)
    console.print()  # Spacer


def print_step(title: str, content: str = ""):
    """
    Prints a distinct step header in the process to guide the user.

    Args:
        title (str): The main step title (e.g., "Analyzing Codebase").
        content (str): Optional description or detail.
    """
    console.print(f"\n[bold {STYLE_SECONDARY}]➤ {title}[/]")
    if content:
        console.print(f"  [dim]{content}[/]")


def print_code(code: str, language: str = "python", title: str = "Generated Code"):
    """
    Renders code with syntax highlighting in a styled panel.

    Args:
        code (str): The source code string.
        language (str): Language for syntax highlighting (python, javascript, etc.).
        title (str): Title of the code block panel.
    """
    syntax = Syntax(code, language, theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title=title, border_style=STYLE_SECONDARY))


def print_success(message: str):
    """Prints a success message with a green checkmark."""
    console.print(f"[bold green]✔ {message}[/]")


def print_error(message: str):
    """Prints an error message with a red cross."""
    console.print(f"[bold red]✘ {message}[/]")
