"""
Prompts for Aurya — multi-domain Brazilian public data.
"""

from src.prompts.router_prompts import prompt_router as ROUTER_PROMPT, CATEGORY_MAP


def get_examples(category: str) -> str:
    return CATEGORY_MAP.get(category, "")
