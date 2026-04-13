"""Smoke tests verifying all LLM-consuming service entry points are traced."""
import inspect

import pytest

from app.services.grading_service import GradingService
from app.services.practice_grading_service import PracticeGradingService
from app.services.scan_service import ScanService


@pytest.mark.parametrize(
    "cls, method_name",
    [
        (ScanService, "scan_and_solve"),
        (ScanService, "scan_and_solve_stream"),
        (ScanService, "followup"),
        (PracticeGradingService, "grade_and_save"),
        (GradingService, "grade_session"),
    ],
)
def test_service_entry_point_is_traceable(cls, method_name):
    fn = getattr(cls, method_name)
    assert getattr(fn, "__langsmith_traceable__", False) is True, (
        f"{cls.__name__}.{method_name} must be wrapped with @traceable"
    )
    assert inspect.unwrap(fn) is not fn
