import os
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

# --- Application Identity ---
APP_NAME = os.getenv("APP_NAME", "TestFoundry")
APP_VERSION = "0.1.0"
APP_SLOGAN = "Forging Bulletproof Code with AI"

# --- LLM Configuration ---
# Defaults to a local Ollama model if not specified
LLM_MODEL = os.getenv("LLM_MODEL", "ollama/llama3")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "4000"))

# --- UI Theme (Rich Styles) ---
STYLE_PRIMARY = "cyan" 
STYLE_SECONDARY = "magenta"     
STYLE_SUCCESS = "green"
STYLE_ERROR = "bold red"
STYLE_WARNING = "yellow"
STYLE_PANEL_BORDER = "blue"
