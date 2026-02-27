"""
LLM Response Parser - Extract JSON from LLM responses using multiple strategies.

This module provides parsing strategies to extract JSON artifacts from varied LLM
output formats including clean JSON, markdown fences, and text with explanations.

Author: D-1 (Senior Developer)
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Sequence, Protocol
import json
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class ParseResult:
    """Result of parsing attempt with diagnostics."""
    success: bool
    data: Optional[Dict[str, Any]]
    strategy_used: Optional[str]
    error_messages: List[str]


class ParsingStrategy(Protocol):
    """Protocol for parsing strategies."""
    
    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to parse JSON from text.
        
        Returns:
            Parsed dict on success, None on failure
            
        Raises:
            Never raises - returns None on any error
        """
        ...


class DirectParseStrategy:
    """Attempt direct json.loads() on full text."""
    
    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON directly from text after stripping common prefixes."""
        try:
            # Strip whitespace and common prefixes
            text = text.strip()
            prefixes = ["Here is the JSON:", "Result:", "Output:", "Here is the result:"]
            for prefix in prefixes:
                if text.startswith(prefix):
                    text = text[len(prefix):].strip()
            
            return json.loads(text)
        except (json.JSONDecodeError, ValueError, TypeError):
            return None


class MarkdownFenceStrategy:
    """Extract JSON from markdown code fences."""
    
    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON from markdown code fences (```json or ```)."""
        # Match ```json or ``` followed by JSON
        pattern = r'```(?:json)?\s*\n(.*?)\n```'
        matches = re.findall(pattern, text, re.DOTALL)
        
        if not matches:
            return None
        
        # If multiple fences, try largest first
        matches_sorted = sorted(matches, key=len, reverse=True)
        
        for match in matches_sorted:
            try:
                return json.loads(match.strip())
            except (json.JSONDecodeError, ValueError, TypeError):
                continue
        
        return None


class FuzzyBoundaryStrategy:
    """Find first { to last } and attempt parse."""
    
    def parse(self, text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON by finding first { to last }."""
        first_brace = text.find('{')
        last_brace = text.rfind('}')
        
        if first_brace == -1 or last_brace == -1:
            return None
        
        json_text = text[first_brace:last_brace + 1]
        
        try:
            return json.loads(json_text)
        except (json.JSONDecodeError, ValueError, TypeError):
            return None


class LLMResponseParser:
    """Parse JSON artifacts from LLM responses using multiple strategies."""
    
    def __init__(self, strategies: Optional[Sequence[ParsingStrategy]] = None):
        """
        Initialize parser with parsing strategies.
        
        Args:
            strategies: Ordered list of strategies to try. If None, uses default:
                       [DirectParseStrategy, MarkdownFenceStrategy, FuzzyBoundaryStrategy]
                       
        Raises:
            ValueError: If strategies list is empty
        """
        if strategies is None:
            strategies = [
                DirectParseStrategy(),
                MarkdownFenceStrategy(),
                FuzzyBoundaryStrategy()
            ]
        
        if not strategies:
            raise ValueError("Parser requires at least one strategy")
        
        self._strategies = list(strategies)
        logger.debug(f"Parser initialized with {len(self._strategies)} strategies")
    
    def parse(self, response_text: str) -> ParseResult:
        """
        Extract JSON from LLM response text.
        
        Tries strategies in configured order until one succeeds.
        
        Args:
            response_text: Raw text from LLM
            
        Returns:
            ParseResult with success status and data or errors
            
        Raises:
            Never raises - all errors captured in ParseResult
        """
        if not isinstance(response_text, str):
            return ParseResult(
                success=False,
                data=None,
                strategy_used=None,
                error_messages=["Invalid input: expected string"]
            )
        
        if not response_text.strip():
            return ParseResult(
                success=False,
                data=None,
                strategy_used=None,
                error_messages=["Empty response text"]
            )
        
        errors = []
        
        for strategy in self._strategies:
            strategy_name = strategy.__class__.__name__
            logger.debug(f"Attempting parse with {strategy_name}")
            
            try:
                result = strategy.parse(response_text)
                if result is not None:
                    logger.debug(f"Parse succeeded using {strategy_name}")
                    return ParseResult(
                        success=True,
                        data=result,
                        strategy_used=strategy_name,
                        error_messages=[]
                    )
                else:
                    logger.debug(f"{strategy_name} returned None")
            except Exception as e:
                error_msg = f"{strategy_name}: {str(e)}"
                errors.append(error_msg)
                logger.debug(f"Parse failed with {strategy_name}: {str(e)}")
        
        return ParseResult(
            success=False,
            data=None,
            strategy_used=None,
            error_messages=errors if errors else ["All strategies failed"]
        )