"""V2-B: tests for the reproducible prompt benchmark. No GPU, no ComfyUI, no network."""
import json

import pytest

from lib.prompt_bench import core
from lib.prompt_bench.corpus import CORPUS, IMAGE_TASKS
from lib.prompt_bench.__main__ import GpuSampler, _gallery, _workflow_params, main as bench_main
from lib.prompt_preparation import PromptTask


def _item(prompt, must, task="photo", forbidden=()):
    return {"id": "t", "task": task, "prompt": prompt, "must": list(must), "forbidden": list(forbidden)}


def test_corpus_is_well_formed_and_covers_required_categories():
    ids = [i["id"] for i in CORPUS]
    assert len(ids) == len(set(ids))
    tasks = {i["task"] for i in CORPUS}
    assert {"photo", "text-to-video", "image-to-video", "retouch", "advertising"} <= tasks
    for item in CORPUS:
        assert item["must"], item["id"]
        for must in item["must"]:
            assert must.lower() in item["prompt"].lower() or core._norm(must) in core._norm(item["prompt"]), (item["id"], must)
        assert PromptTask(item["task"])


def test_legacy_suffix_only_for_image_tasks():
    assert core.legacy_text("une voiture", "photo").endswith(core.LEGACY_IMAGE_SUFFIX)
    assert core.legacy_text("une voiture", "text-to-video") == "une voiture"


def test_ordered_text_keeps_every_clause_and_moves_constraints_first():
    prompt = "Le ciel est nuageux. Une voiture noire roule. Pas de travelling."
    out = core.ordered_text(prompt, "text-to-video")
    assert out == "Une voiture noire roule. Pas de travelling. Le ciel est nuageux."


def test_ordered_text_never_changes_the_words_used():
    prompt = "Un chat noir assis. Le fond est une forêt. Ne pas le rendre blanc."
    out = core.ordered_text(prompt, "photo")
    body = out[: -len(core.LEGACY_IMAGE_SUFFIX)]
    assert sorted(body.replace(".", "").split()) == sorted(prompt.replace(".", "").split())


def test_check_detects_missing_and_forbidden_terms():
    item = _item("Une voiture noire.", ["voiture noire"], forbidden=["rouge"])
    ok = core.check_text("Une voiture noire.", item["prompt"], item)
    assert ok["pass"] and not ok["must_missing"]
    bad = core.check_text("Une voiture rouge.", item["prompt"], item)
    assert not bad["pass"] and bad["must_missing"] == ["voiture noire"]


def test_check_normalises_accents_and_case():
    item = _item("Affiche : « Réveillez-vous » en haut", ["réveillez-vous"])
    assert core.check_text("affiche : « reveillez-vous » en haut", item["prompt"], item)["pass"]


def test_forbidden_term_present_in_source_is_not_flagged():
    item = _item("Pas de rouge", ["pas de rouge"], forbidden=["rouge"])
    assert core.check_text("Pas de rouge", item["prompt"], item)["forbidden_added"] == []


def test_forbidden_term_added_by_preparation_is_flagged():
    item = _item("Une voiture noire", ["voiture noire"], forbidden=["rouge"])
    result = core.check_text("Une voiture noire, rouge", item["prompt"], item)
    assert result["forbidden_added"] == ["rouge"] and not result["pass"]


def test_beyond_clip_window_is_reported_with_estimate():
    filler = " ".join(["mot"] * 80)
    item = _item(f"{filler} vélo rouge", ["vélo rouge"])
    result = core.check_text(f"{filler} vélo rouge", item["prompt"], item)
    assert result["must_beyond_clip_window"] == ["vélo rouge"]
    assert result["approx_clip_tokens"] > core.CLIP_WINDOW


@pytest.mark.asyncio
async def test_v2a_falls_back_to_exact_original_without_llm():
    text, status = await core.v2a_text("Une voiture noire.  Garde l'angle.", "photo")
    assert text == "Une voiture noire.  Garde l'angle."  # exact, whitespace included
    assert status == "fallback"


@pytest.mark.asyncio
async def test_v2a_reference_declared_for_image_to_video_not_retouch():
    _, i2v = await core.v2a_text("L'homme tourne la tête.", "image-to-video")
    _, retouch = await core.v2a_text("Remplacer le ciel.", "retouch")
    assert i2v == "fallback"  # reference accepted, LLM absent
    assert retouch == "unsupported"  # no mask in the app: honest refusal, not a fake capability


@pytest.mark.asyncio
async def test_build_item_returns_three_approaches_and_checks():
    item = next(i for i in CORPUS if i["id"] == "t2v_camera_fixed")
    built = await core.build_item(item)
    assert set(built["approaches"]) == {"A_legacy", "B_v2a_balanced", "C_constraint_first"}
    assert built["approaches"]["B_v2a_balanced"]["text"] == item["prompt"]
    assert built["approaches"]["A_legacy"]["text"] == item["prompt"]  # video raw, as the app sends it
    assert all("checks" in a for a in built["approaches"].values())


@pytest.mark.asyncio
async def test_build_item_with_failing_llm_is_original_not_invented():
    async def broken(system, payload):
        raise TimeoutError("simulated")

    item = next(i for i in CORPUS if i["id"] == "photo_product")
    built = await core.build_item(item, analyzer=broken)
    assert built["approaches"]["B_v2a_balanced"]["text"] == item["prompt"]
    assert built["v2a_status"] == "fallback"


def test_summary_counts_every_approach():
    results = [{"approaches": {n: {"checks": {"pass": True, "must_missing": [], "must_beyond_clip_window": [], "forbidden_added": []}}
                               for n in ("A_legacy", "B_v2a_balanced", "C_constraint_first")}}]
    summary = core.summarize(results)
    assert summary["A_legacy"] == {"pass": 1, "total": 1, "missing": 0, "beyond_clip_window": 0, "forbidden_added": 0}


def test_workflow_params_extracts_sampler_without_links():
    wf = {"5": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "seed": 7, "steps": 22, "cfg": 1.0}},
          "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "x.safetensors"}}}
    params = _workflow_params(wf)
    assert params["KSampler"] == {"seed": 7, "steps": 22, "cfg": 1.0}
    assert params["CheckpointLoaderSimple"] == {"ckpt_name": "x.safetensors"}


def test_gpu_sampler_is_safe_without_nvidia_smi(monkeypatch):
    monkeypatch.setattr(GpuSampler, "_used", staticmethod(lambda: None))
    with GpuSampler() as gpu:
        pass
    assert gpu.peak_delta_mib is None


def test_gallery_escapes_html_and_shows_status(tmp_path):
    manifest = {"created": "t", "renders": [], "items": [{
        "id": "x<script>", "task": "photo", "v2a_status": "fallback",
        "approaches": {n: {"text": "<b>hi</b>", "checks": {"pass": False, "must_missing": ["a"],
                                                            "must_beyond_clip_window": [], "forbidden_added": []}}
                       for n in ("A_legacy", "B_v2a_balanced", "C_constraint_first")}}]}
    page = _gallery(manifest)
    assert "<script>" not in page and "&lt;b&gt;hi&lt;/b&gt;" in page and "FAIL" in page


def test_cli_text_only_run_writes_manifest_without_gpu(tmp_path, monkeypatch):
    monkeypatch.setenv("MONGO_URL", "mongodb://127.0.0.1:1")
    rc = bench_main(["--out", str(tmp_path), "--only", "photo_product", "retouch_localized"])
    assert rc == 0
    run = next(tmp_path.iterdir())
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["rendered"] is False and manifest["renders"] == []
    assert manifest["v2a_llm"].startswith("none")
    assert (run / "index.html").exists()
    assert {i["id"] for i in manifest["items"]} == {"photo_product", "retouch_localized"}


def test_cli_rejects_unknown_identifiers(tmp_path):
    with pytest.raises(SystemExit):
        bench_main(["--out", str(tmp_path), "--only", "does_not_exist"])


def test_image_tasks_constant_matches_corpus():
    assert IMAGE_TASKS == {"photo", "retouch", "advertising"}
