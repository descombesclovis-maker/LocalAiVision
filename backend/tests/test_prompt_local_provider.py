"""V2-A: offline contracts of the optional local-only LLM analyzer.

`lib.prompt_preparation.local_llm` is the only component of the new package that could
reach the network, so every exchange here goes through `httpx.MockTransport`: no socket is
opened, no Ollama / LM Studio / OpenAI-compatible server is required, no model is listed,
pulled or downloaded. These tests pin what may leave the machine (exactly one loopback
POST per analysis), the two supported local dialects (Ollama native, OpenAI-compatible
without any JSON-mode extension) and the fail-closed behaviour on hostile configuration.
They are provider tests, not engine/corpus or visual-quality tests.
"""
import json
import subprocess
import sys
import types
from pathlib import Path

import httpx
import pytest

from lib.prompt_preparation import (
    COMFY_IMAGE, LocalAnalyzer, LocalLLMConfig, PreparationStatus, prepare_prompt,
)
from lib.prompt_preparation.local_llm import NonLocalEndpoint, validate_local_endpoint

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SYSTEM = "You are a local prompt-understanding component, not a creative writer."
PROMPT = '{"task": "photo", "fidelity_mode": "balanced", "clauses": [{"id": 0, "text": "Un chat roux"}]}'
TEXT = '{"subject": [{"clause": 0, "quote": "Un chat roux"}]}'
OLLAMA_REPLY = (200, {"model": "m", "message": {"role": "assistant", "content": TEXT}, "done": True})
OPENAI_REPLY = (200, {"choices": [{"index": 0, "message": {"role": "assistant", "content": TEXT}}]})


def config(kind="ollama", base_url="http://127.0.0.1:11434", model="qwen2.5-coder:14b", num_ctx=16384):
    return LocalLLMConfig(kind, base_url, model, num_ctx)


class Wire:
    """Socket-free local server: records every exchange and replays canned answers."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.client_kwargs: list[dict] = []
        self._replies: list[object] = []

    def reply(self, *items: object) -> "Wire":
        """Queue answers: a (status, json) tuple, an httpx.Response, or an exception to raise."""
        self._replies.extend(items)
        return self

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        item = self._replies.pop(0) if self._replies else (200, {})
        if isinstance(item, BaseException):
            raise item
        if isinstance(item, tuple):
            status, payload = item
            item = httpx.Response(status, json=payload)
        assert isinstance(item, httpx.Response)
        item.request = request
        return item

    @property
    def bodies(self) -> list[dict]:
        return [json.loads(request.content) for request in self.requests]

    @property
    def paths(self) -> list[str]:
        return [request.url.path for request in self.requests]

    @property
    def hosts(self) -> set:
        return {request.url.host for request in self.requests}


@pytest.fixture
def wire(monkeypatch) -> Wire:
    """Force every httpx client built by the provider onto a MockTransport."""
    from lib.prompt_preparation import local_llm

    recorder = Wire()
    real_client = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        recorder.client_kwargs.append(dict(kwargs))
        # The injected transport is the only one used: a real socket can never be opened.
        return real_client(*args, **kwargs, transport=httpx.MockTransport(recorder._handle))

    monkeypatch.setattr(local_llm.httpx, "AsyncClient", client_factory)
    return recorder


@pytest.fixture
def settings(monkeypatch):
    """Replace the lazily imported `lib.local_engine.get_settings` (no DB, no Motor)."""
    source = types.SimpleNamespace(reads=0, values=dict(
        kind="ollama", base_url="http://127.0.0.1:11434", model="qwen2.5:7b", num_ctx=8192,
    ), error=None)

    async def get_settings():
        source.reads += 1
        if source.error is not None:
            raise source.error
        return dict(source.values)

    module = types.ModuleType("lib.local_engine")
    module.get_settings = get_settings
    monkeypatch.setitem(sys.modules, "lib.local_engine", module)
    return source


# --------------------------------------------------------------------------- endpoint guard

@pytest.mark.parametrize("url", [
    "http://localhost:11434",
    "https://localhost:11434",
    "http://LOCALHOST:11434",
    "http://127.0.0.1:11434",
    "http://127.0.0.2:1234",
    "http://[::1]:11434",
    "https://127.0.0.1:8443/v1",
])
def test_loopback_endpoint_is_accepted(url):
    assert validate_local_endpoint(url) == url


@pytest.mark.parametrize("url", [
    "https://api.openai.com/v1",
    "https://api.openai.com/v1/chat/completions",
    "http://192.168.1.10:11434",
    "http://10.0.0.5:11434",
    "http://8.8.8.8:11434",
    "http://0.0.0.0:11434",
    "http://169.254.169.254/latest/meta-data",
    "http://localhost.evil.example:11434",
    "http://localhost.:11434",  # no DNS-name trust beyond the literal "localhost"
    "http://127.0.0.1.nip.io:11434",
    "http://my-desktop:11434",
])
def test_non_loopback_endpoint_is_rejected(url):
    with pytest.raises(NonLocalEndpoint):
        validate_local_endpoint(url)


@pytest.mark.parametrize("url", [
    "http://user:secret@127.0.0.1:11434",
    "http://user@127.0.0.1:11434",
    "http://@127.0.0.1:11434",
    "http://127.0.0.1:11434/?",
    "http://127.0.0.1:11434/#",
    "http://127.0.0.1:11434/?token=1",
    "http://127.0.0.1:11434/#fragment",
])
def test_credentials_query_or_fragment_are_rejected(url):
    with pytest.raises(NonLocalEndpoint):
        validate_local_endpoint(url)


@pytest.mark.parametrize("url", [
    "ftp://127.0.0.1:11434",
    "file://127.0.0.1/etc/passwd",
    "ws://127.0.0.1:11434",
    "//127.0.0.1:11434",
    "localhost:11434",
    "127.0.0.1:11434",
    "/api/chat",
    "",
])
def test_unsafe_scheme_or_relative_url_is_rejected(url):
    with pytest.raises(NonLocalEndpoint):
        validate_local_endpoint(url)


@pytest.mark.parametrize("host", ["2130706433", "127.1", "0x7f.0.0.1", "0177.0.0.1", "127.0.0.1."])
def test_alternate_ip_encoding_is_rejected(host):
    """Numeric shorthands resolve to loopback in some resolvers: refused, never trusted."""
    with pytest.raises(NonLocalEndpoint):
        validate_local_endpoint(f"http://{host}:11434")


def test_ipv4_mapped_ipv6_loopback_is_refused():
    """Documented fail-closed gap: ::ffff:127.0.0.1 is local but `is_loopback` is False."""
    with pytest.raises(NonLocalEndpoint):
        validate_local_endpoint("http://[::ffff:127.0.0.1]:11434")


def test_trailing_slashes_are_removed_and_a_path_prefix_is_kept():
    assert validate_local_endpoint("http://127.0.0.1:11434/") == "http://127.0.0.1:11434"
    assert validate_local_endpoint("http://127.0.0.1:8080/v1//") == "http://127.0.0.1:8080/v1"


@pytest.mark.parametrize("bad", [None, b"http://127.0.0.1:11434", 42])
def test_non_string_url_fails_closed(bad):
    """A malformed setting must be refused, never handed to the HTTP layer."""
    with pytest.raises(NonLocalEndpoint):
        validate_local_endpoint(bad)


# ------------------------------------------------------------------------- request contract

async def test_ollama_native_dialect(wire):
    wire.reply(OLLAMA_REPLY)
    text = await LocalAnalyzer(config())(SYSTEM, PROMPT)

    assert text == TEXT
    assert len(wire.requests) == 1
    request, body = wire.requests[0], wire.bodies[0]
    assert request.method == "POST"
    assert str(request.url) == "http://127.0.0.1:11434/api/chat"
    assert request.headers["content-type"] == "application/json"
    assert set(body) == {"model", "messages", "stream", "format", "options"}
    assert body["model"] == "qwen2.5-coder:14b"
    assert body["stream"] is False
    assert body["format"] == "json"
    assert body["options"] == {"num_ctx": 16384, "num_predict": 4096, "temperature": 0}
    assert body["messages"] == [
        {"role": "system", "content": SYSTEM}, {"role": "user", "content": PROMPT},
    ]


async def test_openai_compatible_dialect_requests_no_json_mode_extension(wire):
    wire.reply(OPENAI_REPLY)
    text = await LocalAnalyzer(config("openai", "http://127.0.0.1:1234", "local-model"))(SYSTEM, PROMPT)

    assert text == TEXT
    assert len(wire.requests) == 1
    request, body = wire.requests[0], wire.bodies[0]
    assert str(request.url) == "http://127.0.0.1:1234/chat/completions"
    assert request.headers["content-type"] == "application/json"
    assert set(body) == {"model", "messages", "stream", "max_tokens", "temperature"}
    assert body["stream"] is False
    assert body["max_tokens"] == 4096
    assert body["temperature"] == 0
    # Bare compatible servers (LM Studio, llama.cpp, vLLM) need not implement JSON mode.
    assert "response_format" not in body
    assert "options" not in body and "format" not in body


async def test_client_is_hardened_against_proxies_redirects_and_credentials(wire, monkeypatch):
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
        monkeypatch.setenv(name, "http://proxy.invalid:3128")
    for name in ("OPENAI_API_KEY", "OLLAMA_HOST"):
        monkeypatch.setenv(name, "must-never-be-sent")
    wire.reply(OPENAI_REPLY)
    await LocalAnalyzer(config("openai", "http://127.0.0.1:1234", "local-model"))(SYSTEM, PROMPT)

    (kwargs,) = wire.client_kwargs
    assert kwargs["trust_env"] is False  # environment proxies/CA settings are ignored
    assert kwargs["follow_redirects"] is False
    assert kwargs["timeout"] == httpx.Timeout(35, connect=3)
    request = wire.requests[0]
    assert "authorization" not in request.headers  # no API key is invented or leaked
    assert "proxy-authorization" not in request.headers
    assert wire.hosts == {"127.0.0.1"}


@pytest.mark.parametrize("base_url,kind,expected", [
    ("http://127.0.0.1:11434", "ollama", "http://127.0.0.1:11434/api/chat"),
    ("http://localhost:11434/", "ollama", "http://localhost:11434/api/chat"),
    ("http://localhost:1234/v1", "openai", "http://localhost:1234/v1/chat/completions"),
    ("http://localhost:1234/v1//", "openai", "http://localhost:1234/v1/chat/completions"),
    ("https://127.0.0.1:8443", "openai", "https://127.0.0.1:8443/chat/completions"),
])
async def test_base_url_forms_resolve_to_a_single_slash_endpoint(wire, base_url, kind, expected):
    wire.reply(OLLAMA_REPLY if kind == "ollama" else OPENAI_REPLY)
    await LocalAnalyzer(config(kind, base_url, "local-model"))(SYSTEM, PROMPT)
    assert [str(request.url) for request in wire.requests] == [expected]


async def test_exactly_one_post_per_call_and_no_discovery_or_download(wire):
    wire.reply(OLLAMA_REPLY, OPENAI_REPLY)
    await LocalAnalyzer(config())(SYSTEM, PROMPT)
    await LocalAnalyzer(config("openai", "http://127.0.0.1:1234", "local-model"))(SYSTEM, PROMPT)

    assert [request.method for request in wire.requests] == ["POST", "POST"]
    assert wire.paths == ["/api/chat", "/chat/completions"]
    forbidden = {"/api/tags", "/api/pull", "/api/push", "/api/show", "/models", "/v1/models"}
    assert not forbidden.intersection(wire.paths)


async def test_payload_is_sent_verbatim_including_non_ascii(wire):
    system = "Règle n°1 : ne jamais traduire « l'original » — 电影 🎬"
    prompt = '{"clauses": [{"id": 0, "text": "Un chat roux à côté d’une fenêtre — 电影 🎬"}]}'
    wire.reply(OLLAMA_REPLY)
    await LocalAnalyzer(config())(system, prompt)
    assert wire.bodies[0]["messages"] == [
        {"role": "system", "content": system}, {"role": "user", "content": prompt},
    ]


async def test_response_text_is_returned_verbatim(wire):
    """The provider must not trim, repair or unwrap the model answer: the engine validates it."""
    fenced = '  ```json\n{"subject": []}\n```  \n'
    wire.reply((200, {"message": {"content": fenced}}))
    assert await LocalAnalyzer(config())(SYSTEM, PROMPT) == fenced


async def test_empty_content_is_returned_without_invention(wire):
    wire.reply((200, {"choices": [{"message": {"content": ""}}]}))
    assert await LocalAnalyzer(config("openai", "http://127.0.0.1:1234", "m"))(SYSTEM, PROMPT) == ""
    assert len(wire.requests) == 1


# ------------------------------------------------------------- configuration fails closed

@pytest.mark.parametrize("kind", ["lmstudio", "Ollama", "OLLAMA", "anthropic", "", "ollama "])
async def test_unsupported_kind_never_reaches_the_network(wire, kind):
    with pytest.raises(ValueError, match="Unsupported local engine configuration"):
        await LocalAnalyzer(config(kind))(SYSTEM, PROMPT)
    assert wire.requests == [] and wire.client_kwargs == []


@pytest.mark.parametrize("model", ["", " ", "\n\t ", "   \n"])
async def test_blank_model_never_reaches_the_network(wire, model):
    with pytest.raises(ValueError, match="Unsupported local engine configuration"):
        await LocalAnalyzer(config(model=model))(SYSTEM, PROMPT)
    assert wire.requests == [] and wire.client_kwargs == []


@pytest.mark.parametrize("model", [None, 42])
async def test_non_string_model_fails_closed(wire, model):
    with pytest.raises((AttributeError, TypeError, ValueError)):
        await LocalAnalyzer(config(model=model))(SYSTEM, PROMPT)
    assert wire.requests == [] and wire.client_kwargs == []


async def test_remote_endpoint_never_creates_an_http_client(wire):
    """The central guarantee: the prompt is not sent anywhere but loopback."""
    with pytest.raises(NonLocalEndpoint):
        await LocalAnalyzer(config("openai", "https://api.openai.com/v1", "gpt-4o-mini"))(SYSTEM, PROMPT)
    assert wire.client_kwargs == []
    assert wire.requests == []


async def test_endpoint_guard_precedes_kind_validation(wire):
    """A remote URL is reported as non-local, never masked by a configuration error."""
    with pytest.raises(NonLocalEndpoint):
        await LocalAnalyzer(config("lmstudio", "http://10.1.2.3:11434", "m"))(SYSTEM, PROMPT)
    assert wire.client_kwargs == []


@pytest.mark.parametrize("port", ["abc", "99999", "0", ""])
async def test_malformed_port_fails_closed_before_client_creation(wire, port):
    with pytest.raises(NonLocalEndpoint):
        await LocalAnalyzer(config("ollama", f"http://127.0.0.1:{port}", "m"))(SYSTEM, PROMPT)
    assert wire.requests == [] and wire.client_kwargs == []


async def test_num_ctx_is_forwarded_to_ollama_only(wire):
    wire.reply(OLLAMA_REPLY, OPENAI_REPLY)
    await LocalAnalyzer(config(num_ctx=2048))(SYSTEM, PROMPT)
    await LocalAnalyzer(config("openai", "http://127.0.0.1:1234", "m", num_ctx=2048))(SYSTEM, PROMPT)
    assert wire.bodies[0]["options"]["num_ctx"] == 2048
    assert "options" not in wire.bodies[1]


# ------------------------------------------------------------------ lazy local settings

def test_constructor_does_not_read_settings(settings):
    LocalAnalyzer()
    assert settings.reads == 0


async def test_explicit_config_bypasses_settings_entirely(wire, settings):
    settings.error = AssertionError("settings must not be read with an explicit config")
    wire.reply(OLLAMA_REPLY)
    await LocalAnalyzer(config())(SYSTEM, PROMPT)
    assert settings.reads == 0
    assert len(wire.requests) == 1


async def test_settings_are_read_once_and_drive_the_request(wire, settings):
    wire.reply(OLLAMA_REPLY)
    await LocalAnalyzer()(SYSTEM, PROMPT)
    assert settings.reads == 1
    body = wire.bodies[0]
    assert body["model"] == "qwen2.5:7b"
    assert body["options"]["num_ctx"] == 8192
    assert str(wire.requests[0].url) == "http://127.0.0.1:11434/api/chat"


async def test_stored_settings_are_not_trusted_blindly(wire, settings):
    settings.values["base_url"] = "https://api.openai.com/v1"
    settings.values["kind"] = "openai"
    with pytest.raises(NonLocalEndpoint):
        await LocalAnalyzer()(SYSTEM, PROMPT)
    assert settings.reads == 1
    assert wire.client_kwargs == [] and wire.requests == []


async def test_settings_are_not_read_again_after_an_http_failure(wire, settings):
    wire.reply((500, {"error": "boom"}))
    with pytest.raises(httpx.HTTPStatusError):
        await LocalAnalyzer()(SYSTEM, PROMPT)
    assert settings.reads == 1
    assert len(wire.requests) == 1


async def test_settings_failure_never_reaches_the_network(wire, settings):
    settings.error = RuntimeError("database unavailable")
    with pytest.raises(RuntimeError):
        await LocalAnalyzer()(SYSTEM, PROMPT)
    assert settings.reads == 1
    assert wire.client_kwargs == [] and wire.requests == []


async def test_settings_missing_key_fails_closed(wire, settings):
    del settings.values["model"]
    with pytest.raises(KeyError):
        await LocalAnalyzer()(SYSTEM, PROMPT)
    assert wire.client_kwargs == [] and wire.requests == []


# ----------------------------------------------------------------------- response handling

@pytest.mark.parametrize("payload", [
    {"done": True},
    {"message": "not-an-object"},
    {"message": {"content": None}},
    {"message": {"content": 5}},
])
async def test_malformed_ollama_payload_raises(wire, payload):
    wire.reply((200, payload))
    with pytest.raises((KeyError, TypeError, ValueError)):
        await LocalAnalyzer(config())(SYSTEM, PROMPT)
    assert len(wire.requests) == 1


@pytest.mark.parametrize("payload", [
    {"choices": []},
    {"choices": [{}]},
    {"choices": [{"message": {}}]},
    {"choices": [{"message": {"content": 3}}]},
    {"choices": "not-a-list"},
])
async def test_malformed_openai_payload_raises(wire, payload):
    wire.reply((200, payload))
    with pytest.raises((IndexError, KeyError, TypeError, ValueError)):
        await LocalAnalyzer(config("openai", "http://127.0.0.1:1234", "m"))(SYSTEM, PROMPT)
    assert len(wire.requests) == 1


async def test_non_json_body_raises(wire):
    wire.reply(httpx.Response(200, text="<html>captive portal</html>"))
    with pytest.raises(ValueError):  # json.JSONDecodeError
        await LocalAnalyzer(config())(SYSTEM, PROMPT)
    assert len(wire.requests) == 1


@pytest.mark.parametrize("status", [400, 401, 404, 429, 500, 503])
async def test_http_error_is_not_retried(wire, status):
    """404 = model absent locally: it must fail, never trigger a pull or a second attempt."""
    wire.reply((status, {"error": "nope"}))
    with pytest.raises(httpx.HTTPStatusError):
        await LocalAnalyzer(config())(SYSTEM, PROMPT)
    assert len(wire.requests) == 1


async def test_redirect_is_not_followed(wire):
    wire.reply(httpx.Response(307, headers={"location": "https://api.openai.com/v1/chat/completions"}))
    with pytest.raises(httpx.HTTPStatusError):
        await LocalAnalyzer(config("openai", "http://127.0.0.1:1234", "m"))(SYSTEM, PROMPT)
    assert len(wire.requests) == 1
    assert wire.hosts == {"127.0.0.1"}


async def test_connection_error_is_not_retried(wire):
    wire.reply(httpx.ConnectError("connection refused"))
    with pytest.raises(httpx.ConnectError):
        await LocalAnalyzer(config())(SYSTEM, PROMPT)
    assert len(wire.requests) == 1


async def test_timeout_error_is_not_retried(wire):
    wire.reply(httpx.ReadTimeout("read timed out"))
    with pytest.raises(httpx.ReadTimeout):
        await LocalAnalyzer(config())(SYSTEM, PROMPT)
    assert len(wire.requests) == 1


# ------------------------------------------------------------------------ engine boundary

async def test_disabled_by_default_never_calls_the_provider(wire):
    async def forbidden(system, prompt):
        raise AssertionError("no local LLM call is allowed while preparation is disabled")

    result = await prepare_prompt("Un chat roux dort sur un canapé bleu.", analyzer=forbidden)
    assert result.status is PreparationStatus.DISABLED
    assert result.prepared_prompt == result.original_prompt
    assert result.local_llm_used is False
    assert wire.requests == []


async def test_remote_configuration_maps_to_a_fallback_without_any_request(wire):
    result = await prepare_prompt(
        "Un chat roux dort sur un canapé bleu.", enabled=True, capabilities=COMFY_IMAGE,
        analyzer=LocalAnalyzer(config("ollama", "http://192.168.1.50:11434", "m")),
    )
    assert result.status is PreparationStatus.FALLBACK
    assert result.prepared_prompt == result.original_prompt
    assert result.local_llm_used is False
    assert "nonlocal_endpoint" in {item.code for item in result.diagnostics}
    assert wire.client_kwargs == [] and wire.requests == []


# --------------------------------------------------------------------- package isolation

def test_import_does_not_touch_db_settings_or_network():
    """Importing the package (and building an analyzer) must stay side-effect free."""
    code = "\n".join([
        "import sys",
        "import lib.prompt_preparation",
        "from lib.prompt_preparation import LocalAnalyzer",
        "LocalAnalyzer()",
        "assert 'lib.db' not in sys.modules, 'DB layer imported'",
        "assert 'lib.local_engine' not in sys.modules, 'settings module imported'",
        "assert 'motor' not in sys.modules, 'Motor imported'",
        "print('ok')",
    ])
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=BACKEND_ROOT,
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"
