"""Five text-only adapters. No sampler/CFG/negative-prompt or workflow mutation."""
from dataclasses import dataclass

from .types import Diagnostic, EngineCapabilities, FidelityMode, PromptAnalysis, PromptTask


# Current BUILT-IN ComfyUI workflows only. They implement img2img / I2V, not masks,
# identity locks, spatial conditioning or a camera-control node. Not for custom graphs.
COMFY_IMAGE = EngineCapabilities(
    name="comfy-builtin-image",
    supported_tasks=frozenset({PromptTask.PHOTO, PromptTask.RETOUCH, PromptTask.ADVERTISING}),
    reference_image=True,
)
COMFY_VIDEO = EngineCapabilities(
    name="comfy-builtin-video",
    supported_tasks=frozenset({PromptTask.TEXT_TO_VIDEO, PromptTask.IMAGE_TO_VIDEO}),
    reference_image=True,
)


@dataclass(frozen=True)
class PromptAdapter:
    title: str
    instruction: str
    focus: tuple[str, ...]


ADAPTERS = {
    PromptTask.PHOTO: PromptAdapter(
        "Still-image instructions",
        "Keep the explicitly requested appearance, colors, spatial layout and style.",
        ("subject", "attributes", "environment", "spatial_relations", "actions", "framing", "lighting", "style"),
    ),
    PromptTask.TEXT_TO_VIDEO: PromptAdapter(
        "Text-to-video instructions",
        "Follow the requested action order and camera motion; do not invent a camera movement.",
        ("subject", "attributes", "actions", "motion", "spatial_relations", "environment", "framing", "lighting", "style"),
    ),
    PromptTask.IMAGE_TO_VIDEO: PromptAdapter(
        "Reference-image animation instructions",
        "Animate the supplied reference according to the request; keep all explicitly protected visual details.",
        ("identity", "preserve", "subject", "attributes", "actions", "motion", "environment", "spatial_relations", "framing", "lighting", "style"),
    ),
    PromptTask.RETOUCH: PromptAdapter(
        "Image-edit instructions",
        "Apply only the requested changes; preserve areas and identity not targeted by the request.",
        ("preserve", "identity", "actions", "subject", "attributes", "spatial_relations", "environment", "framing", "lighting", "style"),
    ),
    PromptTask.ADVERTISING: PromptAdapter(
        "Advertising-image instructions",
        "Keep the requested product, brand details and exact requested wording; do not invent product claims.",
        ("subject", "attributes", "preserve", "spatial_relations", "framing", "lighting", "style", "environment", "actions"),
    ),
}

_MODE_POLICY = {
    FidelityMode.STRICT: "No creative additions. All explicit user requirements are mandatory.",
    FidelityMode.BALANCED: "Improve clarity and execution coherence only. Never override an explicit user requirement.",
    FidelityMode.CREATIVE: "Aesthetic freedom applies only to unspecified details. Never override an explicit user requirement.",
}


def capability_diagnostics(
    task: PromptTask, capabilities: EngineCapabilities | None,
    reference_provided: bool, mask_provided: bool,
) -> tuple[Diagnostic, ...]:
    out = []
    if task in (PromptTask.IMAGE_TO_VIDEO, PromptTask.RETOUCH) and not reference_provided:
        out.append(Diagnostic("reference_required", "Une image de référence est nécessaire pour cette tâche.", "error"))
    if capabilities is None:
        out.append(Diagnostic("capabilities_undeclared", "Capacités du workflow non déclarées : aucun contrôle visuel garanti."))
    elif task not in capabilities.supported_tasks:
        out.append(Diagnostic("unsupported_task", "La tâche demandée n'est pas prise en charge par ce workflow.", "error"))
    if reference_provided and capabilities is not None and not capabilities.reference_image:
        out.append(Diagnostic("unsupported_reference", "Ce workflow ne prend pas en charge une image de référence.", "error"))
    if mask_provided and (capabilities is None or not capabilities.localized_mask or task != PromptTask.RETOUCH):
        out.append(Diagnostic("unsupported_mask", "Aucune prise en charge vérifiée du masque localisé pour cette tâche ; aucun masque ne sera ajouté.", "error"))
    if task == PromptTask.RETOUCH and not mask_provided:
        out.append(Diagnostic("unmasked_edit", "Sans masque effectif, un prompt seul ne garantit pas la conservation des zones non ciblées."))
    return tuple(out)


def control_diagnostics(analysis: PromptAnalysis, capabilities: EngineCapabilities | None) -> tuple[Diagnostic, ...]:
    out = []
    if analysis.identity and (capabilities is None or not capabilities.identity_control):
        out.append(Diagnostic("identity_text_only", "Identité demandée conservée dans le texte, sans verrouillage d'identité garanti par le workflow."))
    if analysis.spatial_relations and (capabilities is None or not capabilities.spatial_control):
        out.append(Diagnostic("spatial_text_only", "Relations spatiales conservées dans le texte, sans contrôle spatial dédié."))
    if analysis.motion and (capabilities is None or not capabilities.camera_control):
        out.append(Diagnostic("motion_text_only", "Mouvements conservés dans le texte, sans contrôle caméra dédié garanti."))
    return tuple(out)


def render_prompt(original: str, task: PromptTask, mode: FidelityMode) -> str:
    """Keep the ENTIRE original once, then fixed, non-visual execution policies only.

    Never append LLM-selected fragments as independent positive instructions. Even a
    verbatim quote can lose a negation/list heading/exception from another sentence.
    Structured evidence stays in diagnostics; it cannot invert source scope here.
    No translation, truncation, new visual facts or inference parameters.
    """
    adapter = ADAPTERS[task]
    return "\n\n".join([
        original, f"{adapter.title}. {adapter.instruction}", _MODE_POLICY[mode],
    ])
