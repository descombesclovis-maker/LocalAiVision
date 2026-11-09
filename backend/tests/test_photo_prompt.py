"""Régression : pas de « blanc., highly detailed » ; app et benchmark partagent le même assemblage."""
from lib.photo_prompt import PHOTO_QUALITY_SUFFIX, comfy_photo_prompt
from lib.prompt_bench.core import IMAGE_TASKS, legacy_text


def test_no_double_punctuation_after_period():
    out = comfy_photo_prompt("Un flacon sur du marbre blanc.")
    assert ".," not in out and out == "Un flacon sur du marbre blanc" + PHOTO_QUALITY_SUFFIX


def test_prompt_without_final_punctuation_is_unchanged_except_suffix():
    assert comfy_photo_prompt("Un flacon bleu") == "Un flacon bleu" + PHOTO_QUALITY_SUFFIX


def test_trailing_spaces_and_semicolons_are_stripped():
    assert comfy_photo_prompt("Un flacon ;  ") == "Un flacon" + PHOTO_QUALITY_SUFFIX


def test_benchmark_legacy_text_uses_same_assembly():
    task = next(iter(IMAGE_TASKS))
    out = legacy_text("Un flacon sur du marbre blanc.", task)
    assert out == comfy_photo_prompt("Un flacon sur du marbre blanc.")
    assert ".," not in out
