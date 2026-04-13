"""Observability helpers — LangSmith integration.

All LangSmith interaction flows through this package so that services
never import ``langsmith`` directly and fail-open behavior is centralized.
"""
