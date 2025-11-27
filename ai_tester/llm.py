import os
from litellm import completion
from dotenv import load_dotenv

load_dotenv()


def get_llm_response(
    prompt: str, model: str = "openrouter/google/gemini-2.0-flash-001"
) -> str:
    """
    Sends a prompt to the LLM and returns the text response.
    We default to a fast, cheap model (Gemini 2.0 Flash via OpenRouter) for now.
    """

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment variables.")

    messages = [{"role": "user", "content": prompt}]

    try:
        response = completion(model=model, messages=messages, api_key=api_key)

        return response.choices[0].message.content
    except Exception as e:
        raise RuntimeError(f"Error communicating with LLM: {e}")
