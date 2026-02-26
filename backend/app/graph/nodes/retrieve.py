from app.graph.state import SolveState


async def retrieve_node(state: SolveState) -> dict:
    """Vector search for related formulas and similar past problems.

    Placeholder: returns empty results. Will be wired to pgvector when
    the embedding service and repositories are created.
    """
    return {
        "related_formulas": [],
        "similar_problems": [],
    }
