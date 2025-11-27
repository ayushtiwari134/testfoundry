import logging
from rich.logging import RichHandler
from .ui import console


def setup_logger(name: str = "ai_tester"):
    """
    Configures a production-grade logger using RichHandler.
    This ensures logs are colored, timestamped, and formatted nicely.

    Args:
        name (str): The name of the logger instance.

    Returns:
        logging.Logger: Configured logger.
    """
    logging.basicConfig(
        level="INFO",
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True, markup=True)],
    )
    return logging.getLogger(name)


# Singleton logger instance
logger = setup_logger()
