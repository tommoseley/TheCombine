"""LLM API pricing utilities."""
import logging
from app.core.config import Settings

logger = logging.getLogger(__name__)

# Cache settings instance to avoid recreating on every call
_settings = None

def _get_settings():
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def calculate_cost(input_tokens: int, output_tokens: int, model: str = "claude-sonnet-4") -> float:
    """Calculate USD cost from token usage.

    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: Model identifier

    Returns:
        Cost in USD (6 decimal places)
    """
    if input_tokens < 0 or output_tokens < 0:
        logger.warning(f"Invalid token counts: input={input_tokens}, output={output_tokens}")
        return 0.0

    try:
        settings = _get_settings()
        input_price_per_mtk = settings.ANTHROPIC_INPUT_PRICE_PER_MTK
        output_price_per_mtk = settings.ANTHROPIC_OUTPUT_PRICE_PER_MTK
    except Exception as e:
        # Fallback to hardcoded defaults if settings unavailable (e.g., in tests)
        logger.warning(f"Could not load settings, using defaults: {e}")
        input_price_per_mtk = 3.0
        output_price_per_mtk = 15.0

    if "claude" not in model.lower():
        logger.warning(f"Unknown model '{model}', using default Anthropic pricing")

    input_cost = (input_tokens / 1_000_000) * input_price_per_mtk
    output_cost = (output_tokens / 1_000_000) * output_price_per_mtk
    total_cost = input_cost + output_cost

    return round(total_cost, 6)
