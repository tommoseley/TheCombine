"""Prompt assembly domain module.

Implements ADR-041: Prompt Template Include System.
"""

from app.domain.prompt.assembler import AssembledPrompt, PromptAssembler
from app.domain.prompt.errors import (
    PromptAssemblyError,
    UnresolvedTokenError,
    IncludeNotFoundError,
    NestedTokenError,
    EncodingError,
)

__all__ = [
    "AssembledPrompt",
    "PromptAssembler",
    "PromptAssemblyError",
    "UnresolvedTokenError",
    "IncludeNotFoundError",
    "NestedTokenError",
    "EncodingError",
]