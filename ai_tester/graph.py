# graph.py
from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import analyze_codebase, plan_tests, generate_tests, run_tests_and_report
from .tools import (
    file_reader_tool,
    file_list_tool,
    cost_estimator_tool,
    model_runner_tool,
)
from .logger import logger
from .llm import invoke_with_tools

"""
This graph supports two interaction patterns:
1) Planner/tool_dispatcher loop (backwards compatible): planner returns pending_tool -> dispatcher executes tool.
2) Agentic LLM with bound tools: call_model node will send message list to LLM; if the LLM uses tools (via bind_tools),
   those tools will be executed internally and the model's response will come back enriched. The model can be instructed
   to use a maximum number of tool calls via prompt instruction (see nodes.plan_tests prompt).
"""


# Simple dispatcher (keeps previous behaviour)
def tool_dispatcher(state: AgentState) -> AgentState:
    pending = state.get("pending_tool")
    if not pending:
        return {}

    name = pending.get("name")
    args = pending.get("args", {})
    logger.info(f"[tool_dispatcher] executing tool: {name}")

    tool_map = {
        "file_reader": file_reader_tool,
        "file_list": file_list_tool,
        "cost_estimator": cost_estimator_tool,
        "model_runner": model_runner_tool,
    }

    tool_fn = tool_map.get(name)
    if not tool_fn:
        return {"tool_response": {"error": f"unknown tool {name}"}}

    result = tool_fn(args)
    return {"tool_response": result, "last_tool_name": name}


# Agent node that calls the llm (and uses bound tools if available)
def call_model_node(state: AgentState) -> AgentState:
    """
    This node expects state["messages"] to be a list of message objects compatible with your LLM client.
    It calls invoke_with_tools() which will delegate to the bound model when available.
    The returned response is appended as the last message for the state.
    """
    messages = state.get("messages", [])
    if not messages:
        return {}

    logger.info("[agent] invoking LLM (with tools if bound)...")
    try:
        llm_response = invoke_with_tools(messages)
    except Exception as e:
        return {"llm_error": str(e)}

    # normalize response object (many wrappers return object with .content)
    content = (
        getattr(llm_response, "content", llm_response)
        if llm_response is not None
        else ""
    )
    # Save raw llm output
    state_copy = {"llm_output": str(content)}
    # append to messages list for further nodes or for tool_dispatcher to inspect if needed
    # In many wrappers, tool-calls are handled internally; if not, planner should set pending_tool
    return {"messages": messages + [llm_response], **state_copy}


def build_graph():
    workflow = StateGraph(AgentState)

    # Core nodes
    workflow.add_node("analyzer", analyze_codebase)
    workflow.add_node("planner", plan_tests)
    workflow.add_node("tool_dispatcher", tool_dispatcher)
    workflow.add_node("agent", call_model_node)  # enables model-with-tools loop if used
    workflow.add_node("generator", generate_tests)
    workflow.add_node("runner", run_tests_and_report)

    workflow.set_entry_point("analyzer")

    # Flow: analyzer -> planner -> agent (for bound-model flows)
    # planner may set pending_tool for dispatcher. We route through dispatcher too to support both patterns.
    workflow.add_edge("analyzer", "planner")
    workflow.add_edge("planner", "tool_dispatcher")
    workflow.add_edge(
        "tool_dispatcher", "planner"
    )  # loop back if pending_tool was used
    # also allow planner to call agent (LLM with bound tools)
    workflow.add_edge("planner", "agent")
    workflow.add_edge("agent", "generator")
    workflow.add_edge("generator", "runner")
    workflow.add_edge("runner", END)

    return workflow.compile()
