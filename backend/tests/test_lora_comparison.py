from lib.lora_comparison import build_controlled_workflows, comparison_cache_key, comparison_manifest
from lib import comfy


def identity(**overrides):
    values = dict(model="sdxl", checkpoint="sd_xl_base_1.0.safetensors", checkpoint_sha256=None,
                  prompt="PRDCT white sneaker on a white studio background", seed=42,
                  width=1024, height=1024, steps=25, cfg=7.5, sampler="dpmpp_2m",
                  scheduler="karras", lora_filename="sdxl-product-photography-shoaibism.safetensors",
                  lora_sha256="772797c56b396c60e246e3329609c091ba88ea764a7709f31dfce5461da180ba",
                  lora_strength=1.0)
    return {**values, **overrides}


def test_controlled_comparison_cache_key_is_stable_and_changes_with_any_material_setting():
    original = identity()
    assert comparison_cache_key(original) == comparison_cache_key(identity())
    assert comparison_cache_key(original) != comparison_cache_key(identity(seed=43))
    assert comparison_cache_key(original) != comparison_cache_key(identity(lora_strength=0.8))
    assert comparison_cache_key(original) != comparison_cache_key(identity(prompt="different prompt"))


def test_workflow_pair_has_identical_sampling_inputs_and_lora_only_on_treatment():
    settings = {**comfy.DEFAULTS, "image_preset": "sdxl", "image_checkpoint": comfy.IMAGE_PRESETS["sdxl"]["checkpoint"]}
    base, with_lora = build_controlled_workflows(settings, prompt="PRDCT white sneaker", seed=42,
        width=1024, height=1024, lora_filename="sdxl-product-photography-shoaibism.safetensors", lora_strength=1.0)
    sample = lambda wf: next(n["inputs"] for n in wf.values() if n["class_type"] == "KSampler")
    a, b = sample(base), sample(with_lora)
    for key in ("seed", "steps", "cfg", "sampler_name", "scheduler", "denoise", "latent_image", "positive", "negative"):
        assert a[key] == b[key]
    assert not any(n["class_type"] == "LoraLoader" for n in base.values())
    assert any(n["class_type"] == "LoraLoader" and n["inputs"]["strength_model"] == 1.0 for n in with_lora.values())


def test_comparison_manifest_declares_only_lora_as_treatment_difference():
    spec = identity()
    manifest = comparison_manifest(spec)
    assert manifest["outputs"]["baseline"]["lora"] is None
    assert manifest["outputs"]["treatment"]["lora"] == spec["lora_filename"]
    assert manifest["identity"]["prompt"] == spec["prompt"]
    assert manifest["visual_validation"] == "not_generated"
