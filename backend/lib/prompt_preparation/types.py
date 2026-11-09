"""Generator-independent contracts for experimental, source-grounded prompt preparation."""
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Literal


class FidelityMode(str, Enum):
    STRICT = "strict"
    BALANCED = "balanced"
    CREATIVE = "creative"


RECOMMENDED_MODE = FidelityMode.BALANCED  # Recommendation, NOT an activation flag.


class PromptTask(str, Enum):
    PHOTO = "photo"
    TEXT_TO_VIDEO = "text-to-video"
    IMAGE_TO_VIDEO = "image-to-video"
    RETOUCH = "retouch"
    ADVERTISING = "advertising"


class PreparationStatus(str, Enum):
    DISABLED = "disabled"
    FALLBACK = "fallback"
    PREPARED = "prepared"
    NEEDS_CLARIFICATION = "needs_clarification"
    UNSUPPORTED = "unsupported"


ANALYSIS_FIELDS = (
    "subject", "attributes", "environment", "actions", "framing", "lighting",
    "mandatory", "forbidden", "preserve", "style", "spatial_relations", "motion", "identity",
)


@dataclass(frozen=True)
class SourceClause:
    id: int
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class Evidence:
    clause: int
    quote: str
    start: int
    end: int
    context: str  # Source clause for diagnostics; original_prompt keeps global scope.


@dataclass(frozen=True)
class Conflict:
    left: Evidence
    right: Evidence
    kind: Literal["mutually_exclusive", "ambiguous_scope", "timing"]


@dataclass(frozen=True)
class PromptAnalysis:
    clauses: tuple[SourceClause, ...] = ()
    subject: tuple[Evidence, ...] = ()
    attributes: tuple[Evidence, ...] = ()
    environment: tuple[Evidence, ...] = ()
    actions: tuple[Evidence, ...] = ()
    framing: tuple[Evidence, ...] = ()
    lighting: tuple[Evidence, ...] = ()
    mandatory: tuple[Evidence, ...] = ()
    forbidden: tuple[Evidence, ...] = ()
    preserve: tuple[Evidence, ...] = ()
    style: tuple[Evidence, ...] = ()
    spatial_relations: tuple[Evidence, ...] = ()
    motion: tuple[Evidence, ...] = ()
    identity: tuple[Evidence, ...] = ()
    conflicts: tuple[Conflict, ...] = ()


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    severity: Literal["info", "warning", "error"] = "warning"


@dataclass(frozen=True)
class EngineCapabilities:
    """Declared workflow capabilities, not promises about the generated visual result.

    No inference parameters are part of this contract. Custom workflows must declare
    their own capabilities instead of inheriting assumptions from a model name.
    """
    name: str
    supported_tasks: frozenset[PromptTask]
    reference_image: bool = False
    localized_mask: bool = False
    identity_control: bool = False
    spatial_control: bool = False
    camera_control: bool = False


@dataclass(frozen=True)
class PreparedPrompt:
    original_prompt: str
    prepared_prompt: str
    task: PromptTask
    mode: FidelityMode
    enabled: bool
    status: PreparationStatus
    analysis: PromptAnalysis
    diagnostics: tuple[Diagnostic, ...] = ()
    local_llm_used: bool = False
    engine_profile: str = "undeclared"

    @property
    def safe_to_apply(self) -> bool:
        """Text preparation validated; NEVER a guarantee of visual compliance."""
        return self.status == PreparationStatus.PREPARED

    @property
    def requires_clarification(self) -> bool:
        return self.status == PreparationStatus.NEEDS_CLARIFICATION

    def to_dict(self) -> dict:
        result = asdict(self)
        result.update(
            schema_version=1,
            task=self.task.value,
            mode=self.mode.value,
            status=self.status.value,
            recommended_mode=RECOMMENDED_MODE.value,
            safe_to_apply=self.safe_to_apply,
            requires_clarification=self.requires_clarification,
            changed=self.prepared_prompt != self.original_prompt,
        )
        return result


@dataclass(frozen=True)
class PromptComparison:
    original_prompt: str
    legacy_prompt: str
    candidate: PreparedPrompt

    @property
    def selected_prompt(self) -> str:
        # Shadow comparison only. No silent replacement of the current preparation.
        return self.legacy_prompt

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "original_prompt": self.original_prompt,
            "legacy_prompt": self.legacy_prompt,
            "candidate": self.candidate.to_dict(),
            "selected_prompt": self.selected_prompt,
            "automatic_application": False,
            "comparison_scope": "text_only_not_visual_quality",
        }
