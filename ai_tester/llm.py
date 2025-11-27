import os
import sys
from langchain_community.chat_models import ChatLiteLLM
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from .config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS
from .logger import logger

load_dotenv()


def validate_environment(model_name: str):
    """
    Checks if the required API key for the chosen model provider is set.
    Fails fast if the key is missing to prevent runtime crashes later.

    Args:
        model_name (str): The model string (e.g., 'openrouter/gpt-4').
    """
    provider_keys = {
        "openrouter": "OPENROUTER_API_KEY",
        "gpt": "OPENAI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "mistral": "MISTRAL_API_KEY",
    }

    for prefix, env_var in provider_keys.items():
        if model_name.startswith(prefix):
            if not os.getenv(env_var):
                logger.critical(
                    f"Missing API Key! Model '{model_name}' requires '{env_var}' in .env"
                )
                sys.exit(1)


def get_llm():
    """
    Initializes and returns the ChatLiteLLM instance based on config.
    """
    validate_environment(LLM_MODEL)
    return ChatLiteLLM(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        max_tokens=LLM_MAX_TOKENS,
        verbose=False,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def resilient_invoke(messages):
    """
    Wrapper for LLM invocation with retry logic for network stability.
    """
    llm = get_llm()
    return llm.invoke(messages)
