import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_ocr_node():
    from app.graph.nodes.ocr import ocr_node
    state = {"image_bytes": b"fake_image_data"}
    with patch("app.graph.nodes.ocr.ocr_service") as mock_ocr:
        mock_ocr.extract_text = AsyncMock(return_value="2x + 5 = 15")
        result = await ocr_node(state)
        assert result["ocr_text"] == "2x + 5 = 15"
        assert "ocr_confidence" in result


@pytest.mark.asyncio
async def test_analyze_node():
    from app.graph.nodes.analyze import analyze_node
    state = {
        "ocr_text": "Solve 2x + 5 = 15",
        "grade_level": "middle school",
        "subject": None,
    }
    mock_response = MagicMock()
    mock_response.content = '{"subject": "math", "problem_type": "equation", "difficulty": "easy", "knowledge_points": ["algebra"]}'

    with patch("app.graph.nodes.analyze.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        result = await analyze_node(state)
        assert result["detected_subject"] == "math"
        assert result["problem_type"] == "equation"


@pytest.mark.asyncio
async def test_analyze_node_preserves_user_subject():
    from app.graph.nodes.analyze import analyze_node
    state = {
        "ocr_text": "Solve 2x + 5 = 15",
        "grade_level": "middle school",
        "subject": "physics",
    }
    mock_response = MagicMock()
    mock_response.content = '{"subject": "math", "problem_type": "equation", "difficulty": "easy", "knowledge_points": ["algebra"]}'

    with patch("app.graph.nodes.analyze.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        result = await analyze_node(state)
        assert result["detected_subject"] == "physics"


@pytest.mark.asyncio
async def test_solve_node():
    from app.graph.nodes.solve import solve_node
    state = {
        "ocr_text": "2x + 5 = 15",
        "detected_subject": "math",
        "grade_level": "middle school",
        "preferred_provider": "claude",
        "attempt_count": 0,
        "related_formulas": [],
        "similar_problems": [],
    }
    mock_response = MagicMock()
    mock_response.content = '{"question_type": "equation", "knowledge_points": ["algebra"], "steps": [{"step": 1, "description": "subtract 5", "formula": "", "calculation": "2x = 10"}], "final_answer": "x = 5", "explanation": "test", "tips": "test"}'
    mock_response.usage_metadata = {"input_tokens": 100, "output_tokens": 50}

    with patch("app.graph.nodes.solve.select_llm") as mock_select:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response
        mock_select.return_value = mock_llm
        mock_llm._llm_type = "anthropic"
        mock_llm.model_name = "claude-sonnet"
        result = await solve_node(state)
        assert "solution_parsed" in result
        assert result["solution_parsed"]["final_answer"] == "x = 5"


@pytest.mark.asyncio
async def test_evaluate_node():
    from app.graph.nodes.evaluate import evaluate_node
    state = {
        "ocr_text": "2x + 5 = 15",
        "solution_raw": '{"steps": [], "final_answer": "x = 5"}',
        "detected_subject": "math",
        "grade_level": "middle school",
        "attempt_count": 0,
    }
    mock_response = MagicMock()
    mock_response.content = '{"scores": {"correctness": 0.9}, "overall": 0.9, "issues": [], "pass": true}'

    with patch("app.graph.nodes.evaluate.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        result = await evaluate_node(state)
        assert result["quality_score"] == 0.9
        assert result["attempt_count"] == 1


@pytest.mark.asyncio
async def test_enrich_node():
    from app.graph.nodes.enrich import enrich_node
    state = {
        "solution_parsed": {"question_type": "equation", "steps": [], "final_answer": "x = 5"},
        "related_formulas": [{"id": 1, "name": "Linear Equation"}],
        "difficulty": "easy",
        "quality_score": 0.9,
    }
    result = await enrich_node(state)
    assert result["final_solution"]["related_formulas"] == [{"id": 1, "name": "Linear Equation"}]
    assert result["related_formula_ids"] == [1]
