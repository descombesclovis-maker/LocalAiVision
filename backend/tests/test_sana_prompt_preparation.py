from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.sana_prompt_preparation import prepare_sana_prompt


REFERENCE_FR = (
    "Un renard roux court de gauche à droite dans une forêt verte, "
    "saute par-dessus une branche tombée, caméra fixe, plan cinématographique large."
)


def test_reference_translation_preserves_required_semantics_and_order():
    prepared = prepare_sana_prompt(REFERENCE_FR)
    assert prepared.safe_to_compare is True
    assert prepared.original_fr == REFERENCE_FR
    assert prepared.candidate_en == (
        "A red fox runs from left to right through a green forest, "
        "jumps over a fallen branch, fixed camera, cinematic wide shot."
    )
    assert prepared.intent.subject == "fox"
    assert prepared.intent.species == "fox"
    assert prepared.intent.subject_count == 1
    assert prepared.intent.colors == ("red",)
    assert prepared.intent.actions == ("run", "jump over a fallen branch")
    assert prepared.intent.movement_directions == ("left-to-right",)
    assert prepared.intent.chronology == ("after the run",)
    assert prepared.intent.object_interactions == ("fox jumps over fallen branch",)
    assert prepared.intent.environment == "green forest"
    assert prepared.intent.camera == "fixed"
    assert prepared.intent.visual_style == "cinematic"
    # Landing is not in the archived V2-AB source prompt; do not invent it.
    assert "land" not in prepared.candidate_en.lower()


def test_unsupported_clause_disables_translation_but_keeps_original_verbatim():
    source = "  " + REFERENCE_FR + " Sans musique.  "
    prepared = prepare_sana_prompt(source)
    assert prepared.original_fr == source
    assert prepared.safe_to_compare is False
    assert prepared.candidate_en is None
    assert prepared.unsupported_clauses == ("Sans musique",)
    assert prepared.intent.negative_constraints == ()


def test_unknown_or_ambiguous_prompt_never_gets_partially_translated():
    source = "Un renard roux court vers le nord et s'arrête près d'une rivière."
    prepared = prepare_sana_prompt(source)
    assert not prepared.safe_to_compare
    assert prepared.candidate_en is None
    assert prepared.unsupported_clauses == (source.rstrip("."),)
    assert prepared.original_fr == source


def test_empty_prompt_rejected_without_creating_candidate():
    try:
        prepare_sana_prompt("  \n")
    except ValueError as exc:
        assert "non vide" in str(exc)
    else:
        raise AssertionError("empty prompt must be rejected")
