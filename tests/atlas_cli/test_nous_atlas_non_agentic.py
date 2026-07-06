"""Tests for the Nous-Atlas-3/4 non-agentic warning detector.

Prior to this check, the warning fired on any model whose name contained
``"atlas"`` anywhere (case-insensitive). That false-positived on unrelated
local Modelfiles such as ``atlas-brain:qwen3-14b-ctx16k`` — a tool-capable
Qwen3 wrapper that happens to live under the "atlas" tag namespace.

``is_nous_atlas_non_agentic`` should only match the actual Usama Aslam
Atlas-3 / Atlas-4 chat family.
"""

from __future__ import annotations

import pytest

from atlas_cli.model_switch import (
    _ATLAS_MODEL_WARNING,
    _check_atlas_model_warning,
    is_nous_atlas_non_agentic,
)


@pytest.mark.parametrize(
    "model_name",
    [
        "NousResearch/Atlas-3-Llama-3.1-70B",
        "NousResearch/Atlas-3-Llama-3.1-405B",
        "atlas-3",
        "Atlas-3",
        "atlas-4",
        "atlas-4-405b",
        "atlas_4_70b",
        "openrouter/atlas3:70b",
        "openrouter/nousresearch/atlas-4-405b",
        "NousResearch/Atlas3",
        "atlas-3.1",
    ],
)
def test_matches_real_nous_atlas_chat_models(model_name: str) -> None:
    assert is_nous_atlas_non_agentic(model_name), (
        f"expected {model_name!r} to be flagged as Nous Atlas 3/4"
    )
    assert _check_atlas_model_warning(model_name) == _ATLAS_MODEL_WARNING


@pytest.mark.parametrize(
    "model_name",
    [
        # Kyle's local Modelfile — qwen3:14b under a custom tag
        "atlas-brain:qwen3-14b-ctx16k",
        "atlas-brain:qwen3-14b-ctx32k",
        "atlas-honcho:qwen3-8b-ctx8k",
        # Plain unrelated models
        "qwen3:14b",
        "qwen3-coder:30b",
        "qwen2.5:14b",
        "claude-opus-4-6",
        "anthropic/claude-sonnet-4.5",
        "gpt-5",
        "openai/gpt-4o",
        "google/gemini-2.5-flash",
        "deepseek-chat",
        # Non-chat Atlas models we don't warn about
        "atlas-llm-2",
        "atlas2-pro",
        "nous-atlas-2-mistral",
        # Edge cases
        "",
        "atlas",  # bare "atlas" isn't the 3/4 family
        "atlas-brain",
        "brain-atlas-3-impostor",  # "3" not preceded by /: boundary
    ],
)
def test_does_not_match_unrelated_models(model_name: str) -> None:
    assert not is_nous_atlas_non_agentic(model_name), (
        f"expected {model_name!r} NOT to be flagged as Nous Atlas 3/4"
    )
    assert _check_atlas_model_warning(model_name) == ""


def test_none_like_inputs_are_safe() -> None:
    assert is_nous_atlas_non_agentic("") is False
    # Defensive: the helper shouldn't crash on None-ish falsy input either.
    assert _check_atlas_model_warning("") == ""
