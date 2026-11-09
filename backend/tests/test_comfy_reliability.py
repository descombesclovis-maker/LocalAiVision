"""V1-C — Fiabilisation des générations ComfyUI.

Targeted tests for:
  1. _choices() returns None on error (not []) — distinguishes unavailable list from empty list.
  2. _missing_files() skips checks when a list is None — no false-positive «model missing».
  3. verify_ready() raises ModelListUnavailable when any list is None (not MissingModel).
  4. verify_ready() raises MissingModel only when the list IS available AND the model IS absent.
  5. generate_image() / generate_video() do NOT call verify_ready() (double-check removed).
  6. media.py _comfy_image / _run_comfy_video call verify_ready() exactly once.
  7. Custom workflow preservation — _fill() substitutes placeholders without altering logic.
  8. All generation parameters (CFG, steps, sampler, resolution, seed, etc.) are unchanged.
  9. New exception hierarchy: ModelListUnavailable is a subclass of ComfyError.
  10. Diagnostics: distinct error messages for each failure mode.

SIMULATION NOTICE: All tests use mocked HTTP clients and canned responses.
No GPU, no real ComfyUI instance, no real model files are used or required.
Results cannot be interpreted as real-hardware generation tests.
"""
import asyncio
import inspect
from pathlib import Path

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]


# ------------------------------------------------------------------ helpers

class _Resp:
    def __init__(self, status=200, json_data=None, content=b"", headers=None):
        self.status_code = status
        self._json = json_data
        self.content = content
        self.headers = headers or {"content-type": "application/json"}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=MagicMock(), response=self)

    def json(self):
        if self._json is None:
            raise ValueError("no json body")
        return self._json


class _Client:
    """Minimal async context-manager client returning canned responses or raising."""
    def __init__(self, get=None, post=None):
        self._get = get
        self._post = post

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, **kwargs):
        if callable(self._get):
            return self._get(url)
        return _Resp(200, json_data={})

    async def post(self, url, **kwargs):
        if callable(self._post):
            return self._post(url)
        return _Resp(200, json_data={})


async def _nosleep(*a, **k):
    pass


# ------------------------------------------------------------------ 1. _choices() returns None on error

class TestChoicesNullOnError:
    """V1-C: _choices must return None (not []) when the request fails."""

    @pytest.mark.asyncio
    async def test_choices_returns_none_on_connection_error(self):
        from lib import comfy

        class _ErrClient:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return None
            async def get(self, url):
                raise ConnectionRefusedError("ComfyUI not running")

        result = await comfy._choices(_ErrClient(), "http://127.0.0.1:8188", "CheckpointLoaderSimple", "ckpt_name")
        assert result is None, "Expected None (list unavailable), not []"

    @pytest.mark.asyncio
    async def test_choices_returns_none_on_http_error(self):
        from lib import comfy

        class _ErrClient:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return None
            async def get(self, url):
                r = _Resp(500)
                r.raise_for_status()

        result = await comfy._choices(_ErrClient(), "http://127.0.0.1:8188", "CheckpointLoaderSimple", "ckpt_name")
        assert result is None

    @pytest.mark.asyncio
    async def test_choices_returns_empty_list_when_comfyui_has_no_models(self):
        """[] means ComfyUI responded but has 0 models in that category — not an error."""
        from lib import comfy

        class _OkClient:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return None
            async def get(self, url):
                node = url.split("/")[-1]
                return _Resp(200, json_data={node: {"input": {"required": {"ckpt_name": [[]]}}}})

        result = await comfy._choices(_OkClient(), "http://127.0.0.1:8188", "CheckpointLoaderSimple", "ckpt_name")
        assert result == [], "An empty list from ComfyUI should be [] not None"

    @pytest.mark.asyncio
    async def test_choices_returns_list_when_models_present(self):
        from lib import comfy

        class _OkClient:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return None
            async def get(self, url):
                node = url.split("/")[-1]
                return _Resp(200, json_data={node: {"input": {"required": {"ckpt_name": [["model_a.safetensors", "model_b.safetensors"]]}}}})

        result = await comfy._choices(_OkClient(), "http://127.0.0.1:8188", "CheckpointLoaderSimple", "ckpt_name")
        assert result == ["model_a.safetensors", "model_b.safetensors"]


# ------------------------------------------------------------------ 2. _missing_files() with None lists

class TestMissingFilesWithNoneLists:
    """V1-C: _missing_files must skip checks for None lists — no false «model missing» diagnostic."""

    def test_none_list_does_not_trigger_missing(self):
        from lib import comfy
        s = {**comfy.DEFAULTS}
        # All lists are None (list unavailable) — no model should be reported missing.
        lists = {"checkpoints": None, "diffusion_models": None, "text_encoders": None, "vae": None}
        missing = comfy._missing_files(s, lists, video=False)
        assert missing == [], (
            "When checkpoints list is None (unavailable), the image checkpoint must NOT be reported missing. "
            "A None list means we could not get the information — not that the model is absent."
        )

    def test_none_video_lists_no_false_positive(self):
        from lib import comfy
        s = {**comfy.DEFAULTS}
        lists = {"checkpoints": None, "diffusion_models": None, "text_encoders": None, "vae": None}
        missing = comfy._missing_files(s, lists, video=True)
        assert missing == []

    def test_empty_list_still_triggers_missing(self):
        """[] (ComfyUI has no models) should still report absence — that's a real missing model."""
        from lib import comfy
        s = {**comfy.DEFAULTS, "image_checkpoint": "absent.safetensors"}
        lists = {"checkpoints": [], "diffusion_models": [], "text_encoders": [], "vae": []}
        missing = comfy._missing_files(s, lists, video=False)
        assert "absent.safetensors" in missing

    def test_present_in_list_no_missing(self):
        from lib import comfy
        s = {**comfy.DEFAULTS}
        lists = {
            "checkpoints": [s["image_checkpoint"]],
            "diffusion_models": [s["video_model"]],
            "text_encoders": [s["video_text_encoder"]],
            "vae": [s["video_vae"]],
        }
        assert comfy._missing_files(s, lists, video=False) == []
        assert comfy._missing_files(s, lists, video=True) == []

    def test_mixed_none_and_present(self):
        """A list can be None for one category and a valid list for another."""
        from lib import comfy
        s = {**comfy.DEFAULTS}
        # checkpoints is None → skip check; text_encoders is [] → would report missing (but not checked for image)
        lists = {"checkpoints": None, "diffusion_models": [], "text_encoders": [], "vae": None}
        # For image (only checkpoints checked): None → skip
        assert comfy._missing_files(s, lists, video=False) == []


# ------------------------------------------------------------------ 3 & 4. verify_ready() with None lists

class TestVerifyReadyListUnavailable:
    """V1-C: verify_ready raises ModelListUnavailable when a required list is None."""

    @pytest.mark.asyncio
    async def test_raises_model_list_unavailable_when_object_info_fails(self, monkeypatch):
        from lib import comfy
        s = {**comfy.DEFAULTS}
        monkeypatch.setattr(comfy, "_client", lambda timeout=30: _Client(get=lambda u: _Resp(200, json_data={})))

        async def _lists_with_none(c, base):
            return {"checkpoints": None, "diffusion_models": None, "text_encoders": None, "vae": None}

        monkeypatch.setattr(comfy, "_model_lists", _lists_with_none)
        with pytest.raises(comfy.ModelListUnavailable) as ei:
            await comfy.verify_ready(s, video=False)
        msg = str(ei.value)
        assert "inaccessible" in msg
        assert "object_info" in msg

    @pytest.mark.asyncio
    async def test_raises_missing_model_only_when_list_available_and_model_absent(self, monkeypatch):
        from lib import comfy
        s = {**comfy.DEFAULTS, "image_checkpoint": "absent.safetensors"}
        monkeypatch.setattr(comfy, "_client", lambda timeout=30: _Client(get=lambda u: _Resp(200, json_data={})))

        async def _lists_available(c, base):
            return {"checkpoints": ["other.safetensors"], "diffusion_models": [], "text_encoders": [], "vae": []}

        monkeypatch.setattr(comfy, "_model_lists", _lists_available)
        with pytest.raises(comfy.MissingModel) as ei:
            await comfy.verify_ready(s, video=False)
        assert "absent.safetensors" in str(ei.value)

    @pytest.mark.asyncio
    async def test_no_raise_when_model_present(self, monkeypatch):
        from lib import comfy
        s = {**comfy.DEFAULTS}
        monkeypatch.setattr(comfy, "_client", lambda timeout=30: _Client(get=lambda u: _Resp(200, json_data={})))

        async def _lists_present(c, base):
            return {
                "checkpoints": [s["image_checkpoint"]],
                "diffusion_models": [s["video_model"]],
                "text_encoders": [s["video_text_encoder"]],
                "vae": [s["video_vae"]],
            }

        monkeypatch.setattr(comfy, "_model_lists", _lists_present)
        await comfy.verify_ready(s, video=False)  # must not raise
        await comfy.verify_ready(s, video=True)   # must not raise

    @pytest.mark.asyncio
    async def test_unreachable_raises_comfy_unreachable(self, monkeypatch):
        from lib import comfy
        s = {**comfy.DEFAULTS}

        def _raise(url):
            raise httpx.ConnectError("refused")

        monkeypatch.setattr(comfy, "_client", lambda timeout=30: _Client(get=_raise))
        with pytest.raises(comfy.ComfyUnreachable):
            await comfy.verify_ready(s)

    @pytest.mark.asyncio
    async def test_model_list_unavailable_is_not_missing_model(self, monkeypatch):
        """ModelListUnavailable must NOT be confused with MissingModel — they are distinct types."""
        from lib import comfy
        # Type hierarchy check (no async needed, but kept for consistency).
        assert issubclass(comfy.ModelListUnavailable, comfy.ComfyError), (
            "ModelListUnavailable must be a ComfyError so existing 'except comfy.ComfyError' catches it."
        )
        assert not issubclass(comfy.ModelListUnavailable, comfy.MissingModel), (
            "ModelListUnavailable and MissingModel must be distinct types."
        )
        assert not issubclass(comfy.MissingModel, comfy.ModelListUnavailable)

        # verify_ready raises ModelListUnavailable (not MissingModel) when lists are None.
        s = {**comfy.DEFAULTS}
        monkeypatch.setattr(comfy, "_client", lambda timeout=30: _Client(get=lambda u: _Resp(200, json_data={})))

        async def _lists_none(c, base):
            return {"checkpoints": None, "diffusion_models": None, "text_encoders": None, "vae": None}

        monkeypatch.setattr(comfy, "_model_lists", _lists_none)
        with pytest.raises(comfy.ModelListUnavailable):
            await comfy.verify_ready(s)


# ------------------------------------------------------------------ 5. No double verify_ready in generate_*

class TestNoDoubleVerify:
    """V1-C: generate_image() and generate_video() must NOT call verify_ready()."""

    def test_generate_image_does_not_call_verify_ready(self):
        from lib import comfy
        import ast, textwrap
        src = inspect.getsource(comfy.generate_image)
        # Parse the AST to find actual verify_ready() calls, not just docstring mentions.
        tree = ast.parse(textwrap.dedent(src))
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(getattr(node.func, "attr", None) or node.func, ast.Attribute)
            and getattr(node.func, "attr", "") == "verify_ready"
        ]
        assert len(calls) == 0, (
            "generate_image() must not call verify_ready() — this is done by media.py before the GPU slot. "
            "Calling it twice was a V1-C regression risk."
        )

    def test_generate_video_does_not_call_verify_ready(self):
        from lib import comfy
        import ast, textwrap
        src = inspect.getsource(comfy.generate_video)
        tree = ast.parse(textwrap.dedent(src))
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(getattr(node.func, "attr", None) or node.func, ast.Attribute)
            and getattr(node.func, "attr", "") == "verify_ready"
        ]
        assert len(calls) == 0, (
            "generate_video() must not call verify_ready() — this is done by media.py."
        )

    def test_media_py_still_calls_verify_ready(self):
        """media.py must still call verify_ready() — that's the authoritative single call."""
        media_src = (ROOT / "backend" / "routers" / "media.py").read_text()
        assert "verify_ready" in media_src, "media.py must call verify_ready()"
        assert media_src.count("verify_ready") >= 2, (
            "media.py should call verify_ready for both image (_comfy_image) and video (_run_comfy_video)"
        )

    def test_verify_ready_call_count_per_generation_is_one(self):
        """Each function (_comfy_image, _run_comfy_video) calls verify_ready exactly once."""
        import ast
        media_src = (ROOT / "backend" / "routers" / "media.py").read_text()
        # Count actual verify_ready() call expressions (not comments or imports).
        tree = ast.parse(media_src)
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Attribute) and node.func.attr == "verify_ready")
                or (isinstance(node.func, ast.Name) and node.func.id == "verify_ready")
            )
        ]
        assert len(calls) == 2, (
            f"Expected exactly 2 verify_ready calls in media.py (one for image, one for video), "
            f"found {len(calls)}. Each generation path must check exactly once."
        )


# ------------------------------------------------------------------ 6. Generation parameter preservation

class TestGenerationParamsPreserved:
    """V1-C must not alter any generation parameter."""

    def test_image_workflow_cfg_steps_sampler_unchanged(self):
        from lib import comfy
        s = {**comfy.DEFAULTS}
        wf = comfy._image_workflow(s, "test prompt", 1024, 1024, 42, None)
        ks = wf["5"]["inputs"]
        # FLUX dev: 22 steps, cfg 1.0, euler sampler, simple scheduler
        assert ks["steps"] == 22
        assert ks["cfg"] == 1.0
        assert ks["sampler_name"] == "euler"
        assert ks["scheduler"] == "simple"

    def test_image_workflow_schnell_params_unchanged(self):
        from lib import comfy
        s = {**comfy.DEFAULTS, "image_preset": "flux-schnell", "image_checkpoint": "flux1-schnell-fp8.safetensors"}
        wf = comfy._image_workflow(s, "test", 1344, 768, 1, None)
        ks = wf["5"]["inputs"]
        # FLUX schnell: 4 steps, cfg 1.0
        assert ks["steps"] == 4
        assert ks["cfg"] == 1.0

    def test_image_workflow_sdxl_params_unchanged(self):
        from lib import comfy
        s = {**comfy.DEFAULTS, "image_preset": "sdxl", "image_checkpoint": "sd_xl_base_1.0.safetensors"}
        wf = comfy._image_workflow(s, "test", 1024, 1024, 1, None)
        ks = wf["5"]["inputs"]
        assert ks["steps"] == 30
        assert ks["cfg"] == 6.5
        assert ks["sampler_name"] == "dpmpp_2m"
        assert ks["scheduler"] == "karras"

    def test_video_workflow_wan22_params_unchanged(self):
        from lib import comfy
        s = {**comfy.DEFAULTS}
        wf = comfy._video_workflow(s, "test", 832, 480, 73, 1, None)
        ks = wf["9"]["inputs"]
        assert ks["steps"] == 30
        assert ks["cfg"] == 5.0
        assert ks["sampler_name"] == "uni_pc"

    def test_video_lengths_unchanged(self):
        from lib import comfy
        assert comfy.VIDEO_LENGTHS["3"] == 73
        assert comfy.VIDEO_LENGTHS["5"] == 121

    def test_image_sizes_unchanged(self):
        from lib import comfy
        assert comfy.IMAGE_SIZES["1:1"] == (1024, 1024)
        assert comfy.IMAGE_SIZES["16:9"] == (1344, 768)
        assert comfy.IMAGE_SIZES["9:16"] == (768, 1344)

    def test_video_sizes_unchanged(self):
        from lib import comfy
        assert comfy.VIDEO_SIZES["16:9"] == (832, 480)
        assert comfy.VIDEO_SIZES["9:16"] == (480, 832)

    def test_defaults_unchanged(self):
        from lib import comfy
        assert comfy.DEFAULTS["image_preset"] == "flux-dev"
        assert comfy.DEFAULTS["image_checkpoint"] == "flux1-dev-fp8.safetensors"
        assert comfy.DEFAULTS["video_preset"] == "wan22"
        assert comfy.DEFAULTS["video_model"] == "wan2.2_ti2v_5B_fp16.safetensors"

    def test_no_model_deletion(self):
        """The code must not delete model files — verify no file-deletion calls related to models."""
        comfy_src = (ROOT / "backend" / "lib" / "comfy.py").read_text()
        # No shutil.rmtree, os.remove, Path.unlink calls targeting model directories.
        assert "shutil.rmtree" not in comfy_src
        # unlink is acceptable only for .boot_token cleanup (in auth.py), not in comfy.py.
        assert "unlink" not in comfy_src

    def test_no_automatic_download(self):
        """The code must not trigger model downloads automatically."""
        comfy_src = (ROOT / "backend" / "lib" / "comfy.py").read_text()
        # No urllib, requests.get to a model hosting URL, no subprocess calling wget/curl for models.
        import re
        # Check for download-related patterns that would indicate auto-downloading.
        assert not re.search(r"urllib\.request\.urlretrieve", comfy_src)
        assert not re.search(r"requests\.get\s*\(.*huggingface", comfy_src, re.I)
        assert not re.search(r"subprocess.*wget|subprocess.*curl", comfy_src, re.I)


# ------------------------------------------------------------------ 7. Custom workflow preservation

class TestCustomWorkflow:
    """Custom workflows must work without modification."""

    def test_fill_substitutes_placeholders(self):
        from lib import comfy
        wf = {"node": {"inputs": {"text": "{{PROMPT}}", "seed": "{{SEED}}", "w": "{{WIDTH}}"}}}
        result = comfy._fill(wf, {"PROMPT": "a cat", "SEED": 42, "WIDTH": 1024})
        assert result["node"]["inputs"]["text"] == "a cat"
        assert result["node"]["inputs"]["seed"] == 42
        assert result["node"]["inputs"]["w"] == 1024

    def test_fill_preserves_native_types_for_exact_placeholders(self):
        """A node value that IS the placeholder keeps the native Python type."""
        from lib import comfy
        wf = {"5": {"inputs": {"seed": "{{SEED}}", "steps": "{{WIDTH}}"}}}
        result = comfy._fill(wf, {"SEED": 12345, "WIDTH": 1024})
        assert result["5"]["inputs"]["seed"] == 12345
        assert isinstance(result["5"]["inputs"]["seed"], int)

    def test_fill_does_not_alter_non_placeholder_values(self):
        from lib import comfy
        wf = {"node": {"inputs": {"sampler": "euler", "cfg": 3.5, "steps": 30}}}
        result = comfy._fill(wf, {"PROMPT": "test"})
        assert result["node"]["inputs"]["sampler"] == "euler"
        assert result["node"]["inputs"]["cfg"] == 3.5
        assert result["node"]["inputs"]["steps"] == 30

    @pytest.mark.asyncio
    async def test_custom_image_workflow_used_when_set(self, monkeypatch):
        """When custom_image_workflow is set, it must be used instead of the built-in workflow."""
        from lib import comfy
        import json

        custom_wf = json.dumps({"1": {"class_type": "CustomNode", "inputs": {"prompt": "{{PROMPT}}"}}})
        s = {**comfy.DEFAULTS, "custom_image_workflow": custom_wf}

        captured = {}

        async def _mock_run(wf, video, progress=None, on_queued=None, s=None):
            captured["wf"] = wf
            return b"fake-image-data", "image/png"

        async def _mock_get_settings():
            return s

        monkeypatch.setattr(comfy, "run", _mock_run)
        monkeypatch.setattr(comfy, "get_settings", _mock_get_settings)

        await comfy.generate_image("a cat")
        assert "1" in captured["wf"]
        assert captured["wf"]["1"]["class_type"] == "CustomNode"


# ------------------------------------------------------------------ 8. Diagnostic messages

class TestDiagnosticMessages:
    """Error messages must clearly identify the failure mode."""

    @pytest.mark.asyncio
    async def test_unreachable_message_contains_url(self, monkeypatch):
        from lib import comfy
        s = {**comfy.DEFAULTS, "base_url": "http://127.0.0.1:8188"}

        def _raise(url):
            raise httpx.ConnectError("refused")

        monkeypatch.setattr(comfy, "_client", lambda timeout=30: _Client(get=_raise))
        with pytest.raises(comfy.ComfyUnreachable) as ei:
            await comfy.verify_ready(s)
        assert "127.0.0.1:8188" in str(ei.value)
        assert "ComfyUI" in str(ei.value)

    @pytest.mark.asyncio
    async def test_list_unavailable_message_identifies_problem(self, monkeypatch):
        from lib import comfy
        s = {**comfy.DEFAULTS}
        monkeypatch.setattr(comfy, "_client", lambda timeout=30: _Client(get=lambda u: _Resp(200, json_data={})))

        async def _null_lists(c, base):
            return {"checkpoints": None, "diffusion_models": None, "text_encoders": None, "vae": None}

        monkeypatch.setattr(comfy, "_model_lists", _null_lists)
        with pytest.raises(comfy.ModelListUnavailable) as ei:
            await comfy.verify_ready(s)
        msg = str(ei.value)
        assert "object_info" in msg
        # Message should tell the user what to do
        assert "démarrage" in msg or "réessayez" in msg

    @pytest.mark.asyncio
    async def test_missing_model_message_names_the_model(self, monkeypatch):
        from lib import comfy
        s = {**comfy.DEFAULTS, "image_checkpoint": "my-missing-model.safetensors"}
        monkeypatch.setattr(comfy, "_client", lambda timeout=30: _Client(get=lambda u: _Resp(200, json_data={})))

        async def _known_lists(c, base):
            return {"checkpoints": ["other.safetensors"], "diffusion_models": [], "text_encoders": [], "vae": []}

        monkeypatch.setattr(comfy, "_model_lists", _known_lists)
        with pytest.raises(comfy.MissingModel) as ei:
            await comfy.verify_ready(s)
        msg = str(ei.value)
        assert "my-missing-model.safetensors" in msg
        assert "download-models" in msg

    def test_vram_error_message_contains_advice(self, monkeypatch):
        from lib import comfy
        ge = comfy.GenerationError(
            "VRAM insuffisante pour ce rendu (CUDA out of memory). Réduisez la résolution."
        )
        assert "VRAM" in str(ge)
        assert "résolution" in str(ge)

    def test_timeout_error_is_generation_error(self):
        """Timeout during generation is a GenerationError (not ComfyUnreachable)."""
        from lib import comfy
        err = comfy.GenerationError(
            "Délai de rendu local dépassé — la carte graphique est peut-être trop lente."
        )
        assert isinstance(err, comfy.ComfyError)
        assert not isinstance(err, comfy.ComfyUnreachable)


# ------------------------------------------------------------------ 9. Exception hierarchy

class TestExceptionHierarchy:
    """All ComfyUI exceptions must remain catchable as comfy.ComfyError."""

    def test_all_errors_inherit_comfy_error(self):
        from lib import comfy
        for cls in (
            comfy.ComfyUnreachable,
            comfy.MissingModel,
            comfy.ModelListUnavailable,
            comfy.WorkflowError,
            comfy.GenerationError,
        ):
            assert issubclass(cls, comfy.ComfyError), f"{cls.__name__} must be a subclass of ComfyError"

    def test_model_list_unavailable_not_missing_model(self):
        """ModelListUnavailable and MissingModel must be distinct types."""
        from lib import comfy
        assert not issubclass(comfy.ModelListUnavailable, comfy.MissingModel)
        assert not issubclass(comfy.MissingModel, comfy.ModelListUnavailable)

    def test_comfy_error_is_runtime_error(self):
        from lib import comfy
        assert issubclass(comfy.ComfyError, RuntimeError)


# ------------------------------------------------------------------ 10. Backward compatibility

class TestBackwardCompatibility:
    """Existing code that catches comfy.ComfyError or comfy.MissingModel must still work."""

    def test_model_list_unavailable_caught_as_comfy_error(self):
        from lib import comfy
        caught = False
        try:
            raise comfy.ModelListUnavailable("list unavailable")
        except comfy.ComfyError:
            caught = True
        assert caught, "ModelListUnavailable must be catchable as ComfyError"

    def test_missing_model_caught_as_comfy_error(self):
        from lib import comfy
        caught = False
        try:
            raise comfy.MissingModel("model absent")
        except comfy.ComfyError:
            caught = True
        assert caught

    def test_verify_ready_signature_unchanged(self):
        """verify_ready must keep its (s, video=False) signature."""
        from lib import comfy
        sig = inspect.signature(comfy.verify_ready)
        params = list(sig.parameters)
        assert "s" in params
        assert "video" in params
        assert sig.parameters["video"].default is False

    def test_generate_image_signature_unchanged(self):
        from lib import comfy
        sig = inspect.signature(comfy.generate_image)
        params = list(sig.parameters)
        assert "prompt" in params
        assert "aspect" in params
        assert "ref" in params
        assert "progress" in params
        assert "on_queued" in params

    def test_generate_video_signature_unchanged(self):
        from lib import comfy
        sig = inspect.signature(comfy.generate_video)
        params = list(sig.parameters)
        assert "prompt" in params
        assert "duration" in params
        assert "aspect" in params

    @pytest.mark.asyncio
    async def test_generate_image_t2i_simulation(self, monkeypatch):
        """Text-to-image generation path simulation (no GPU required).
        SIMULATION: uses mocked HTTP — does not represent real GPU generation."""
        from lib import comfy
        import json

        s = {**comfy.DEFAULTS}
        fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20

        async def _mock_get_settings():
            return s

        async def _mock_run(wf, video, progress=None, on_queued=None, s=None):
            # Verify the workflow uses correct checkpoint
            for node in wf.values():
                if node.get("class_type") == "CheckpointLoaderSimple":
                    assert node["inputs"]["ckpt_name"] == comfy.DEFAULTS["image_checkpoint"]
            return fake_png, "image/png"

        monkeypatch.setattr(comfy, "get_settings", _mock_get_settings)
        monkeypatch.setattr(comfy, "run", _mock_run)

        data, mime = await comfy.generate_image("a beautiful landscape")
        assert data == fake_png
        assert mime == "image/png"

    @pytest.mark.asyncio
    async def test_generate_video_t2v_simulation(self, monkeypatch):
        """Text-to-video (T2V) generation path simulation (no GPU required).
        SIMULATION: uses mocked HTTP — does not represent real GPU generation."""
        from lib import comfy

        s = {**comfy.DEFAULTS}
        fake_mp4 = b"\x00\x00\x00\x18ftyp" + b"\x00" * 20

        async def _mock_get_settings():
            return s

        async def _mock_run(wf, video, progress=None, on_queued=None, s=None):
            assert video is True
            # Wan22 workflow should use UNETLoader
            for node in wf.values():
                if node.get("class_type") == "UNETLoader":
                    assert node["inputs"]["unet_name"] == comfy.DEFAULTS["video_model"]
            return fake_mp4, "video/mp4"

        monkeypatch.setattr(comfy, "get_settings", _mock_get_settings)
        monkeypatch.setattr(comfy, "run", _mock_run)

        data, mime = await comfy.generate_video("a sunset", "3", "16:9")
        assert data == fake_mp4
        assert mime == "video/mp4"

    @pytest.mark.asyncio
    async def test_generate_video_i2v_simulation(self, monkeypatch):
        """Image-to-video (I2V) generation path simulation (no GPU required).
        SIMULATION: uses mocked HTTP — does not represent real GPU generation."""
        from lib import comfy

        s = {**comfy.DEFAULTS}
        fake_mp4 = b"\x00\x00\x00\x18ftyp" + b"\x00" * 20
        fake_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20

        captured = {}

        async def _mock_get_settings():
            return s

        async def _mock_upload(c, base, data, mime):
            captured["uploaded"] = True
            return "uploaded_image.png"

        async def _mock_run(wf, video, progress=None, on_queued=None, s=None):
            # Verify the image reference was injected into the workflow
            assert "10" in wf, "LoadImage node must be present for I2V"
            return fake_mp4, "video/mp4"

        monkeypatch.setattr(comfy, "get_settings", _mock_get_settings)
        monkeypatch.setattr(comfy, "_upload", _mock_upload)
        monkeypatch.setattr(comfy, "run", _mock_run)

        # Mock _client to avoid real HTTP connection for upload
        class _FakeClient:
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return None
        monkeypatch.setattr(comfy, "_client", lambda timeout=30: _FakeClient())

        data, mime = await comfy.generate_video("animate this", "3", "16:9", ref=(fake_image, "image/png"))
        assert data == fake_mp4
        assert captured.get("uploaded"), "Image should have been uploaded for I2V"
