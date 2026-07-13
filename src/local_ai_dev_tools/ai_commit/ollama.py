"""Ollama library invocation."""

import ollama

NUM_PREDICT = 256


class OllamaError(RuntimeError):
    """Raised when Ollama cannot generate a message."""


def generate_commit_message(prompt: str, model: str) -> str:
    """Generate a commit message with the configured Ollama model."""
    try:
        response = ollama.generate(
            model=model,
            prompt=prompt,
            options={"num_predict": NUM_PREDICT},
        )
    except ollama.ResponseError as exc:
        raise OllamaError(f"ollama failed: {exc}") from exc
    except ollama.RequestError as exc:
        raise OllamaError(f"ollama request failed: {exc}") from exc
    except ConnectionError as exc:
        raise OllamaError(f"ollama connection failed: {exc}") from exc

    output = response["response"].strip()
    if not output:
        raise OllamaError("ollama returned an empty commit message")
    return output
