"""
Aurya V3 - Usando ChatBedrock oficial do langchain-aws
=======================================================

✅ Usa langchain-aws ChatBedrock (oficial e estável)
✅ LangGraph para state management
✅ PostgreSQL connection pooling
✅ LLM caching
✅ Token tracking
✅ Timing metrics

Diferença vs V2: Remove BedrockWrapper customizado, usa ChatBedrock oficial
"""

import os
from typing import Any, Dict, List, Optional, TypedDict, Annotated
from datetime import datetime
import hashlib
import time

# LangChain imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage, AIMessage

# LangGraph imports
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

# Aurya components
from src.prompts.router_prompts import prompt_router, get_example
from src.core.postgres_pool import PostgresConnector
from src.core.llm_provider import get_llm, get_provider, clear_cache as clear_llm_cache
from src.core.react_agent import ReActSQLAgent
from src.core.token_callback import TokenUsageCallback
from src.core.catalogue import build_context


# ============================================================================
# STATE DEFINITION
# ============================================================================

class AuryaState(TypedDict):
    """Estado para o workflow da Aurya com LangGraph"""
    input: str
    category: Optional[str]
    examples: Optional[str]
    messages: Annotated[List, add_messages]
    sql_query: Optional[str]
    output: Optional[str]
    timing: Dict[str, float]
    token_usage: Dict[str, Dict[str, int]]


# ============================================================================
# AURYA V3 WITH LANGGRAPH + CHATBEDROCK
# ============================================================================

class AuryaV3:
    """
    🇧🇷 Aurya V3 - ChatBedrock oficial + LangGraph

    Mudanças vs V2:
    - ✅ Usa ChatBedrock do langchain-aws (oficial)
    - ✅ Remove BedrockWrapper customizado
    - ✅ Mais estável e mantido
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._response_cache: Dict[str, Dict] = {}
        self._cache_max = 200

        provider = get_provider()
        print(f"🇧🇷 [Aurya V3] Inicializando com provider: {provider}")

        # Database (lazy — connects on first query)
        self.db = PostgresConnector.get_database()

        # LLMs via provider factory
        self.llm_fast = get_llm(role="fast", temperature=0.0, max_tokens=2048)
        self.llm_primary = get_llm(
            role="primary", temperature=0.0, max_tokens=4096,
            stop_sequences=["\nObservation"],
        )

        # SQL Agent (custom ReAct)
        self.sql_agent = ReActSQLAgent(
            llm=self.llm_primary,
            db=self.db,
            max_iterations=5,
            verbose=verbose,
        )

        # Router chain
        router_template = ChatPromptTemplate.from_messages([
            ("system", prompt_router),
            ("user", "{input}")
        ])
        self.parser = JsonOutputParser()
        self.router_chain = router_template | self.llm_fast | self.parser

        # Build LangGraph
        self.graph = self._build_graph()

        print("✅ [Aurya V3] Inicializada com sucesso!")

    async def _warmup_llms(self):
        """
        Warm up LLMs em background (inicializa sem bloquear).

        Faz uma chamada dummy para cada LLM para inicializar as credenciais.
        """
        try:
            print("[Aurya V3] ⚡ Warming up LLMs in background...")

            # Warm up Haiku (Router)
            await self.llm_fast.ainvoke([HumanMessage(content="test")])
            print("[Aurya V3] ✅ Haiku warmed up")

            # Warm up Sonnet (SQL Agent)
            await self.llm_primary.ainvoke([HumanMessage(content="test")])
            print("[Aurya V3] ✅ Sonnet warmed up")

            print("[Aurya V3] ⚡ All LLMs ready!")

        except Exception as e:
            print(f"[Aurya V3] ⚠️  Warmup failed (will init on first use): {e}")

    def _build_graph(self) -> StateGraph:
        """Constrói o grafo LangGraph"""
        workflow = StateGraph(AuryaState)

        # Adicionar nós
        workflow.add_node("router", self._router_node)
        workflow.add_node("sql_agent", self._sql_agent_node)
        workflow.add_node("format_output", self._format_output_node)

        # Adicionar arestas
        workflow.add_edge(START, "router")
        workflow.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "sql_agent": "sql_agent",
                "output": "format_output"
            }
        )
        workflow.add_edge("sql_agent", "format_output")
        workflow.add_edge("format_output", END)

        # Adicionar checkpointer para memória conversacional
        self.checkpointer = MemorySaver()
        return workflow.compile(checkpointer=self.checkpointer)

    async def _router_node(self, state: AuryaState) -> AuryaState:
        """Router node: classificar input com contexto conversacional"""
        start_time = time.time()

        if self.verbose:
            print(f"\n[Router] Processing: {state['input'][:100]}...")

        # Criar callback para tokens
        token_callback = TokenUsageCallback()

        try:
            # Construir input com contexto conversacional se existir histórico
            router_input = state["input"]

            # Se há histórico (mais de 1 mensagem), incluir contexto
            if len(state.get("messages", [])) > 1:
                previous_messages = state["messages"][:-1]  # Excluir pergunta atual
                context_summary = []

                # Incluir apenas últimas 2 interações (4 mensagens) para não sobrecarregar
                for msg in previous_messages[-4:]:
                    role = "Usuário" if msg.__class__.__name__ == "HumanMessage" else "Assistente"
                    content = msg.content[:200]  # Limitar tamanho
                    context_summary.append(f"{role}: {content}")

                if context_summary:
                    context_text = "\n".join(context_summary)
                    router_input = f"Contexto da conversa:\n{context_text}\n\nPergunta atual: {state['input']}"

                    if self.verbose:
                        print(f"[Router] Using conversation context ({len(previous_messages)} previous messages)")

            raw_response = await self.router_chain.ainvoke(
                {"input": router_input},
                config={"callbacks": [token_callback]}
            )

            state["category"] = raw_response.get("category")
            state["timing"]["router"] = time.time() - start_time
            state["token_usage"]["router"] = token_callback.get_stats()

            if self.verbose:
                print(f"[Router] Category: {state['category']}")
                print(f"[Router] Time: {state['timing']['router']:.2f}s")

            # Se for cumprimento, output direto
            if state["category"] == "greetings":
                state["output"] = raw_response.get("output")
            else:
                state["examples"] = build_context(state["category"])

        except Exception as e:
            print(f"[Router] Error: {e}")
            state["category"] = "greetings"
            state["output"] = "Olá! Como posso ajudar você hoje?"
            state["timing"]["router"] = time.time() - start_time

        return state

    def _route_decision(self, state: AuryaState) -> str:
        """Decide próximo nó"""
        return "output" if state["category"] == "greetings" else "sql_agent"

    async def _sql_agent_node(self, state: AuryaState) -> AuryaState:
        """SQL Agent node"""
        start_time = time.time()

        if self.verbose:
            print(f"\n[SQL Agent] Starting...")

        try:
            # Obter histórico de mensagens (exceto a última que é a pergunta atual)
            previous_messages = state["messages"][:-1] if len(state["messages"]) > 1 else []

            result = await self.sql_agent.run(
                question=state["input"],
                examples=state["examples"] or "",
                request_id="",
                previous_messages=previous_messages
            )

            state["output"] = result["output"]
            state["sql_query"] = result["sql_query"]
            state["timing"]["sql_agent"] = time.time() - start_time
            state["token_usage"]["sql_agent"] = result.get("token_usage", {})

            if self.verbose:
                print(f"[SQL Agent] Time: {state['timing']['sql_agent']:.2f}s")

        except Exception as e:
            print(f"[SQL Agent] Error: {e}")
            state["output"] = "Desculpe, encontrei um erro ao processar sua pergunta."
            state["timing"]["sql_agent"] = time.time() - start_time

        return state

    async def _format_output_node(self, state: AuryaState) -> AuryaState:
        """Format output and add AI response to messages"""
        # Adicionar resposta da Aurya ao histórico
        if state.get("output"):
            state["messages"].append(AIMessage(content=state["output"]))
        return state

    async def ainvoke(self, user_input: str, request_id: str = "", thread_id: str = "default") -> Dict[str, Any]:
        """
        Processa pergunta do usuário.

        Args:
            user_input: Pergunta do usuário
            request_id: ID da requisição para logging
            thread_id: ID do thread para memória conversacional (normalmente o session_id)

        Returns:
            Dict com 'output', 'sql_query', 'category', 'timing', 'token_usage'
        """
        start_time = time.time()

        # Check response cache (same question = same answer)
        cache_key = hashlib.md5(user_input.strip().lower().encode()).hexdigest()
        if cache_key in self._response_cache:
            cached = self._response_cache[cache_key]
            cached["timing"] = {"total": 0.0, "cache": "hit"}
            cached["request_id"] = request_id
            print(f"[Aurya V3] Cache HIT for: {user_input[:80]}...")
            return cached

        # Inicializar estado (messages será gerenciado pelo checkpointer)
        initial_state: AuryaState = {
            "input": user_input,
            "category": None,
            "examples": None,
            "messages": [HumanMessage(content=user_input)],  # Adicionar pergunta do usuário
            "sql_query": None,
            "output": None,
            "timing": {},
            "token_usage": {}
        }

        # Config com thread_id para memória conversacional
        config = {"configurable": {"thread_id": thread_id}}

        # Executar grafo (o checkpointer vai mesclar com o histórico existente)
        final_state = await self.graph.ainvoke(initial_state, config)

        # Timing total
        total_time = time.time() - start_time
        final_state["timing"]["total"] = total_time

        # Log summary
        print(f"\n{'='*70}")
        print(f"[Aurya V3] Request: {request_id}")
        print(f"  Router:      {final_state['timing'].get('router', 0):.2f}s")
        if 'sql_agent' in final_state['timing']:
            print(f"  SQL Agent:   {final_state['timing'].get('sql_agent', 0):.2f}s")
        print(f"  TOTAL:       {total_time:.2f}s")
        print(f"{'='*70}\n")

        result = {
            "output": final_state.get("output"),
            "sql_query": final_state.get("sql_query"),
            "category": final_state.get("category"),
            "timing": final_state.get("timing"),
            "token_usage": final_state.get("token_usage"),
            "request_id": request_id
        }

        # Cache response (skip greetings and errors)
        if result.get("output") and result.get("category") != "greetings":
            if len(self._response_cache) >= self._cache_max:
                oldest = next(iter(self._response_cache))
                del self._response_cache[oldest]
            self._response_cache[cache_key] = {k: v for k, v in result.items() if k != "request_id"}

        return result

    def clear_history(self, thread_id: str) -> bool:
        """
        Limpa o histórico conversacional de um thread específico.

        Args:
            thread_id: ID do thread para limpar histórico

        Returns:
            bool: True se limpou com sucesso, False se não havia histórico
        """
        try:
            # Acessar o storage interno do MemorySaver
            config = {"configurable": {"thread_id": thread_id}}

            # MemorySaver armazena checkpoints em self.storage (um dict)
            # Limpar todos os checkpoints para este thread_id
            if hasattr(self.checkpointer, 'storage'):
                keys_to_delete = [k for k in self.checkpointer.storage.keys() if k[0] == thread_id]
                for key in keys_to_delete:
                    del self.checkpointer.storage[key]

                if self.verbose:
                    print(f"[Aurya V3] Cleared {len(keys_to_delete)} checkpoints for thread: {thread_id}")

                return len(keys_to_delete) > 0

            return False
        except Exception as e:
            print(f"[Aurya V3] Error clearing history: {e}")
            return False


# ============================================================================
# FACTORY
# ============================================================================

def create_aurya_v3(verbose: bool = False) -> AuryaV3:
    """Cria instância da Aurya V3"""
    return AuryaV3(verbose=verbose)


def clear_all_caches():
    """Limpa todos os caches"""
    from src.core.postgres_pool import PostgresConnector

    clear_llm_cache()
    PostgresConnector.clear_pool()
    print("✅ [Aurya V3] Caches cleared")


# ============================================================================
# TEST
# ============================================================================

async def main():
    """Test Aurya V3"""
    print("AURYA V3 - ChatBedrock Oficial + LangGraph")
    print("=" * 70)

    aurya = create_aurya_v3(verbose=True)

    result = await aurya.ainvoke("Olá!", request_id="test_1")
    print(f"\nOutput: {result['output']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
