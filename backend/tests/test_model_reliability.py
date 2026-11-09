"""V1-A — Fiabilisation des modèles IA : targeted tests for model detection, error categorisation and the
pre-flight guard. No GPU, no ComfyUI, no Ollama, no MongoDB connection are required — httpx is mocked.

Covers:
- ComfyUI exception hierarchy (subclasses still caught by `except comfy.ComfyError`).
- `_missing_files` / `verify_ready` pre-flight (ComfyUnreachable vs MissingModel; image/video presets).
- `run()` error categorisation (missing model, workflow error, unreachable, VRAM/OOM, no output).
- Ollama/local-engine error categorisation (`_engine_http_error`).
- `friendly_error` mapping for every category + the budget fallback.
"""
import asyncio

import httpx
import pytest
from unittest.mock import MagicMock


def test_exception_hierarchy():
    from lib import comfy
    from lib.local_engine import LocalEngineError, EngineUnreachable, ModelMissing

    # ComfyUI errors all inherit from ComfyError (existing `except comfy.ComfyError` still catches them).
    for sub in (comfy.ComfyUnreachable, comfy.MissingModel, comfy.WorkflowError, comfy.GenerationError):
        assert issubclass(sub, comfy.ComfyError)
    assert issubclass(comfy.ComfyError, RuntimeError)

    # Local engine errors.
    for sub in (EngineUnreachable, ModelMissing):
        assert issubclass(sub, LocalEngineError)
    assert issubclass(LocalEngineError, RuntimeError)


# ------------------------------------------------------------------ _missing_files (pure logic)

def test_missing_files_image_present():
    from lib import comfy
    s = {**comfy.DEFAULTS}
    lists = {"checkpoints": [s["image_checkpoint"]], "diffusion_models": [], "text_encoders": [], "vae": []}
    assert comfy._missing_files(s, lists, video=False) == []


def test_missing_files_image_absent():
    from lib import comfy
    s = {**comfy.DEFAULTS, "image_checkpoint": "absent.safetensors"}
    lists = {"checkpoints": ["other.safetensors"], "diffusion_models": [], "text_encoders": [], "vae": []}
    assert comfy._missing_files(s, lists, video=False) == ["absent.safetensors"]


def test_missing_files_video_ignores_image_checkpoint():
    """A video render must NOT require the image checkpoint."""
    from lib import comfy
    s = {**comfy.DEFAULTS}  # wan22 preset by default
    # checkpoints empty (image checkpoint absent) but video=True → image checkpoint must not be flagged.
    lists = {
        "checkpoints": [],
        "diffusion_models": [s["video_model"]],
        "text_encoders": [s["video_text_encoder"]],
        "vae": [s["video_vae"]],
    }
    assert comfy._missing_files(s, lists, video=True) == []


def test_missing_files_video_wan22_model_absent():
    from lib import comfy
    s = {**comfy.DEFAULTS}  # wan22
    lists = {
        "checkpoints": [],
        "diffusion_models": [],
        "text_encoders": [s["video_text_encoder"]],
        "vae": [s["video_vae"]],
    }
    miss = comfy._missing_files(s, lists, video=True)
    assert miss == [s["video_model"]]
    assert s["image_checkpoint"] not in miss


def test_missing_files_video_ltxv_uses_checkpoints_pool():
    from lib import comfy
    s = {**comfy.DEFAULTS, "video_preset": "ltxv", "video_model": "ltx-video-2b.safetensors",
         "video_text_encoder": "t5xxl_fp16.safetensors", "video_vae": ""}
    # ltxv model is a checkpoint, not a diffusion model.
    lists = {"checkpoints": ["ltx-video-2b.safetensors"], "diffusion_models": [],
            "text_encoders": ["t5xxl_fp16.safetensors"], "vae": []}
    assert comfy._missing_files(s, lists, video=True) == []
    # missing model
    lists["checkpoints"] = []
    assert comfy._missing_files(s, lists, video=True) == ["ltx-video-2b.safetensors"]


# ------------------------------------------------------------------ _is_missing_model_error

def test_is_missing_model_error():
    from lib import comfy
    assert comfy._is_missing_model_error("value 'flux1-dev-fp8.safetensors' not in list", "") is True
    assert comfy._is_missing_model_error("File not found: wan2.2_ti2v_5B_fp16.safetensors", "") is True
    # A malformed graph / unknown node is NOT a missing-model error.
    assert comfy._is_missing_model_error("class_type not found", "") is False
    assert comfy._is_missing_model_error("some unrelated error", "") is False


# ------------------------------------------------------------------ verify_ready (mocked httpx)

class _Resp:
    def __init__(self, status=200, json_data=None, content=b"", headers=None):
        self.status_code = status
        self._json = json_data
        self.content = content
        self.headers = headers or {"content-type": "application/json"}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=None, response=self)

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


class _Client:
    """Minimal async context-manager client whose .get/.post return canned responses or raise."""
    def __init__(self, get=None, post=None):
        self._get = get
        self._post = post

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url):
        if callable(self._get):
            return self._get(url)
        return _Resp(200, json_data={})

    async def post(self, url, json=None):
        if callable(self._post):
            return self._post(url)
        return _Resp(200, json_data={})


async def test_verify_ready_ok(monkeypatch):
    from lib import comfy
    s = {**comfy.DEFAULTS}
    monkeypatch.setattr(comfy, "_client", lambda timeout=30: _Client(get=lambda u: _Resp(200, json_data={})))

    async def _lists(c, base):
        return {"checkpoints": [s["image_checkpoint"]], "diffusion_models": [], "text_encoders": [], "vae": []}

    monkeypatch.setattr(comfy, "_model_lists", _lists)
    await comfy.verify_ready(s, video=False)  # must not raise


async def test_verify_ready_unreachable(monkeypatch):
    from lib import comfy
    s = {**comfy.DEFAULTS}

    def _raise(url):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(comfy, "_client", lambda timeout=30: _Client(get=_raise))
    with pytest.raises(comfy.ComfyUnreachable):
        await comfy.verify_ready(s, video=False)


async def test_verify_ready_missing_image(monkeypatch):
    from lib import comfy
    s = {**comfy.DEFAULTS, "image_checkpoint": "absent.safetensors"}
    monkeypatch.setattr(comfy, "_client", lambda timeout=30: _Client(get=lambda u: _Resp(200, json_data={})))

    async def _lists(c, base):
        return {"checkpoints": ["other.safetensors"], "diffusion_models": [], "text_encoders": [], "vae": []}

    monkeypatch.setattr(comfy, "_model_lists", _lists)
    with pytest.raises(comfy.MissingModel) as ei:
        await comfy.verify_ready(s, video=False)
    msg = str(ei.value)
    assert "absent.safetensors" in msg
    assert "download-models" in msg


async def test_verify_ready_missing_video_lists_present_models(monkeypatch):
    from lib import comfy
    s = {**comfy.DEFAULTS}  # wan22
    monkeypatch.setattr(comfy, "_client", lambda timeout=30: _Client(get=lambda u: _Resp(200, json_data={})))

    async def _lists(c, base):
        return {"checkpoints": [], "diffusion_models": [], "text_encoders": [s["video_text_encoder"]], "vae": [s["video_vae"]]}

    monkeypatch.setattr(comfy, "_model_lists", _lists)
    with pytest.raises(comfy.MissingModel) as ei:
        await comfy.verify_ready(s, video=True)
    msg = str(ei.value)
    assert s["video_model"] in msg
    # image checkpoint is irrelevant for a video render
    assert s["image_checkpoint"] not in msg
    assert "download-models" in msg


# ------------------------------------------------------------------ run() error categorisation

async def _nosleep(*a, **k):
    return None


async def test_run_missing_model_rejection(monkeypatch):
    from lib import comfy
    s = {**comfy.DEFAULTS}
    monkeypatch.setattr(comfy.asyncio, "sleep", _nosleep)
    detail = {"error": {"message": "prompt_outputs_failed"},
              "node_errors": {"5": {"errors": [{"details": "ckpt_name: value 'flux1-dev-fp8.safetensors' not in list"}]}}}

    def post(url):
        return _Resp(400, json_data=detail)

    monkeypatch.setattr(comfy, "_client", lambda timeout=30: _Client(post=post))
    with pytest.raises(comfy.MissingModel) as ei:
        await comfy.run({"1": {}}, False, s=s)
    assert "flux1-dev-fp8.safetensors" in str(ei.value)


async def test_run_workflow_error(monkeypatch):
    from lib import comfy
    s = {**comfy.DEFAULTS}
    monkeypatch.setattr(comfy.asyncio, "sleep", _nosleep)
    detail = {"error": {"message": "Output list is not a list"},
              "node_errors": {"9": {"errors": [{"message": "Invalid output connection"}]}}}

    def post(url):
        return _Resp(400, json_data=detail)

    monkeypatch.setattr(comfy, "_client", lambda timeout=30: _Client(post=post))
    with pytest.raises(comfy.WorkflowError):
        await comfy.run({"1": {}}, False, s=s)


async def test_run_unreachable(monkeypatch):
    from lib import comfy
    s = {**comfy.DEFAULTS}
    monkeypatch.setattr(comfy.asyncio, "sleep", _nosleep)

    def post(url):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(comfy, "_client", lambda timeout=30: _Client(post=post))
    with pytest.raises(comfy.ComfyUnreachable):
        await comfy.run({"1": {}}, False, s=s)


async def test_run_vram_error(monkeypatch):
    from lib import comfy
    s = {**comfy.DEFAULTS}
    monkeypatch.setattr(comfy.asyncio, "sleep", _nosleep)
    hist = {"p1": {"status": {"status_str": "error",
                              "messages": [("execution_error", {"exception_message": "CUDA out of memory. Tried to allocate 2.00 GiB"})]},
                    "outputs": {}}}

    def post(url):
        return _Resp(200, json_data={"prompt_id": "p1"})

    def get(url):
        if "history" in url:
            return _Resp(200, json_data=hist)
        return _Resp(200, json_data={})

    monkeypatch.setattr(comfy, "_client", lambda timeout=30: _Client(get=get, post=post))
    with pytest.raises(comfy.GenerationError) as ei:
        await comfy.run({"1": {}}, False, s=s)
    assert "VRAM" in str(ei.value)


async def test_run_no_output(monkeypatch):
    from lib import comfy
    s = {**comfy.DEFAULTS}
    monkeypatch.setattr(comfy.asyncio, "sleep", _nosleep)
    hist = {"p1": {"status": {"status_str": "success"}, "outputs": {}}}

    def post(url):
        return _Resp(200, json_data={"prompt_id": "p1"})

    def get(url):
        if "history" in url:
            return _Resp(200, json_data=hist)
        return _Resp(200, json_data={})

    monkeypatch.setattr(comfy, "_client", lambda timeout=30: _Client(get=get, post=post))
    with pytest.raises(comfy.GenerationError) as ei:
        await comfy.run({"1": {}}, False, s=s)
    assert "aucun fichier" in str(ei.value)


# ------------------------------------------------------------------ local engine (Ollama) errors

def test_engine_http_error_missing_ollama():
    from lib.local_engine import _engine_http_error, ModelMissing, DEFAULTS
    s = {**DEFAULTS}
    err = _engine_http_error(s, 404, '{"error":"model \'qwen2.5-coder:14b\' not found, try pulling it first"}')
    assert isinstance(err, ModelMissing)
    assert "ollama pull" in str(err)
    assert "qwen2.5-coder:14b" in str(err)


def test_engine_http_error_missing_lmstudio():
    from lib.local_engine import _engine_http_error, ModelMissing, DEFAULTS
    s = {**DEFAULTS, "kind": "openai", "model": "local-model"}
    err = _engine_http_error(s, 404, "model not found")
    assert isinstance(err, ModelMissing)
    assert "LM Studio" in str(err)


def test_engine_http_error_generic():
    from lib.local_engine import _engine_http_error, LocalEngineError, ModelMissing, DEFAULTS
    s = {**DEFAULTS}
    err = _engine_http_error(s, 500, "Internal Server Error")
    assert isinstance(err, LocalEngineError)
    assert not isinstance(err, ModelMissing)
    assert "500" in str(err)


# ------------------------------------------------------------------ friendly_error mapping

def test_friendly_error_comfy_categories():
    from lib import comfy, llm

    mm = comfy.MissingModel("Modèle(s) ComfyUI manquant(s) : flux1-dev-fp8.safetensors. Lancez download-models.ps1.")
    assert "flux1-dev-fp8.safetensors" in llm.friendly_error(mm)
    assert "download-models" in llm.friendly_error(mm)

    cu = comfy.ComfyUnreachable("ComfyUI injoignable à http://127.0.0.1:8188. Lancez ComfyUI …")
    assert "injoignable" in llm.friendly_error(cu)

    we = comfy.WorkflowError("ComfyUI a refusé le workflow : nœud inconnu")
    assert "refusé" in llm.friendly_error(we)

    ge = comfy.GenerationError("VRAM insuffisante pour ce rendu (CUDA out of memory).")
    assert "VRAM" in llm.friendly_error(ge)


def test_friendly_error_local_engine():
    from lib import llm
    from lib.local_engine import ModelMissing, EngineUnreachable
    om = ModelMissing("Modèle de texte « qwen2.5-coder:14b » absent du serveur. Téléchargez-le : ollama pull qwen2.5-coder:14b.")
    assert "ollama pull" in llm.friendly_error(om)
    eu = EngineUnreachable("Moteur local injoignable à http://localhost:11434.")
    assert "injoignable" in llm.friendly_error(eu)


def test_friendly_error_budget_and_generic():
    from lib import llm
    assert "Solde" in llm.friendly_error(RuntimeError("insufficient credits 402"))
    assert "boom" in llm.friendly_error(RuntimeError("boom"))
