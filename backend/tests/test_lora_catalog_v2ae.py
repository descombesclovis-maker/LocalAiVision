import pytest

from lib import comfy

def test_sdxl_lora_is_applied_to_model_and_clip_and_strength():
    settings = {**comfy.DEFAULTS, "image_preset": "sdxl", "image_checkpoint": comfy.IMAGE_PRESETS["sdxl"]["checkpoint"]}
    wf = comfy._image_workflow(settings, "hiresjewels_style ring", 1024, 1024, 12, None, "jewelry-sdxl-v1.safetensors", 0.65)
    loader = wf["10"]
    assert loader["class_type"] == "LoraLoader"
    assert loader["inputs"]["lora_name"] == "jewelry-sdxl-v1.safetensors"
    assert loader["inputs"]["strength_model"] == loader["inputs"]["strength_clip"] == 0.65
    assert wf["2"]["inputs"]["clip"] == ["10", 1]
    assert wf["5"]["inputs"]["model"] == ["10", 0]

def test_lora_is_refused_for_flux_and_custom_workflows():
    flux = {**comfy.DEFAULTS, "image_preset": "flux-schnell", "image_checkpoint": comfy.IMAGE_PRESETS["flux-schnell"]["checkpoint"]}
    with pytest.raises(comfy.WorkflowError, match="uniquement pour le preset SDXL"):
        comfy._image_workflow(flux, "product", 1024, 1024, 1, None, "jewelry-sdxl-v1.safetensors")

@pytest.mark.parametrize("installed,selectable", [(True, True), (False, False), (None, False)])
async def test_catalog_never_claims_missing_or_unverified_install_selectable(monkeypatch, installed, selectable):
    choices = None if installed is None else (["jewelry-sdxl-v1.safetensors"] if installed else [])
    async def fake_choices(client, base, node, field):
        if node == "LoraLoader": return choices
        return [comfy.IMAGE_PRESETS["sdxl"]["checkpoint"]]
    monkeypatch.setattr(comfy, "_choices", fake_choices)
    settings = {**comfy.DEFAULTS, "image_preset": "sdxl", "image_checkpoint": comfy.IMAGE_PRESETS["sdxl"]["checkpoint"]}
    status = await comfy.lora_catalog_status(settings)
    assert status[0]["selectable"] is selectable
    assert status[0]["compatible"] is True

async def test_generate_image_passes_installed_lora_and_fixed_seed_to_executor(monkeypatch):
    settings = {**comfy.DEFAULTS, "image_preset": "sdxl", "image_checkpoint": comfy.IMAGE_PRESETS["sdxl"]["checkpoint"]}
    async def get_settings(): return settings
    captured = {}
    async def fake_run(workflow, video, progress=None, on_queued=None, s=None):
        captured.update(workflow=workflow, video=video, settings=s)
        return b"png", "image/png"
    monkeypatch.setattr(comfy, "get_settings", get_settings)
    monkeypatch.setattr(comfy, "run", fake_run)
    await comfy.generate_image("hiresjewels_style ring", "1:1", preset="sdxl", lora_name="jewelry-sdxl-v1.safetensors", lora_strength=0.7, seed_override=778899)
    assert captured["workflow"]["10"]["class_type"] == "LoraLoader"
    assert captured["workflow"]["5"]["inputs"]["seed"] == 778899
    assert captured["workflow"]["5"]["inputs"]["model"] == ["10", 0]
    assert captured["video"] is False


async def test_catalog_marks_flux_incompatible(monkeypatch):
    async def fake_choices(client, base, node, field):
        return ["jewelry-sdxl-v1.safetensors"] if node == "LoraLoader" else [comfy.IMAGE_PRESETS["flux-schnell"]["checkpoint"]]
    monkeypatch.setattr(comfy, "_choices", fake_choices)
    settings = {**comfy.DEFAULTS, "image_preset": "flux-schnell", "image_checkpoint": comfy.IMAGE_PRESETS["flux-schnell"]["checkpoint"]}
    status = await comfy.lora_catalog_status(settings)
    assert status[0]["compatible"] is False and status[0]["selectable"] is False


def test_no_lora_keeps_the_existing_sdxl_workflow_unchanged():
    settings = {**comfy.DEFAULTS, "image_preset": "sdxl", "image_checkpoint": comfy.IMAGE_PRESETS["sdxl"]["checkpoint"]}
    wf = comfy._image_workflow(settings, "product ring", 1024, 1024, 12, None)
    assert "10" not in wf
    assert wf["5"]["inputs"]["model"] == ["1", 0]
    assert wf["2"]["inputs"]["clip"] == ["1", 1]


def test_unapproved_lora_filename_is_rejected():
    settings = {**comfy.DEFAULTS, "image_preset": "sdxl", "image_checkpoint": comfy.IMAGE_PRESETS["sdxl"]["checkpoint"]}
    with pytest.raises(comfy.WorkflowError, match="uniquement pour le preset SDXL"):
        comfy._image_workflow(settings, "product", 1024, 1024, 1, None, "other.safetensors")


async def test_custom_workflow_and_unlicensed_preview_are_not_offered(monkeypatch):
    async def fake_choices(client, base, node, field):
        return ["jewelry-sdxl-v1.safetensors"] if node == "LoraLoader" else [comfy.IMAGE_PRESETS["sdxl"]["checkpoint"]]
    monkeypatch.setattr(comfy, "_choices", fake_choices)
    settings = {**comfy.DEFAULTS, "image_preset": "sdxl", "image_checkpoint": comfy.IMAGE_PRESETS["sdxl"]["checkpoint"], "custom_image_workflow": '{"1": {}}'}
    item = comfy.LORA_CATALOG[0]
    status = await comfy.lora_catalog_status(settings)
    assert item["preview_url"] is None
    assert status[0]["installed"] is True
    assert status[0]["compatible"] is False
    assert status[0]["selectable"] is False


def test_product_photo_lora_is_wired_to_sdxl_and_preserves_reference_nodes():
    filename = "sdxl-product-photography-shoaibism.safetensors"
    settings = {**comfy.DEFAULTS, "image_preset": "sdxl", "image_checkpoint": comfy.IMAGE_PRESETS["sdxl"]["checkpoint"]}
    wf = comfy._image_workflow(settings, "PRDCT white sneaker", 1024, 1024, 42, "ref.png", filename, 0.75)
    assert wf["12"]["class_type"] == "LoraLoader"
    assert wf["12"]["inputs"]["lora_name"] == filename
    assert wf["12"]["inputs"]["strength_model"] == wf["12"]["inputs"]["strength_clip"] == 0.75
    assert wf["10"]["class_type"] == "LoadImage"
    assert wf["11"]["class_type"] == "ImageScaleToTotalPixels"
    assert wf["5"]["inputs"]["model"] == ["12", 0]
    assert wf["2"]["inputs"]["clip"] == ["12", 1]


def test_product_lora_metadata_is_pinned_and_trigger_is_exact():
    item = next(x for x in comfy.LORA_CATALOG if x["filename"] == "sdxl-product-photography-shoaibism.safetensors")
    assert item["base_model"] == "stabilityai/stable-diffusion-xl-base-1.0"
    assert item["source_revision"] == "304e968eceee596bff14e7f0979868169dac5c08"
    assert item["file_size_bytes"] == 93065304
    assert item["file_sha256"] == "772797c56b396c60e246e3329609c091ba88ea764a7709f31dfce5461da180ba"
    assert item["trigger"] == "PRDCT"
    assert item["preview_url"] is None  # no third-party preview rights asserted
    assert comfy.prepare_lora_prompt("white sneaker", item["filename"]) == "PRDCT, white sneaker"
    assert comfy.prepare_lora_prompt("PRDCT white sneaker", item["filename"]) == "PRDCT white sneaker"
    assert comfy.prepare_lora_prompt("white sneaker", None) == "white sneaker"


def test_advertisement_candidate_is_not_catalogued_without_clear_license():
    assert not any(x["source_url"] == "https://huggingface.co/martintomov/sdxl-advertisement-lora" for x in comfy.LORA_CATALOG)


def test_future_taxonomy_slots_are_declared_without_fake_loras():
    marketing = comfy.LORA_CATALOG_UNIVERSES["vision-marketing"]
    advertising = comfy.LORA_CATALOG_UNIVERSES["advertising"]
    assert "Architecture" in marketing and "Gastronomie" in marketing and "Headers de sites web" in marketing
    assert "Mannequins" in advertising and "Présentateurs" in advertising and "Publicités cinématographiques" in advertising
    assert all(item["media_type"] == "image" for item in comfy.LORA_CATALOG)
    assert len(comfy.LORA_CATALOG) == 2


@pytest.mark.parametrize("preset", ["flux-dev", "flux-schnell"])
def test_product_lora_is_refused_for_non_sdxl(preset):
    settings = {**comfy.DEFAULTS, "image_preset": preset, "image_checkpoint": comfy.IMAGE_PRESETS[preset]["checkpoint"]}
    with pytest.raises(comfy.WorkflowError, match="uniquement pour le preset SDXL"):
        comfy._image_workflow(settings, "PRDCT product", 1024, 1024, 7, None, "sdxl-product-photography-shoaibism.safetensors")


async def test_product_lora_is_selectable_only_when_file_and_sdxl_are_present(monkeypatch):
    async def fake_choices(client, base, node, field):
        if node == "LoraLoader":
            return ["sdxl-product-photography-shoaibism.safetensors"]
        return [comfy.IMAGE_PRESETS["sdxl"]["checkpoint"]]
    monkeypatch.setattr(comfy, "_choices", fake_choices)
    settings = {**comfy.DEFAULTS, "image_preset": "sdxl", "image_checkpoint": comfy.IMAGE_PRESETS["sdxl"]["checkpoint"]}
    statuses = await comfy.lora_catalog_status(settings)
    product = next(x for x in statuses if x["filename"] == "sdxl-product-photography-shoaibism.safetensors")
    jewelry = next(x for x in statuses if x["filename"] == "jewelry-sdxl-v1.safetensors")
    assert product["installed"] is True and product["compatible"] is True and product["selectable"] is True
    assert jewelry["installed"] is False and jewelry["selectable"] is False


async def test_product_lora_refused_if_comfy_does_not_report_file(monkeypatch):
    async def fake_choices(client, base, node, field):
        return [] if node == "LoraLoader" else [comfy.IMAGE_PRESETS["sdxl"]["checkpoint"]]
    monkeypatch.setattr(comfy, "_choices", fake_choices)
    settings = {**comfy.DEFAULTS, "image_preset": "sdxl", "image_checkpoint": comfy.IMAGE_PRESETS["sdxl"]["checkpoint"]}
    product = next(x for x in await comfy.lora_catalog_status(settings) if x["filename"] == "sdxl-product-photography-shoaibism.safetensors")
    assert product["installed"] is False and product["selectable"] is False
