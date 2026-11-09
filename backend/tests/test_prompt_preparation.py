"""V2-A source/capability/regression tests, NOT a claim of improved visual quality.

Corpus annotations below are a deterministic stand-in for local LLM responses. They
validate the parser/guards/adapters, not a real LLM's extraction accuracy or GPU output.
"""
import asyncio
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import AsyncMock

import pytest

from lib.prompt_preparation import (
    COMFY_IMAGE, COMFY_VIDEO, RECOMMENDED_MODE, EngineCapabilities, FidelityMode,
    PreparationStatus, PromptTask, compare_preparations, prepare_prompt,
)
from lib.prompt_preparation.engine import ANALYSIS_FIELDS, MAX_CLAUSES, MAX_PROMPT_CHARS, split_clauses

BACKEND = Path(__file__).resolve().parents[1]
CORPUS = json.loads((Path(__file__).parent / "fixtures/prompts_v2a.json").read_text(encoding="utf-8"))


def evidence(prompt, quote):
    clause = next(item for item in split_clauses(prompt) if quote in item.text)
    return {"clause": clause.id, "quote": quote}


def response_for(case):
    prompt = case["prompt"]
    data = {field: [evidence(prompt, quote) for quote in case.get("annotations", {}).get(field, [])] for field in ANALYSIS_FIELDS}
    data["conflicts"] = [{
        "left": evidence(prompt, item["left"]), "right": evidence(prompt, item["right"]), "kind": item["kind"],
    } for item in case.get("conflicts", [])]
    return data


def small_case(prompt="Une voiture noire, pas rouge. Caméra immobile ; aucun travelling."):
    return {"prompt": prompt, "annotations": {"subject": ["voiture noire"], "mandatory": ["Caméra immobile"]}}


def codes(result):
    return {item.code for item in result.diagnostics}


@pytest.mark.parametrize("case", CORPUS, ids=lambda case: case["id"])
@pytest.mark.parametrize("mode", list(FidelityMode))
async def test_corpus_requirements_survive_in_all_modes(case, mode):
    analyzer = AsyncMock(return_value=json.dumps(response_for(case), ensure_ascii=False))
    task = PromptTask(case["task"])
    result = await prepare_prompt(
        case["prompt"], enabled=True, task=task, mode=mode, analyzer=analyzer,
        capabilities=COMFY_VIDEO if task in (PromptTask.TEXT_TO_VIDEO, PromptTask.IMAGE_TO_VIDEO) else COMFY_IMAGE,
        reference_provided=case.get("reference_provided", False),
    )
    analyzer.assert_awaited_once()
    assert result.original_prompt == case["prompt"]
    for requirement in case["required"]:
        assert requirement in result.prepared_prompt
    for field, quotes in case["annotations"].items():
        assert [item.quote for item in getattr(result.analysis, field)] == quotes
    for field in ANALYSIS_FIELDS:
        for item in getattr(result.analysis, field):
            assert result.original_prompt[item.start:item.end] == item.quote
            assert item.quote in item.context
    if case.get("conflicts"):
        assert result.status == PreparationStatus.NEEDS_CLARIFICATION
        assert result.prepared_prompt == result.original_prompt
        assert result.requires_clarification and not result.safe_to_apply
        assert len(result.analysis.conflicts) == len(case["conflicts"])
        assert "conflicting_requirements" in codes(result)
    else:
        assert result.status == PreparationStatus.PREPARED and result.safe_to_apply
        assert result.prepared_prompt.startswith(case["prompt"])
        assert not result.requires_clarification
    if task == PromptTask.IMAGE_TO_VIDEO:
        assert "identity_text_only" in codes(result)
    if task == PromptTask.RETOUCH:
        assert "unmasked_edit" in codes(result)


async def test_balanced_is_recommended_not_automatically_activated():
    analyzer = AsyncMock(side_effect=AssertionError("disabled must not do I/O"))
    result = await prepare_prompt("  Prompt original\r\n\tinchangé 🎬  ", analyzer=analyzer)
    assert RECOMMENDED_MODE == FidelityMode.BALANCED
    assert result.mode == FidelityMode.BALANCED
    assert result.status == PreparationStatus.DISABLED
    assert result.prepared_prompt == result.original_prompt
    assert not result.safe_to_apply and not result.local_llm_used
    assert result.to_dict()["recommended_mode"] == "balanced"
    analyzer.assert_not_awaited()


@pytest.mark.parametrize("error", [ConnectionError("offline"), RuntimeError("private-response-secret"), ValueError("missing model")])
async def test_llm_unavailable_falls_back_verbatim_without_leaking_response(error):
    original = " \r\nUne voiture noire ; caméra fixe. Ne rien ajouter.\t "
    result = await prepare_prompt(original, enabled=True, analyzer=AsyncMock(side_effect=error))
    assert result.status == PreparationStatus.FALLBACK
    assert result.original_prompt == result.prepared_prompt == original
    assert not result.safe_to_apply
    assert "local_llm_unavailable" in codes(result)
    assert "private-response-secret" not in json.dumps(result.to_dict())


async def test_timeout_cancels_analysis_and_preserves_original():
    cancelled = asyncio.Event()

    async def blocked(system, payload):
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    result = await prepare_prompt("Une voiture noire.", enabled=True, analyzer=blocked, timeout=0.01)
    assert result.prepared_prompt == "Une voiture noire."
    assert "analysis_timeout" in codes(result)
    assert cancelled.is_set()


async def test_caller_cancellation_is_not_swallowed_as_fallback():
    started = asyncio.Event()

    async def blocked(system, payload):
        started.set()
        await asyncio.Event().wait()

    task = asyncio.create_task(prepare_prompt("Une voiture noire.", enabled=True, analyzer=blocked))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.parametrize("original", ["", "  \r\n\t ", "x" * (MAX_PROMPT_CHARS + 1), "Objet. " * (MAX_CLAUSES + 1)])
async def test_empty_or_excessive_input_never_truncates_or_calls_llm(original):
    analyzer = AsyncMock()
    result = await prepare_prompt(original, enabled=True, analyzer=analyzer)
    assert result.original_prompt == result.prepared_prompt == original
    assert result.status == PreparationStatus.FALLBACK
    analyzer.assert_not_awaited()


@pytest.mark.parametrize("raw", [None, "not JSON", "[]", "{}", '{"subject": [], "subject": []}', "x" * 65537])
async def test_malformed_or_duplicate_json_is_not_used(raw):
    case = small_case()
    result = await prepare_prompt(case["prompt"], enabled=True, analyzer=AsyncMock(return_value=raw))
    assert result.status == PreparationStatus.FALLBACK
    assert result.prepared_prompt == case["prompt"]
    assert "invalid_analysis" in codes(result)


@pytest.mark.parametrize("mutation", [
    lambda data: data.update(enhanced_prompt="a red car, cinematic dolly-in"),
    lambda data: data.update(cfg=9, steps=80),
    lambda data: data.update(negative_prompt="static, black car"),
    lambda data: data.update(subject=[{"clause": 0, "quote": "voiture rouge"}]),
    lambda data: data.update(subject=[{"clause": 1, "quote": "voiture noire"}]),
    lambda data: data.update(subject=[{"clause": True, "quote": "voiture noire"}]),
    lambda data: data.update(subject=[{"clause": -1, "quote": "voiture noire"}]),
    lambda data: data.update(subject=[{"clause": 0, "quote": "voiture noire", "rewrite": "red car"}]),
    lambda data: data.update(subject="voiture noire"),
    lambda data: data.update(mandatory=[{"clause": 0, "quote": ""}]),
    lambda data: data.update(preserve=None),
    lambda data: data.pop("forbidden"),
    lambda data: data.update(subject=[], actions=[]),
])
async def test_llm_cannot_inject_rewrites_parameters_or_ungrounded_details(mutation):
    case = small_case()
    data = copy.deepcopy(response_for(case))
    mutation(data)
    result = await prepare_prompt(case["prompt"], enabled=True, analyzer=AsyncMock(return_value=json.dumps(data)))
    assert result.status == PreparationStatus.FALLBACK
    assert result.prepared_prompt == case["prompt"]
    assert "invalid_analysis" in codes(result)


async def test_negative_subquote_cannot_be_promoted_without_its_source_context():
    case = small_case()
    data = response_for(case)
    # An imperfect local classifier selects "rouge" as an attribute despite "pas rouge".
    data["attributes"] = [evidence(case["prompt"], "rouge")]
    result = await prepare_prompt(case["prompt"], enabled=True, analyzer=AsyncMock(return_value=json.dumps(data)))
    assert result.status == PreparationStatus.PREPARED
    assert result.prepared_prompt.count("Une voiture noire, pas rouge.") == 1
    assert result.analysis.attributes[0].context == "Une voiture noire, pas rouge."
    assert "rouge" not in result.prepared_prompt[len(case["prompt"]):]
    assert "red car" not in result.prepared_prompt
    assert "slow camera push-in" not in result.prepared_prompt


@pytest.mark.parametrize("wrapper", [lambda text: text, lambda text: "```json\n" + text + "\n```"])
async def test_valid_plain_or_single_fenced_json_is_accepted(wrapper):
    case = small_case()
    result = await prepare_prompt(case["prompt"], enabled=True, analyzer=AsyncMock(return_value=wrapper(json.dumps(response_for(case)))))
    assert result.safe_to_apply


async def test_unresolved_conflict_is_never_resolved_even_in_creative_mode():
    case = next(item for item in CORPUS if item["id"] == "contradictory_same_scope")
    result = await prepare_prompt(case["prompt"], enabled=True, mode="creative", analyzer=AsyncMock(return_value=json.dumps(response_for(case))))
    assert result.status == PreparationStatus.NEEDS_CLARIFICATION
    assert not result.safe_to_apply
    assert result.prepared_prompt == case["prompt"]
    assert all(item.left.quote in case["prompt"] and item.right.quote in case["prompt"] for item in result.analysis.conflicts)


@pytest.mark.parametrize("options,expected", [
    ({"task": "image-to-video", "capabilities": COMFY_VIDEO}, "reference_required"),
    ({"task": "retouch", "capabilities": COMFY_IMAGE}, "reference_required"),
    ({"task": "text-to-video", "capabilities": COMFY_IMAGE}, "unsupported_task"),
    ({"task": "retouch", "capabilities": COMFY_IMAGE, "reference_provided": True, "mask_provided": True}, "unsupported_mask"),
])
async def test_unsupported_capabilities_do_not_trigger_llm_or_fake_workflow_support(options, expected):
    analyzer = AsyncMock()
    result = await prepare_prompt("Demande source à conserver.", enabled=True, analyzer=analyzer, **options)
    assert result.status == PreparationStatus.UNSUPPORTED
    assert expected in codes(result)
    assert result.original_prompt == result.prepared_prompt
    assert not result.safe_to_apply
    analyzer.assert_not_awaited()


async def test_declared_mask_capability_is_only_metadata_not_an_inference_parameter():
    case = next(item for item in CORPUS if item["id"] == "localized_retouch")
    # Abstract TEST workflow, not a claim that current ComfyUI built-ins support inpainting.
    capability = EngineCapabilities("test-masked-workflow", frozenset({PromptTask.RETOUCH}), reference_image=True, localized_mask=True)
    result = await prepare_prompt(case["prompt"], task="retouch", enabled=True, analyzer=AsyncMock(return_value=json.dumps(response_for(case))), capabilities=capability, reference_provided=True, mask_provided=True)
    assert result.safe_to_apply
    assert "unmasked_edit" not in codes(result)
    assert not {"cfg", "steps", "sampler", "negative_prompt", "mask"}.intersection(result.to_dict())


async def test_mode_and_task_adapters_are_distinct_without_visual_inventions():
    case = small_case()
    outputs = {}
    for task in PromptTask:
        for mode in FidelityMode:
            result = await prepare_prompt(case["prompt"], task=task, mode=mode, enabled=True, analyzer=AsyncMock(return_value=json.dumps(response_for(case))), reference_provided=True)
            assert result.safe_to_apply
            outputs[task, mode] = result.prepared_prompt
            assert result.prepared_prompt.startswith(case["prompt"])
    assert len(set(outputs.values())) == len(PromptTask) * len(FidelityMode)
    assert "unspecified details" in outputs[PromptTask.PHOTO, FidelityMode.CREATIVE]
    assert "No creative additions" in outputs[PromptTask.PHOTO, FidelityMode.STRICT]


async def test_comparison_keeps_actual_legacy_text_selected_and_exposes_diagnostics():
    case = small_case()
    legacy = case["prompt"] + ", highly detailed, professional photography, sharp focus, premium quality"
    result = await compare_preparations(case["prompt"], legacy, enabled=True, analyzer=AsyncMock(return_value=json.dumps(response_for(case))))
    document = json.loads(json.dumps(result.to_dict(), ensure_ascii=False))
    assert result.selected_prompt == legacy
    assert document["automatic_application"] is False
    assert document["comparison_scope"] == "text_only_not_visual_quality"
    assert document["candidate"]["original_prompt"] == case["prompt"]
    assert document["candidate"]["prepared_prompt"] != legacy
    assert document["candidate"]["analysis"]["subject"][0]["quote"] == "voiture noire"


async def test_current_photo_route_keeps_its_legacy_preparation(monkeypatch):
    # Real route, mocked storage/spawn only: V2-A has NOT replaced the live preparation.
    from lib.prompt_preparation import engine
    from models.schemas import ImageRequest
    from routers import media

    guard = AsyncMock(side_effect=AssertionError("experimental engine must stay opt-in"))
    monkeypatch.setattr(engine, "prepare_prompt", guard)
    monkeypatch.setattr(media, "_ref_b64", AsyncMock(return_value=(None, None)))
    monkeypatch.setattr(media, "create_media", AsyncMock(return_value={"id": "m1"}))
    monkeypatch.setattr(media, "_run_image", AsyncMock())
    monkeypatch.setattr(media, "spawn", lambda coro: coro.close())
    monkeypatch.setattr(media, "_out", lambda value: value)
    body = ImageRequest(prompt="Une voiture noire, caméra fixe.", model="comfy")
    await media.create_image(body)
    assert media._run_image.call_args.args[1] == body.prompt + ", highly detailed, professional photography, sharp focus, premium quality"
    assert media.create_media.await_args.args[2] == body.prompt
    guard.assert_not_awaited()


def test_source_offsets_preserve_unicode_decimals_and_crlf():
    source = "  ÉCLAIR 🎬, focale 50.5 mm, f/1.8, pas rouge.\r\n\tMême visage e\u0301.  "
    clauses = split_clauses(source)
    assert len(clauses) == 2
    assert "50.5 mm, f/1.8" in clauses[0].text
    assert all(source[item.start:item.end] == item.text for item in clauses)
    assert clauses[1].text.endswith("e\u0301.")


def test_cli_disabled_comparison_preserves_utf8_crlf_and_needs_no_db(tmp_path):
    original = " \r\nUne voiture noire, caméra immobile 🎬.\t "
    legacy = original + ", legacy unchanged\r\n"
    prompt_file, legacy_file = tmp_path / "original.txt", tmp_path / "legacy.txt"
    prompt_file.write_bytes(original.encode("utf-8"))
    legacy_file.write_bytes(legacy.encode("utf-8"))
    env = dict(os.environ)
    env.pop("MONGO_URL", None)
    env.pop("DB_NAME", None)
    completed = subprocess.run([
        sys.executable, "-m", "lib.prompt_preparation", "--prompt-file", str(prompt_file),
        "--legacy-file", str(legacy_file), "--profile", "comfy-image",
    ], cwd=BACKEND, env=env, capture_output=True, text=True, encoding="utf-8", timeout=10, check=True)
    result = json.loads(completed.stdout)
    assert result["original_prompt"] == original
    assert result["selected_prompt"] == legacy
    assert result["candidate"]["prepared_prompt"] == original
    assert result["candidate"]["status"] == "disabled"
    assert result["automatic_application"] is False


async def test_multiline_prohibition_scope_cannot_be_inverted_by_classifier():
    prompt = "À ne PAS représenter :\nUne voiture rouge.\nSujet réel : une voiture noire."
    case = {"prompt": prompt, "annotations": {"subject": ["Une voiture rouge"]}}
    # Grounded but misclassified source: the forbidden heading is in another clause.
    result = await prepare_prompt(prompt, enabled=True, analyzer=AsyncMock(return_value=json.dumps(response_for(case))))
    assert result.safe_to_apply
    assert result.prepared_prompt.startswith(prompt)
    assert result.prepared_prompt.count("Une voiture rouge.") == 1
    assert "rouge" not in result.prepared_prompt[len(prompt):]


async def test_task_adapter_guides_local_analysis_without_rewriting_the_source():
    case = small_case()
    analyzer = AsyncMock(return_value=json.dumps(response_for(case)))
    await prepare_prompt(case["prompt"], task="image-to-video", enabled=True, analyzer=analyzer, reference_provided=True)
    payload = json.loads(analyzer.await_args.args[1])
    assert payload["task"] == "image-to-video"
    assert payload["analysis_priority"][:5] == ["mandatory", "forbidden", "preserve", "identity", "subject"]
    assert [item["text"] for item in payload["clauses"]] == [item.text for item in split_clauses(case["prompt"])]
