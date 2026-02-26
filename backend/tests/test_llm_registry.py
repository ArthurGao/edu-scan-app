import pytest
from app.llm.registry import get_llm, select_llm, LLM_REGISTRY, MODEL_CONFIG


def test_registry_has_all_providers():
    assert "claude" in LLM_REGISTRY
    assert "openai" in LLM_REGISTRY
    assert "gemini" in LLM_REGISTRY


def test_model_config_has_tiers():
    for provider in LLM_REGISTRY:
        assert "strong" in MODEL_CONFIG[provider]
        assert "fast" in MODEL_CONFIG[provider]


def test_get_llm_returns_chat_model():
    llm = get_llm("fast", "openai")
    assert llm is not None
    assert hasattr(llm, "ainvoke")


def test_select_llm_uses_subject_mapping():
    llm = select_llm(preferred=None, subject="math", attempt=0)
    assert "claude" in str(type(llm)).lower() or "anthropic" in str(type(llm)).lower()


def test_select_llm_rotates_on_retry():
    llm_0 = select_llm(preferred="claude", subject="math", attempt=0)
    llm_1 = select_llm(preferred="claude", subject="math", attempt=1)
    assert type(llm_0) != type(llm_1)


def test_select_llm_respects_preferred():
    llm = select_llm(preferred="openai", subject="math", attempt=0)
    assert "openai" in str(type(llm)).lower()
