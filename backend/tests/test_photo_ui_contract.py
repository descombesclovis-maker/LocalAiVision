"""V2-E regression guards for the photo UI contract (static checks; the browser flow was run separately).

They protect three behaviours validated in the real browser: the model picker, the per-request preset
and the readable message shown when a window has no session (instead of an empty page).
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_photo_studio_sends_the_selected_preset_and_blocks_only_when_nothing_is_installed():
    vision = _read("frontend/src/components/vision.tsx")
    assert 'data-testid="photo-preset-picker"' in vision
    assert "comfy_preset: model === \"comfy\" ? choice : null" in vision
    assert "(model === \"comfy\" && noneInstalled)" in vision
    # a null (unknown) state must not be treated as missing
    assert "m.installed !== false" in vision


def test_bootstrap_only_blocks_on_explicit_refusal_and_shows_a_message():
    main = _read("frontend/src/main.tsx")
    assert "denied = res.status === 401 || res.status === 403;" in main
    assert "data-testid=\"session-required\"" in main
    assert "root.render(<SessionRequired />)" in main


def test_image_model_status_route_is_registered_before_the_generic_presets_route():
    engines = _read("backend/routers/engines.py")
    assert '"/settings/comfyui/image-models"' in engines
    assert engines.index("/settings/comfyui/image-models") < engines.index("/settings/comfyui/presets")
