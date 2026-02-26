from app.graph.state import SolveState


async def enrich_node(state: SolveState) -> dict:
    """Attach formula references, tips, and metadata to the solution."""
    solution = dict(state.get("solution_parsed", {}))
    solution["related_formulas"] = state.get("related_formulas", [])
    solution["difficulty"] = state.get("difficulty", "medium")
    solution["quality_score"] = state.get("quality_score", 0)

    formula_ids = [f["id"] for f in state.get("related_formulas", []) if "id" in f]

    return {
        "final_solution": solution,
        "related_formula_ids": formula_ids,
    }
