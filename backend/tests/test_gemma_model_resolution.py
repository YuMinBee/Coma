import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.gemma_analyzer import _find_available_model


def test_preferred_gemma_model_wins():
    models = [
        {"name": "gemma3:4b", "model": "gemma3:4b"},
        {"name": "gemma2:2b", "model": "gemma2:2b"},
    ]

    assert _find_available_model(models, "gemma2:2b") == "gemma2:2b"


def test_any_gemma_model_is_used_when_preferred_is_missing():
    models = [
        {"name": "llama3.2:3b", "model": "llama3.2:3b"},
        {"name": "gemma3:4b", "model": "gemma3:4b"},
    ]

    assert _find_available_model(models, "gemma2:2b") == "gemma3:4b"


def test_non_gemma_models_are_not_selected():
    models = [
        {"name": "llama3.2:3b", "model": "llama3.2:3b"},
        {"name": "mistral:7b", "model": "mistral:7b"},
    ]

    assert _find_available_model(models, "gemma2:2b") is None


if __name__ == "__main__":
    test_preferred_gemma_model_wins()
    test_any_gemma_model_is_used_when_preferred_is_missing()
    test_non_gemma_models_are_not_selected()
    print("gemma model resolution tests passed")
