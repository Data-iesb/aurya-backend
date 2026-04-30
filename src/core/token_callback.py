"""
Token Usage Callback - Captura métricas de uso de tokens dos LLMs
===================================================================

Permite rastreamento detalhado de tokens para:
- Debugging
- Cost tracking
- Performance monitoring
"""

from typing import Any
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.outputs import LLMResult


class TokenUsageCallback(AsyncCallbackHandler):
    """
    Callback handler para capturar uso de tokens das respostas LLM.

    Usage:
        callback = TokenUsageCallback()
        response = await llm.ainvoke(messages, config={"callbacks": [callback]})
        print(f"Tokens: {callback.total_tokens}")
    """

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.model_id = ""

    async def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        """Captura uso de tokens quando LLM completa"""
        if response.llm_output and "usage" in response.llm_output:
            usage = response.llm_output["usage"]
            self.input_tokens = usage.get("input_tokens", 0)
            self.output_tokens = usage.get("output_tokens", 0)
            self.total_tokens = usage.get("total_tokens", 0)
            self.model_id = response.llm_output.get("model_id", "")

    def reset(self):
        """Reset contadores para nova requisição"""
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.model_id = ""

    def get_stats(self) -> dict:
        """Retorna estatísticas de uso"""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "model_id": self.model_id
        }
