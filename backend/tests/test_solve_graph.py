import pytest
from app.graph.edges import should_retry


def test_should_retry_passes_when_quality_high():
    state = {"quality_score": 0.85, "attempt_count": 1}
    assert should_retry(state) == "enrich"


def test_should_retry_retries_when_quality_low():
    state = {"quality_score": 0.5, "attempt_count": 1}
    assert should_retry(state) == "retry"


def test_should_retry_fallbacks_after_max_attempts():
    state = {"quality_score": 0.3, "attempt_count": 3}
    assert should_retry(state) == "fallback"


def test_solve_graph_compiles():
    from app.graph.solve_graph import build_solve_graph
    graph = build_solve_graph()
    assert graph is not None
    assert hasattr(graph, "ainvoke")


def test_followup_graph_compiles():
    from app.graph.followup_graph import build_followup_graph
    graph = build_followup_graph()
    assert graph is not None
    assert hasattr(graph, "ainvoke")
