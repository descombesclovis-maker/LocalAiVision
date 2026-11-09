"""V2-A opt-in, generator-independent prompt understanding/preparation.

Importing this package does not import DB/generators, open connections or read settings.
Existing generation paths deliberately do not use this experimental component yet.
"""
from .adapters import COMFY_IMAGE, COMFY_VIDEO
from .engine import compare_preparations, prepare_prompt
from .local_llm import LocalAnalyzer, LocalLLMConfig, NonLocalEndpoint
from .types import (
    RECOMMENDED_MODE, Diagnostic, EngineCapabilities, FidelityMode, PreparationStatus,
    PreparedPrompt, PromptAnalysis, PromptComparison, PromptTask,
)

__all__ = [
    "COMFY_IMAGE", "COMFY_VIDEO", "RECOMMENDED_MODE", "Diagnostic", "EngineCapabilities",
    "FidelityMode", "LocalAnalyzer", "LocalLLMConfig", "NonLocalEndpoint", "PreparationStatus", "PreparedPrompt",
    "PromptAnalysis", "PromptComparison", "PromptTask", "compare_preparations", "prepare_prompt",
]
