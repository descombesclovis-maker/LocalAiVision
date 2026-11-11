"""Conservative, experimental French-to-English prompt preparation for SANA.

This helper is intentionally not wired into the generation path. It translates
only clauses whose semantic mapping is explicit and tested; unknown clauses
make the candidate unusable, while the original French prompt is always kept.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re


@dataclass(frozen=True)
class PromptIntent:
    subject: str | None = None
    species: str | None = None
    subject_count: int | None = None
    colors: tuple[str, ...] = ()
    actions: tuple[str, ...] = ()
    movement_directions: tuple[str, ...] = ()
    chronology: tuple[str, ...] = ()
    object_interactions: tuple[str, ...] = ()
    environment: str | None = None
    camera: str | None = None
    visual_style: str | None = None
    explicit_constraints: tuple[str, ...] = ()
    negative_constraints: tuple[str, ...] = ()


@dataclass(frozen=True)
class PreparedPrompt:
    original_fr: str
    candidate_en: str | None
    intent: PromptIntent
    translated_clauses: tuple[str, ...]
    unsupported_clauses: tuple[str, ...]
    safe_to_compare: bool

    def as_dict(self) -> dict:
        result = asdict(self)
        result["intent"] = asdict(self.intent)
        return result


def _clean_clause(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().rstrip(".;:"))


# Exact semantic mappings for the archived V2-AB reference prompt. The deliberate
# narrow scope avoids silently dropping or embellishing unsupported French text.
_RULES: tuple[tuple[re.Pattern[str], str, dict], ...] = (
    (
        re.compile(r"un renard roux court de gauche à droite dans une forêt (?:verte|verdoyante)", re.I),
        "A red fox runs from left to right through a green forest",
        {
            "subject": "fox",
            "species": "fox",
            "subject_count": 1,
            "colors": ("red",),
            "actions": ("run",),
            "movement_directions": ("left-to-right",),
            "environment": "green forest",
        },
    ),
    (
        re.compile(r"saute par-dessus une branche tombée", re.I),
        "jumps over a fallen branch",
        {
            "actions": ("jump over a fallen branch",),
            "chronology": ("after the run",),
            "object_interactions": ("fox jumps over fallen branch",),
        },
    ),
    (
        re.compile(r"caméra fixe", re.I),
        "fixed camera",
        {"camera": "fixed"},
    ),
    (
        re.compile(r"plan cinématographique large", re.I),
        "cinematic wide shot",
        {"visual_style": "cinematic", "explicit_constraints": ("wide shot",)},
    ),
)


def prepare_sana_prompt(prompt_fr: str) -> PreparedPrompt:
    """Return a clause-preserving candidate; never replace the source prompt.

    A candidate is safe for an experiment only when every non-empty comma-
    separated clause matches a reviewed mapping. Unsupported text is reported
    verbatim and disables the translated candidate.
    """
    if not isinstance(prompt_fr, str) or not prompt_fr.strip():
        raise ValueError("Le prompt français doit être une chaîne non vide.")

    source = prompt_fr
    clauses = tuple(
        _clean_clause(x)
        for x in re.split(r"[,;\n]+|(?<=\.)\s+(?=[A-ZÀ-ÖØ-Þ])", source.strip())
        if _clean_clause(x)
    )
    translations: list[str] = []
    unsupported: list[str] = []
    collected: dict[str, object] = {}

    for clause in clauses:
        match = next((rule for rule in _RULES if rule[0].fullmatch(clause)), None)
        if match is None:
            unsupported.append(clause)
            continue
        _pattern, english, values = match
        translations.append(english)
        for key, value in values.items():
            if isinstance(value, tuple):
                collected[key] = tuple(collected.get(key, ())) + value
            else:
                collected[key] = value

    intent = PromptIntent(**collected)
    safe = bool(clauses) and not unsupported and len(translations) == len(clauses)
    return PreparedPrompt(
        original_fr=source,
        candidate_en=", ".join(translations) + "." if safe else None,
        intent=intent,
        translated_clauses=tuple(translations),
        unsupported_clauses=tuple(unsupported),
        safe_to_compare=safe,
    )
