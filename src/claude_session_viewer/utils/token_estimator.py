"""Token estimation and cost calculation utilities."""


# Per 1M tokens (as of Feb 2026)
MODEL_COSTS: dict[str, dict[str, float]] = {
    "claude-opus-4-6":   {"input": 15.00, "output": 75.00, "cache_read": 1.50, "cache_create": 18.75},
    "claude-sonnet-4-5": {"input": 3.00,  "output": 15.00, "cache_read": 0.30, "cache_create": 3.75},
    "claude-haiku-4-5":  {"input": 0.80,  "output": 4.00,  "cache_read": 0.08, "cache_create": 1.00},
}


def estimate_tokens(text: str) -> int:
    """Estimate token count from text using ~4 chars per token heuristic."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def estimate_tokens_for_content(content) -> int:
    """Estimate tokens for message content (string or list of content blocks)."""
    if isinstance(content, str):
        return estimate_tokens(content)
    if isinstance(content, list):
        total = 0
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    total += estimate_tokens(block.get("text", ""))
                elif block.get("type") == "thinking":
                    total += estimate_tokens(block.get("thinking", ""))
                elif block.get("type") == "tool_use":
                    total += estimate_tokens(str(block.get("input", {})))
                elif block.get("type") == "tool_result":
                    result_content = block.get("content", "")
                    if isinstance(result_content, str):
                        total += estimate_tokens(result_content)
                    elif isinstance(result_content, list):
                        for item in result_content:
                            if isinstance(item, dict):
                                total += estimate_tokens(item.get("text", ""))
            elif isinstance(block, str):
                total += estimate_tokens(block)
        return total
    return 0


def _match_model(model: str) -> dict[str, float] | None:
    """Match a model string to its cost entry by prefix."""
    if not model:
        return None
    for prefix, costs in MODEL_COSTS.items():
        if model.startswith(prefix):
            return costs
    # Try partial matches (e.g., "claude-sonnet-4-5-20250929")
    for prefix, costs in MODEL_COSTS.items():
        base = prefix.rsplit("-", 1)[0]  # e.g., "claude-opus-4"
        if model.startswith(base):
            return costs
    return None


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    cache_read_tokens: int,
    cache_creation_tokens: int,
    model: str,
) -> float:
    """Calculate cost in USD for the given token counts and model."""
    costs = _match_model(model)
    if not costs:
        return 0.0
    return (
        input_tokens * costs["input"]
        + output_tokens * costs["output"]
        + cache_read_tokens * costs["cache_read"]
        + cache_creation_tokens * costs["cache_create"]
    ) / 1_000_000
