"""Published per-token prices, used to report what each call costs.

USD per million tokens: (input, cached input, output), standard tier, short
context. Embeddings have no output tokens.
"""

from __future__ import annotations

AS_OF = "2026-11-01"
SOURCES = {"openai": "https://developers.openai.com/api/docs/pricing"}

PRICES = {
    "gpt-6.1-sol": (2.00, 0.10, 10.00),
    "gpt-6.1-terra": (1.00, 0.05, 5.00),
    "gpt-6-luna": (0.10, 0.01, 0.50),
    "text-embedding-3-small": (0.02, 0.02, 0.0),
}


def price(model: str) -> tuple[float, float, float] | None:
    """Exact id, or a dated snapshot of a listed id (gpt-6.1-sol-2026-...)."""
    if model in PRICES:
        return PRICES[model]
    return next((p for m, p in PRICES.items() if model.startswith(m + "-")), None)


def cost_usd(provider: str, model: str, input_tokens: int, cached_input_tokens: int,
             output_tokens: int) -> float | None:
    if (p := price(model)) is None:
        return None
    uncached = input_tokens - cached_input_tokens
    return (uncached * p[0] + cached_input_tokens * p[1] + output_tokens * p[2]) / 1_000_000
