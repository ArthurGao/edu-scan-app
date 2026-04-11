"""Tests for LangSmith observability configuration fields on Settings."""
import os
from unittest.mock import patch

from app.config import Settings


def test_langsmith_config_defaults_to_disabled():
    """With no env vars set, tracing must be off and endpoint blank."""
    with patch.dict(os.environ, {}, clear=True):
        s = Settings(_env_file=None)
        assert s.langsmith_tracing is False
        assert s.langsmith_api_key == ""
        assert s.langsmith_project == "eduscan"
        assert s.langsmith_endpoint == ""
        assert s.langsmith_sampling_rate == 1.0


def test_langsmith_config_reads_env():
    env = {
        "LANGSMITH_TRACING": "true",
        "LANGSMITH_API_KEY": "ls__fake",
        "LANGSMITH_PROJECT": "eduscan-test",
        "LANGSMITH_ENDPOINT": "https://eu.api.smith.langchain.com",
        "LANGSMITH_SAMPLING_RATE": "0.25",
    }
    with patch.dict(os.environ, env, clear=True):
        s = Settings(_env_file=None)
        assert s.langsmith_tracing is True
        assert s.langsmith_api_key == "ls__fake"
        assert s.langsmith_project == "eduscan-test"
        assert s.langsmith_endpoint == "https://eu.api.smith.langchain.com"
        assert s.langsmith_sampling_rate == 0.25
