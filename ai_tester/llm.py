# llm.py
import os
import sys
import logging
import json
import re
from typing import List, Dict, Any, Optional

from tenacity import retry, stop_after_attempt, wait_exponential
from dotenv import load_dotenv

load_dotenv()

from .logger import logger
from .config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS

# Prefer ChatLiteLLM as the single LLM client (keeps previous behavior).
try:
    from langchain_litellm import ChatLiteLLM
except Exception as e:
    ChatLiteLLM = None
    logger.warning("langchain_litellm.ChatLiteLLM not importable: %s", e)

# Tools provider (your combined tools.py)
from .tools import tools_for_binding

ENABLE_DEBUG = os.getenv("DEBUG", "false").lower() == "true"
if ENABLE_DEBUG:
    logger.setLevel(logging.DEBUG)


def validate_environment(model_name: str):
    """
    Keep the same quick provider-to-env check you had earlier;
    this is conservative but doesn't exit for Ollama local refs.
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
                    "Missing API Key! Model '%s' requires '%s' in .env",
                    model_name,
                    env_var,
                )
                sys.exit(1)


def _make_litellm(model_name: str, temperature: float = 0.0, max_tokens: int = 2048):
    if ChatLiteLLM is None:
        raise RuntimeError("ChatLiteLLM is not available. Install langchain_litellm.")
    return ChatLiteLLM(
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        verbose=ENABLE_DEBUG,
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
def resilient_invoke(messages: List[Any]):
    """
    Simple LLM invocation (no tool loop). Keeps backward compatibility.
    `messages` expected to be list of SystemMessage/HumanMessage objects (or wrapper's accepted format).
    """
    llm = _make_litellm(
        LLM_MODEL, temperature=LLM_TEMPERATURE, max_tokens=LLM_MAX_TOKENS
    )
    return llm.invoke(messages)


# ---------------- Tool-invocation loop (LLM-agnostic; works with ChatLiteLLM) ---------------

_TOOL_MAP = None


def _build_tool_map():
    """
    Build a name -> callable map from tools_for_binding() descriptors.
    Assumes tools_for_binding() returns [{'name':..., 'fn': callable, ...}, ...]
    """
    global _TOOL_MAP
    if _TOOL_MAP is not None:
        return _TOOL_MAP
    descriptors = tools_for_binding()
    mapping = {}
    for d in descriptors:
        name = d.get("name") or d.get("_tool_name")
        fn = d.get("fn") or d.get("callable") or d.get("function")
        if name and callable(fn):
            mapping[name] = fn
    _TOOL_MAP = mapping
    return _TOOL_MAP


def _try_extract_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Try strict json load, then a safe regex-based extraction of the first JSON object.
    """
    text = text.strip()
    # Quick try: whole text is JSON
    try:
        return json.loads(text)
    except Exception:
        pass
    # Regex: find the first balanced curly block approximate
    m = re.search(r"(\{[\s\S]*\})", text)
    if not m:
        return None
    blob = m.group(1)
    try:
        return json.loads(blob)
    except Exception:
        return None


def invoke_with_tools(messages: List[Any], max_tool_calls: int = 3):
    """
    Call the LLM and execute tool calls the model requests.

    messages: list of SystemMessage/HumanMessage objects (or model-accepted format).
    Behavior:
      1. Call the LLM with messages.
      2. If the model returns JSON containing "tool_call" or "tool_calls", execute them (using your tools.py functions).
      3. Append tool responses to the conversation as assistant messages and re-call the LLM.
      4. Repeat until no more tool calls or max_tool_calls reached.
    """
    llm = _make_litellm(
        LLM_MODEL, temperature=LLM_TEMPERATURE, max_tokens=LLM_MAX_TOKENS
    )
    tool_map = _build_tool_map()

    conversation = list(messages)  # shallow copy to append to

    tool_calls_done = 0
    while True:
        # Invoke the model
        logger.debug(
            "[invoke_with_tools] invoking LLM (tool_calls_done=%s)", tool_calls_done
        )
        resp = llm.invoke(conversation)
        content = getattr(resp, "content", resp) if resp is not None else ""
        logger.debug("[invoke_with_tools] model output: %s", str(content)[:1000])

        # Try to parse JSON from the response
        parsed = _try_extract_json(str(content))
        if not parsed:
            # No JSON → treat as final answer
            # append model response and return
            conversation.append(resp)
            return resp

        # If JSON contains tool call(s), prepare list
        calls = []
        if "tool_call" in parsed and isinstance(parsed["tool_call"], dict):
            calls = [parsed["tool_call"]]
        elif "tool_calls" in parsed and isinstance(parsed["tool_calls"], list):
            calls = parsed["tool_calls"]
        else:
            # Not a tool-call JSON → final answer
            conversation.append(resp)
            return resp

        # Execute each tool in order
        tool_results_texts = []
        for call in calls:
            if tool_calls_done >= max_tool_calls:
                logger.warning(
                    "Max tool calls reached (%s); stopping further calls.",
                    max_tool_calls,
                )
                break

            name = call.get("name")
            args = call.get("args", {}) or {}
            if name not in tool_map:
                tool_output = {"error": f"unknown tool '{name}'"}
            else:
                try:
                    tool_fn = tool_map[name]
                    tool_output = tool_fn(args)
                except Exception as e:
                    logger.exception("Tool execution error for %s", name)
                    tool_output = {"error": str(e)}

            # Format tool result into a textual assistant message for the next model invocation
            tool_result_text = (
                f"[Tool {name} result] {json.dumps(tool_output, ensure_ascii=False)}"
            )
            tool_results_texts.append(tool_result_text)

            # increment counter
            tool_calls_done += 1

        # Append the model response (the one that asked for tools) and then each tool result as assistant messages
        conversation.append(resp)
        # Wrap tool outputs as assistant messages (we use simple dicts so llm.invoke accepts them)
        for tr in tool_results_texts:
            # Try to create a simple message object matching typical wrappers: {"role":"assistant","content": tr}
            conversation.append({"role": "assistant", "content": tr})

        # Loop: model will be invoked again with the appended tool outputs.
        # If we hit max_tool_calls or no tool results, break and return the last raw response
        if tool_calls_done >= max_tool_calls:
            logger.debug("Reached tool call limit; returning last model response.")
            return resp
        # otherwise, continue loop to allow more tool-driven reasoning


# Expose a simple API similar to before
def invoke(messages: List[Any], use_tools: bool = True, max_tool_calls: int = 3):
    """
    Public entry point: if use_tools is True, runs the tool loop; else simple invocation.
    """
    if use_tools:
        return invoke_with_tools(messages, max_tool_calls=max_tool_calls)
    return resilient_invoke(messages)
