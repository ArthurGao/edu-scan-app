from langgraph.graph import StateGraph, START, END
from app.graph.state import SolveState
from app.graph.nodes import (
    ocr_node, analyze_node, retrieve_node,
    solve_node, evaluate_node, enrich_node,
)
from app.graph.edges import should_retry


def build_solve_graph():
    """Build and compile the main problem-solving graph."""
    graph = StateGraph(SolveState)

    graph.add_node("ocr", ocr_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("solve", solve_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("enrich", enrich_node)

    graph.add_edge(START, "ocr")
    graph.add_edge("ocr", "analyze")
    graph.add_edge("analyze", "retrieve")
    graph.add_edge("retrieve", "solve")
    graph.add_edge("solve", "evaluate")

    graph.add_conditional_edges(
        "evaluate",
        should_retry,
        {
            "enrich": "enrich",
            "retry": "solve",
            "fallback": "enrich",
        },
    )

    graph.add_edge("enrich", END)

    return graph.compile()


solve_graph = build_solve_graph()
