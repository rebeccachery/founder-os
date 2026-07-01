import json
import os
from typing import Any

import httpx

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"


class LlmError(Exception):
    pass


def _openai_api_key() -> str | None:
    return os.getenv("OPENAI_API_KEY") or None


def _anthropic_api_key() -> str | None:
    return os.getenv("ANTHROPIC_API_KEY") or None


def ollama_base_url(override: str | None = None) -> str:
    return (override or os.getenv("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL).rstrip("/")


def ollama_root_url(base_url: str | None = None) -> str:
    base = ollama_base_url(base_url)
    if base.endswith("/v1"):
        return base[:-3].rstrip("/")
    return base


def _parse_json_content(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise LlmError("Response did not contain JSON")
    return json.loads(text[start : end + 1])


def is_ollama_available(base_url: str | None = None) -> bool:
    root = ollama_root_url(base_url)
    try:
        with httpx.Client(timeout=3.0) as client:
            response = client.get(f"{root}/api/tags")
            return response.status_code == 200
    except httpx.HTTPError:
        return False


def is_llm_available(provider: str | None = None, base_url: str | None = None) -> bool:
    chosen = (provider or os.getenv("LLM_PROVIDER", "ollama")).lower()
    if chosen == "anthropic":
        return bool(_anthropic_api_key())
    if chosen == "ollama":
        return is_ollama_available(base_url)
    if chosen == "openai":
        return bool(_openai_api_key())
    return False


def chat_json(
    *,
    system: str,
    user: str,
    model: str,
    provider: str = "ollama",
    temperature: float = 0.7,
    base_url: str | None = None,
) -> dict[str, Any]:
    provider = provider.lower()
    if provider == "anthropic":
        return _anthropic_chat_json(system, user, model, temperature)
    if provider == "ollama":
        return _ollama_chat_json(system, user, model, temperature, base_url=base_url)
    return _openai_chat_json(system, user, model, temperature)


def _ollama_chat_json(
    system: str,
    user: str,
    model: str,
    temperature: float,
    *,
    base_url: str | None = None,
) -> dict[str, Any]:
    if not is_ollama_available(base_url):
        raise LlmError(
            "Ollama is not running. Start it with: ollama serve "
            f"(expected at {ollama_root_url(base_url)})"
        )

    api_base = ollama_base_url(base_url)
    user_prompt = f"{user}\n\nRespond with valid JSON only."

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{api_base}/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "model": model,
                    "temperature": temperature,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_prompt},
                    ],
                    "format": "json",
                },
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise LlmError(f"Ollama request failed: {exc}") from exc

    content = payload["choices"][0]["message"]["content"]
    return _parse_json_content(content)


def _openai_chat_json(
    system: str,
    user: str,
    model: str,
    temperature: float,
) -> dict[str, Any]:
    api_key = _openai_api_key()
    if not api_key:
        raise LlmError("OPENAI_API_KEY is not set")

    try:
        with httpx.Client(timeout=90.0) as client:
            response = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "temperature": temperature,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise LlmError(f"OpenAI request failed: {exc}") from exc

    content = payload["choices"][0]["message"]["content"]
    return json.loads(content)


def _anthropic_chat_json(
    system: str,
    user: str,
    model: str,
    temperature: float,
) -> dict[str, Any]:
    api_key = _anthropic_api_key()
    if not api_key:
        raise LlmError("ANTHROPIC_API_KEY is not set")

    user_prompt = f"{user}\n\nRespond with valid JSON only."
    try:
        with httpx.Client(timeout=90.0) as client:
            response = client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": 4096,
                    "temperature": temperature,
                    "system": system,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise LlmError(f"Anthropic request failed: {exc}") from exc

    content = payload["content"][0]["text"]
    return _parse_json_content(content)
