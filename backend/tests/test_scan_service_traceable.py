"""Tests verifying ScanService entry points are wrapped with @traceable."""
import inspect

from app.services.scan_service import ScanService


def test_scan_and_solve_is_traceable():
    fn = ScanService.scan_and_solve
    assert getattr(fn, "__langsmith_traceable__", False) is True, (
        "ScanService.scan_and_solve must be wrapped with @traceable"
    )
    assert inspect.unwrap(fn) is not fn


def test_scan_and_solve_stream_is_traceable():
    fn = ScanService.scan_and_solve_stream
    assert getattr(fn, "__langsmith_traceable__", False) is True
    assert inspect.unwrap(fn) is not fn
