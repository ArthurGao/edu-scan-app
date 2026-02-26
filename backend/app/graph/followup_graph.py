from langgraph.graph import StateGraph, START, END
from app.graph.state import FollowUpState
from app.llm.registry import get_llm
from app.llm.prompts.followup import build_followup_messages


async def build_context_node(state: FollowUpState) -> dict:
    """Build conversation context from history."""
    history = state.get("conversation_history", [])
    return {"conversation_history": history}


async def generate_reply_node(state: FollowUpState) -> dict:
    """Generate reply to follow-up question."""
    llm = get_llm("strong")
    messages = build_followup_messages(
        conversation_history=state.get("conversation_history", []),
        user_message=state.get("user_message", ""),
        subject=state.get("subject", "math"),
        grade_level=state.get("grade_level", "middle school"),
    )
    result = await llm.ainvoke(messages)
    usage = result.usage_metadata or {}
    return {
        "reply": result.content,
        "tokens_used": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
    }


def build_followup_graph():
    """Build and compile the follow-up conversation graph."""
    graph = StateGraph(FollowUpState)

    graph.add_node("build_context", build_context_node)
    graph.add_node("generate_reply", generate_reply_node)

    graph.add_edge(START, "build_context")
    graph.add_edge("build_context", "generate_reply")
    graph.add_edge("generate_reply", END)

    return graph.compile()


followup_graph = build_followup_graph()
