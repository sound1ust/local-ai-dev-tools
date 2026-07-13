from typing import Any

import ollama
import pytest

from local_ai_dev_tools.ai_commit.ollama import (
    NUM_PREDICT,
    OllamaError,
    generate_commit_message,
)


def test_ollama_generate_uses_supplied_model(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_generate(**kwargs: Any) -> dict[str, str]:
        calls.append(kwargs)
        return {"response": "message"}

    monkeypatch.setattr(ollama, "generate", fake_generate)

    assert generate_commit_message("prompt", "qwen2.5-coder:14b") == "message"
    assert calls == [
        {
            "model": "qwen2.5-coder:14b",
            "prompt": "prompt",
            "options": {"num_predict": NUM_PREDICT},
        }
    ]


def test_ollama_reports_response_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_generate(**kwargs: Any) -> dict[str, str]:
        raise ollama.ResponseError("model missing")

    monkeypatch.setattr(ollama, "generate", fake_generate)

    with pytest.raises(OllamaError, match="model missing"):
        generate_commit_message("prompt", "custom-model")


def test_ollama_reports_request_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_generate(**kwargs: Any) -> dict[str, str]:
        raise ollama.RequestError("server unavailable")

    monkeypatch.setattr(ollama, "generate", fake_generate)

    with pytest.raises(OllamaError, match="server unavailable"):
        generate_commit_message("prompt", "custom-model")


def test_ollama_reports_empty_output(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_generate(**kwargs: Any) -> dict[str, str]:
        return {"response": ""}

    monkeypatch.setattr(ollama, "generate", fake_generate)

    with pytest.raises(OllamaError, match="empty"):
        generate_commit_message("prompt", "custom-model")
