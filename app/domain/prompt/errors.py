"""Prompt assembly error types.

Per ADR-041, all failure modes produce explicit, typed errors.
"""


class PromptAssemblyError(Exception):
    """Base class for prompt assembly errors."""

    pass


class UnresolvedTokenError(PromptAssemblyError):
    """Workflow Token has no matching include in the workflow's includes map.
    
    Raised when a $$SECTION_NAME token is found in the template but
    the workflow node's includes map does not contain a matching key.
    """

    def __init__(self, token: str):
        self.token = token
        super().__init__(f"Unresolved token: $${token}")


class IncludeNotFoundError(PromptAssemblyError):
    """Include file does not exist at the specified path.
    
    Raised when either:
    - A Workflow Token's include path points to a non-existent file
    - A Template Include ($$include <path>) references a non-existent file
    """

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Include file not found: {path}")


class NestedTokenError(PromptAssemblyError):
    """Include file contains tokens, which is prohibited.
    
    Per ADR-041, include files MUST NOT contain unresolved tokens.
    This prevents recursive includes and maintains single-pass assembly.
    """

    def __init__(self, path: str, token: str):
        self.path = path
        self.token = token
        super().__init__(f"Nested token $${token} found in {path}")


class EncodingError(PromptAssemblyError):
    """File is not valid UTF-8.
    
    Per ADR-041, all include files MUST be UTF-8 encoded (no BOM).
    """

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Invalid UTF-8 encoding: {path}")