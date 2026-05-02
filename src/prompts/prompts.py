"""
Prompts for Aurya — multi-domain Brazilian public data.
"""

from src.prompts.router_prompts import prompt_router as ROUTER_PROMPT, CATEGORY_MAP
from src.prompts.react_prompts import AURYA_PREFIX as AGENT_PREFIX
from src.prompts.response_prompts import AURYA_SUFFIX


def get_examples(category: str) -> str:
    return CATEGORY_MAP.get(category, "")
