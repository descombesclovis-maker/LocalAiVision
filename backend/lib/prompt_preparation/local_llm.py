"""Optional local-only analyzer: one request, no cloud fallback, no model download.

Existing local-engine settings are read lazily only for an enabled preparation.
The config is frozen for the request; no second settings read after endpoint validation.
"""
from dataclasses import dataclass
from ipaddress import ip_address
from urllib.parse import urlsplit

import httpx


class NonLocalEndpoint(ValueError):
    pass


@dataclass(frozen=True)
class LocalLLMConfig:
    kind: str
    base_url: str
    model: str
    num_ctx: int = 16384


def validate_local_endpoint(url: str) -> str:
    if not isinstance(url, str) or any(char.isspace() for char in url):
        raise NonLocalEndpoint("Only loopback HTTP(S) endpoints are allowed")
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        local = host == "localhost" or ip_address(host).is_loopback
        port = parts.port  # Validate malformed/out-of-range ports before any HTTP client.
        valid = parts.scheme in ("http", "https") and local and not (
            parts.username is not None or parts.password is not None
            or "?" in url or "#" in url or parts.netloc.endswith(":")
        ) and (port is None or 1 <= port <= 65535)
    except ValueError:
        valid = False
    if not valid:
        raise NonLocalEndpoint("Only loopback HTTP(S) endpoints are allowed")
    return url.rstrip("/")


class LocalAnalyzer:
    def __init__(self, config: LocalLLMConfig | None = None):
        self.config = config

    async def __call__(self, system: str, prompt: str) -> str:
        config = self.config
        if config is None:
            # Existing configuration/model, never select/download a new model.
            from lib.local_engine import get_settings
            settings = await get_settings()
            config = LocalLLMConfig(settings["kind"], settings["base_url"], settings["model"], settings["num_ctx"])
        base = validate_local_endpoint(config.base_url)
        if (
            config.kind not in ("ollama", "openai") or not isinstance(config.model, str)
            or not config.model or config.model != config.model.strip()
            or type(config.num_ctx) is not int or config.num_ctx <= 0
        ):
            raise ValueError("Unsupported local engine configuration")
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        if config.kind == "ollama":
            endpoint = f"{base}/api/chat"
            body = {
                "model": config.model, "messages": messages, "stream": False, "format": "json",
                "options": {"num_ctx": config.num_ctx, "num_predict": 4096, "temperature": 0},
            }
        else:
            endpoint = f"{base}/chat/completions"
            # Do not require response_format / a JSON-mode extension from compatible servers.
            body = {"model": config.model, "messages": messages, "stream": False, "max_tokens": 4096, "temperature": 0}
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(35, connect=3), trust_env=False, follow_redirects=False,
        ) as client:
            response = await client.post(endpoint, json=body)
            response.raise_for_status()
            data = response.json()
        text = data["message"]["content"] if config.kind == "ollama" else data["choices"][0]["message"]["content"]
        if not isinstance(text, str):
            raise ValueError("Local LLM returned no text")
        return text
