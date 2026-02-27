from langgraph.graph import StateGraph, START, END
from app.graph.state import SolveState
from app.graph.nodes import (
    ocr_node, analyze_node, retrieve_node,
    solve_node, enrich_node, quick_verify_node,
)
from app.graph.edges import should_retry_after_verify


def build_solve_graph():
    """Build and compile the main problem-solving graph.

    Pipeline:
        OCR → ANALYZE → RETRIEVE → SOLVE → QUICK_VERIFY → (conditional) → ENRICH → END
                                      ↑                          |
                                      └── retry (different model) ┘
    """
    graph = StateGraph(SolveState)

    graph.add_node("ocr", ocr_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("solve", solve_node)
    graph.add_node("quick_verify", quick_verify_node)
    graph.add_node("enrich", enrich_node)

    graph.add_edge(START, "ocr")
    graph.add_edge("ocr", "analyze")
    graph.add_edge("analyze", "retrieve")
    graph.add_edge("retrieve", "solve")
    graph.add_edge("solve", "quick_verify")

    graph.add_conditional_edges(
        "quick_verify",
        should_retry_after_verify,
        {
            "enrich": "enrich",
            "solve": "solve",
            "caution": "enrich",
        },
    )

    graph.add_edge("enrich", END)

    return graph.compile()


solve_graph = build_solve_graph()
