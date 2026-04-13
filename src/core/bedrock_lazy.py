"""
Bedrock LLM Lazy Initialization - Evita timeout no startup
===========================================================

Problema: ChatBedrock valida credenciais no __init__, causando timeout

Solução: Criar wrapper que adia inicialização até primeira chamada
"""

import os
import asyncio
from typing import Optional, Any, List
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_aws import ChatBedrock
from botocore.exceptions import ClientError


class LazyChatBedrock(Runnable):
    """
    Wrapper para ChatBedrock com lazy initialization.

    Só cria o ChatBedrock de verdade quando ainvoke() é chamado pela primeira vez.
    Isso evita timeout no startup.
    """

    def __init__(
        self,
        model_id: str,
        region_name: str = "us-east-1",
        model_kwargs: Optional[dict] = None,
        max_retries: int = 3,
        initial_retry_delay: float = 1.0
    ):
        # Armazenar parâmetros sem criar o ChatBedrock ainda
        self.model_id = model_id
        self.region_name = region_name
        self.model_kwargs = model_kwargs or {}
        self._llm: Optional[ChatBedrock] = None
        self._initialized = False

        # Retry configuration
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay

        print(f"[LazyChatBedrock] Configured (not initialized): {model_id}")

    def _ensure_initialized(self):
        """Inicializa ChatBedrock apenas quando necessário"""
        if not self._initialized:
            print(f"[LazyChatBedrock] Initializing on first use: {self.model_id}")

            self._llm = ChatBedrock(
                model_id=self.model_id,
                region_name=self.region_name,
                model_kwargs=self.model_kwargs
            )

            self._initialized = True
            print(f"[LazyChatBedrock] ✅ Initialized: {self.model_id}")

    def invoke(self, input: Any, config: Optional[RunnableConfig] = None, **kwargs) -> Any:
        """Runnable interface - sync invoke"""
        self._ensure_initialized()
        return self._llm.invoke(input, config=config, **kwargs)

    async def ainvoke(self, input: Any, config: Optional[RunnableConfig] = None, **kwargs) -> Any:
        """Runnable interface - async invoke with retry logic"""
        self._ensure_initialized()
        return await self._ainvoke_with_retry(input, config=config, **kwargs)

    async def _ainvoke_with_retry(self, input: Any, config: Optional[RunnableConfig] = None, **kwargs) -> Any:
        """
        Invoke com retry exponential backoff para ThrottlingException.

        Tenta até max_retries vezes, esperando progressivamente mais tempo:
        - Tentativa 1: imediato
        - Tentativa 2: espera 1s
        - Tentativa 3: espera 2s
        - Tentativa 4: espera 4s
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                result = await self._llm.ainvoke(input, config=config, **kwargs)

                # Se conseguiu, retorna
                if attempt > 0:
                    print(f"[LazyChatBedrock] ✅ Retry successful on attempt {attempt + 1}")

                return result

            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', '')

                # Só faz retry para ThrottlingException
                if error_code == 'ThrottlingException':
                    last_exception = e

                    if attempt < self.max_retries - 1:
                        # Exponential backoff: 1s, 2s, 4s
                        delay = self.initial_retry_delay * (2 ** attempt)
                        print(f"[LazyChatBedrock] ⚠️ ThrottlingException on attempt {attempt + 1}/{self.max_retries}")
                        print(f"[LazyChatBedrock] ⏳ Waiting {delay}s before retry...")
                        await asyncio.sleep(delay)
                    else:
                        print(f"[LazyChatBedrock] ❌ Max retries reached ({self.max_retries})")
                        raise
                else:
                    # Outros erros não fazem retry
                    print(f"[LazyChatBedrock] ❌ Non-retryable error: {error_code}")
                    raise

            except Exception as e:
                # Erros não-ClientError também não fazem retry
                print(f"[LazyChatBedrock] ❌ Unexpected error: {type(e).__name__}")
                raise

        # Se chegou aqui, esgotou tentativas
        if last_exception:
            raise last_exception

    @property
    def InputType(self):
        """Required by Runnable"""
        return Any

    @property
    def OutputType(self):
        """Required by Runnable"""
        return Any


class BedrockLLMCache:
    """Cache para LazyChatBedrock (thread-safe)"""

    _cache = {}

    @classmethod
    def get_or_create_llm(
        cls,
        model_id: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        region: str = "us-east-1",
        **kwargs
    ) -> LazyChatBedrock:
        """
        Retorna LazyChatBedrock cached.

        Importante: NÃO inicializa o ChatBedrock real aqui!
        """
        cache_key = (model_id, temperature, max_tokens, region)

        if cache_key not in cls._cache:
            print(f"[BedrockCache] Creating lazy wrapper: {model_id}")

            llm = LazyChatBedrock(
                model_id=model_id,
                region_name=region,
                model_kwargs={
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    **kwargs.get("model_kwargs", {})
                }
            )

            cls._cache[cache_key] = llm
            print(f"[BedrockCache] ✅ Cached (lazy): {model_id}")
        else:
            print(f"[BedrockCache] ♻️  Reusing cached: {model_id}")

        return cls._cache[cache_key]

    @classmethod
    def clear_cache(cls):
        """Limpa cache"""
        cls._cache.clear()
        print("[BedrockCache] Cache cleared")

    @classmethod
    def get_cache_stats(cls) -> dict:
        """Estatísticas"""
        return {
            "cached_llms": len(cls._cache),
            "initialized_llms": sum(1 for llm in cls._cache.values() if llm._initialized)
        }
