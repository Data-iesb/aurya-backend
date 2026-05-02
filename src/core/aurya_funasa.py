"""
Aurya FUNASA — isolated agent for FUNASA site. Saude only, gold.sus_aih only.
"""

import time
import hashlib
from typing import Any, Dict, List, Optional, TypedDict, Annotated

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from src.prompts.funasa_prompts import FUNASA_ROUTER_PROMPT, FUNASA_PREFIX, FUNASA_EXAMPLES
from src.prompts.response_prompts import AURYA_SUFFIX
from src.core.trino_funasa import TrinoFunasa
from src.core.llm_provider import get_llm
from src.core.react_agent import ReActSQLAgent
from src.core.token_callback import TokenUsageCallback


class FunasaState(TypedDict):
    input: str
    category: Optional[str]
    messages: Annotated[List, add_messages]
    sql_query: Optional[str]
    output: Optional[str]
    timing: Dict[str, float]
    token_usage: Dict[str, Dict[str, int]]


class AuryaFunasa:
    """Aurya agent isolated for FUNASA — only saude domain, only gold.sus_aih."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._response_cache: Dict[str, Dict] = {}
        self._cache_max = 200

        print("🏥 [Aurya-FUNASA] Inicializando...")

        self.db = TrinoFunasa.get_database()
        self.llm_fast = get_llm(role="fast", temperature=0.0, max_tokens=2048)
        self.llm_primary = get_llm(
            role="primary", temperature=0.0, max_tokens=4096,
            stop_sequences=["\nObservation"],
        )

        # SQL Agent with FUNASA-specific prompts injected via subclass override
        self.sql_agent = _FunasaReActAgent(
            llm=self.llm_primary, db=self.db,
            max_iterations=5, verbose=verbose,
        )

        router_template = ChatPromptTemplate.from_messages([
            ("system", FUNASA_ROUTER_PROMPT),
            ("user", "{input}")
        ])
        self.parser = JsonOutputParser()
        self.router_chain = router_template | self.llm_fast | self.parser

        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()
        print("✅ [Aurya-FUNASA] Pronta!")

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(FunasaState)
        workflow.add_node("router", self._router_node)
        workflow.add_node("sql_agent", self._sql_agent_node)
        workflow.add_node("format_output", self._format_output_node)

        workflow.add_edge(START, "router")
        workflow.add_conditional_edges(
            "router",
            lambda s: "output" if s["category"] == "greetings" else "sql_agent",
            {"sql_agent": "sql_agent", "output": "format_output"}
        )
        workflow.add_edge("sql_agent", "format_output")
        workflow.add_edge("format_output", END)
        return workflow.compile(checkpointer=self.checkpointer)

    async def _router_node(self, state: FunasaState) -> FunasaState:
        start = time.time()
        token_cb = TokenUsageCallback()
        try:
            router_input = state["input"]
            if len(state.get("messages", [])) > 1:
                prev = state["messages"][:-1]
                ctx = "\n".join(
                    f"{'Usuário' if m.__class__.__name__ == 'HumanMessage' else 'Assistente'}: {m.content[:200]}"
                    for m in prev[-4:]
                )
                if ctx:
                    router_input = f"Contexto da conversa:\n{ctx}\n\nPergunta atual: {state['input']}"

            raw = await self.router_chain.ainvoke(
                {"input": router_input}, config={"callbacks": [token_cb]}
            )
            state["category"] = raw.get("category")
            state["timing"]["router"] = time.time() - start
            state["token_usage"]["router"] = token_cb.get_stats()

            if state["category"] == "greetings":
                state["output"] = raw.get("output")
        except Exception as e:
            print(f"[FUNASA-Router] Error: {e}")
            state["category"] = "greetings"
            state["output"] = "Olá! Sou a Aurya da FUNASA. Como posso ajudar com dados do SUS?"
            state["timing"]["router"] = time.time() - start
        return state

    async def _sql_agent_node(self, state: FunasaState) -> FunasaState:
        start = time.time()
        try:
            prev = state["messages"][:-1] if len(state["messages"]) > 1 else []
            result = await self.sql_agent.run(
                question=state["input"], examples=FUNASA_EXAMPLES,
                request_id="", previous_messages=prev,
            )
            state["output"] = result["output"]
            state["sql_query"] = result["sql_query"]
            state["timing"]["sql_agent"] = time.time() - start
            state["token_usage"]["sql_agent"] = result.get("token_usage", {})
        except Exception as e:
            print(f"[FUNASA-SQL] Error: {e}")
            state["output"] = "Desculpe, encontrei um erro ao processar sua pergunta."
            state["timing"]["sql_agent"] = time.time() - start
        return state

    async def _format_output_node(self, state: FunasaState) -> FunasaState:
        if state.get("output"):
            state["messages"].append(AIMessage(content=state["output"]))
        return state

    async def ainvoke(self, user_input: str, request_id: str = "", thread_id: str = "default") -> Dict[str, Any]:
        start = time.time()

        cache_key = hashlib.md5(user_input.strip().lower().encode()).hexdigest()
        if cache_key in self._response_cache:
            cached = self._response_cache[cache_key]
            cached["timing"] = {"total": 0.0, "cache": "hit"}
            return cached

        initial: FunasaState = {
            "input": user_input, "category": None,
            "messages": [HumanMessage(content=user_input)],
            "sql_query": None, "output": None,
            "timing": {}, "token_usage": {},
        }

        final = await self.graph.ainvoke(initial, {"configurable": {"thread_id": thread_id}})
        final["timing"]["total"] = time.time() - start

        result = {
            "output": final.get("output"),
            "sql_query": final.get("sql_query"),
            "category": final.get("category"),
            "timing": final.get("timing"),
            "token_usage": final.get("token_usage"),
        }

        if result.get("output") and result.get("category") != "greetings":
            if len(self._response_cache) >= self._cache_max:
                del self._response_cache[next(iter(self._response_cache))]
            self._response_cache[cache_key] = {k: v for k, v in result.items()}

        return result


class _FunasaReActAgent(ReActSQLAgent):
    """Override _build_prompt to use FUNASA-specific prefix."""

    def _build_prompt(self, question: str, examples: str, previous_messages: list = None) -> str:
        system_prefix = "Use the following format:\n\nQuestion: the input question you must answer\nThought: you should always think about what to do\nAction: the action to take, should be one of [sql_db_query, final_answer]\nAction Input: the input to the action\nObservation: the result of the action\n... (this Thought/Action/Action Input/Observation can repeat N times)\nThought: I now know the final answer\nFinal Answer: the final response formatted in markdown.\n"

        conversation_context = ""
        if previous_messages:
            conversation_context = "\n<conversation_history>\n"
            for msg in previous_messages[-6:]:
                role = "Usuário" if msg.__class__.__name__ == "HumanMessage" else "Aurya"
                conversation_context += f"{role}: {msg.content}\n\n"
            conversation_context += "</conversation_history>\n"

        return f"""{FUNASA_PREFIX}

<tools>
1. sql_db_query: Execute a Trino SQL query on gold.sus_aih
2. final_answer: Provide the final markdown answer
</tools>

{system_prefix}

{AURYA_SUFFIX}
{conversation_context}
<examples>
{examples or ''}
</examples>

Question: {question}
"""


def create_aurya_funasa(verbose: bool = False) -> AuryaFunasa:
    return AuryaFunasa(verbose=verbose)
