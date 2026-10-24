"""One interface, every model.

Each provider is a tiny HTTP adapter (stdlib only) exposing:

    chat(system: str, messages: list[dict]) -> str

Pick a model with ARMY_MODEL="provider:model", e.g.
    anthropic:claude-sonnet-4-5   openai:gpt-4o-mini   gemini:gemini-2.5-flash
    ollama:llama3.2               deepseek:deepseek-chat  groq:llama-3.3-70b-versatile
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-5",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-2.5-flash",
    "ollama": "llama3.2",
    "deepseek": "deepseek-chat",
    "groq": "llama-3.3-70b-versatile",
    "openrouter": "openrouter/auto",
}


class LLMError(RuntimeError):
    pass


def _post(url: str, payload: dict, headers: dict, timeout: int | None = None) -> dict:
    timeout = timeout or int(os.environ.get("ARMY_TIMEOUT", "180"))
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise LLMError(f"HTTP {e.code} from {url.split('?')[0]}: {e.read().decode()[:500]}") from None
    except urllib.error.URLError as e:
        raise LLMError(f"Could not reach {url.split('?')[0]}: {e.reason}") from None


def _key(env: str) -> str:
    value = os.environ.get(env)
    if not value:
        raise LLMError(f"Set {env} to use this provider.")
    return value


class LLM:
    provider = "base"

    def __init__(self, model: str):
        self.model = model

    def chat(self, system: str, messages: list[dict], **kw) -> str:  # pragma: no cover
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.provider}:{self.model}"


class Anthropic(LLM):
    provider = "anthropic"

    def __init__(self, model: str, max_tokens: int = 4096):
        super().__init__(model)
        self.max_tokens = max_tokens
        self.base = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")

    def chat(self, system, messages, **kw):
        r = _post(
            f"{self.base}/v1/messages",
            {"model": self.model, "max_tokens": self.max_tokens, "system": system, "messages": messages},
            {"x-api-key": _key("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01"},
        )
        return "".join(b.get("text", "") for b in r.get("content", []) if b.get("type") == "text")


class OpenAICompatible(LLM):
    """OpenAI and every OpenAI-compatible server (Ollama, DeepSeek, Groq, OpenRouter, vLLM...)."""

    def __init__(self, model: str, provider: str, base_url: str, key_env: str | None):
        super().__init__(model)
        self.provider = provider
        self.base = base_url.rstrip("/")
        self.key_env = key_env

    def chat(self, system, messages, **kw):
        headers = {"authorization": f"Bearer {_key(self.key_env)}"} if self.key_env else {}
        payload = {"model": self.model, "messages": [{"role": "system", "content": system}, *messages]}
        if kw.get("json_mode") and (self.provider == "ollama" or os.environ.get("ARMY_JSON_MODE") == "1"):
            payload["response_format"] = {"type": "json_object"}  # constrained decoding: always-valid JSON
        r = _post(f"{self.base}/chat/completions", payload, headers)
        return r["choices"][0]["message"].get("content") or ""


class Gemini(LLM):
    provider = "gemini"

    def chat(self, system, messages, **kw):
        contents = [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in messages
        ]
        r = _post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            {"systemInstruction": {"parts": [{"text": system}]}, "contents": contents},
            {"x-goog-api-key": _key("GEMINI_API_KEY")},
        )
        parts = r.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)


class Mock(LLM):
    """Scripted model for tests and offline demos. Records every call."""

    provider = "mock"

    def __init__(self, responses: list[str] | None = None):
        super().__init__("scripted")
        self.responses = list(responses or [])
        self.calls: list[tuple[str, list[dict]]] = []

    def chat(self, system, messages, **kw):
        self.calls.append((system, [dict(m) for m in messages]))
        return self.responses.pop(0) if self.responses else '{"final": "mock answer"}'


_OPENAI_LIKE = {
    "openai": (os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"), "OPENAI_API_KEY"),
    "ollama": (os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"), None),
    "deepseek": ("https://api.deepseek.com/v1", "DEEPSEEK_API_KEY"),
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
}


def _detect() -> str:
    for env, provider in [
        ("ANTHROPIC_API_KEY", "anthropic"),
        ("OPENAI_API_KEY", "openai"),
        ("GEMINI_API_KEY", "gemini"),
        ("DEEPSEEK_API_KEY", "deepseek"),
        ("GROQ_API_KEY", "groq"),
        ("OPENROUTER_API_KEY", "openrouter"),
    ]:
        if os.environ.get(env):
            return provider
    return "ollama"  # no keys at all: assume a local model


def get_llm(spec: str | None = None) -> LLM:
    """Build an LLM from "provider:model" (or ARMY_MODEL, or whatever API key is present)."""
    spec = spec or os.environ.get("ARMY_MODEL") or _detect()
    provider, _, model = spec.partition(":")
    provider = provider.lower().strip()
    if provider == "mock":
        return Mock()
    model = model.strip() or DEFAULT_MODELS.get(provider, "")
    if provider == "anthropic":
        return Anthropic(model)
    if provider == "gemini":
        return Gemini(model)
    if provider in _OPENAI_LIKE:
        base, key_env = _OPENAI_LIKE[provider]
        return OpenAICompatible(model, provider, base, key_env)
    raise LLMError(f"Unknown provider '{provider}'. Use one of: anthropic, gemini, mock, {', '.join(_OPENAI_LIKE)}")
