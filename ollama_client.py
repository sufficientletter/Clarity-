"""Ollama client for local LLM chat."""

import json
import urllib.request
import urllib.error


OLLAMA_BASE_URL = "http://localhost:11434"


def check_ollama_running() -> bool:
    """Check if Ollama is running locally."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


def list_models() -> list[str]:
    """List available local models."""
    try:
        req = urllib.request.Request(f"{OLLAMA_BASE_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return []


def check_model_available(model: str) -> bool:
    """Check if a specific model is downloaded."""
    models = list_models()
    # Match exactly or by base name (e.g. "gemma3:12b" matches "gemma3:12b")
    return any(model == m or model == m.split(":")[0] for m in models)


def chat_stream(model: str, messages: list[dict], system: str = "") -> str:
    """Send a chat request to Ollama and stream the response.

    Args:
        model: Model name (e.g. "gemma3:12b")
        messages: List of {"role": "user"|"assistant", "content": "..."}
        system: System prompt

    Yields characters as they arrive, returns the full response.
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }

    if system:
        # Prepend system message
        payload["messages"] = [{"role": "system", "content": system}] + payload["messages"]

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    full_response = []
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            for line in resp:
                if not line.strip():
                    continue
                chunk = json.loads(line)
                token = chunk.get("message", {}).get("content", "")
                if token:
                    full_response.append(token)
                    yield token
                if chunk.get("done"):
                    break
    except urllib.error.URLError as e:
        raise ConnectionError(f"Failed to connect to Ollama: {e}")

    return "".join(full_response)


def chat(model: str, messages: list[dict], system: str = "") -> str:
    """Send a chat request to Ollama and return the full response (non-streaming)."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }

    if system:
        payload["messages"] = [{"role": "system", "content": system}] + payload["messages"]

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read())
            return result.get("message", {}).get("content", "")
    except urllib.error.URLError as e:
        raise ConnectionError(f"Failed to connect to Ollama: {e}")
