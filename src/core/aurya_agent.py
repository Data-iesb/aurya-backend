"""
Atena Agent — agente de consulta aos dados do SUS via Trino.
"""

import asyncio
import time
import hashlib
from typing import Any, Dict, List, Optional, TypedDict, Annotated

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from src.prompts.prompts import ROUTER_PROMPT, get_examples
from src.prompts.temas import TEMA_PREFIX, EDUCACIONAL_MODE_PROMPTS
from src.prompts.response_prompts import AURYA_SUFFIX
from src.core import iesb_rag
from src.core.trino import TrinoConnection
from src.core.llm_provider import get_llm
from src.core.react_agent import ReActSQLAgent
from src.core.token_callback import TokenUsageCallback

# Temas respondidos por RAG (sem SQL)
RAG_TEMAS = {"iesb", "educacional"}


class AgentState(TypedDict):
    input: str
    agent: Optional[str]
    mode: Optional[str]
    category: Optional[str]
    messages: Annotated[List, add_messages]
    sql_query: Optional[str]
    output: Optional[str]
    timing: Dict[str, float]
    token_usage: Dict[str, Dict[str, int]]


class AuryaAgent:
    """Atena agent — consultas aos dados do SUS."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._response_cache: Dict[str, Dict] = {}
        self._cache_max = 200

        print("🚀 [Atena] Inicializando...")

        self.db_engine = TrinoConnection.get_engine()
        self.llm_fast = get_llm(role="fast", temperature=0.0, max_tokens=2048)
        self.llm_primary = get_llm(
            role="primary", temperature=0.0, max_tokens=4096,
            stop_sequences=["\nObservation"],
        )

        self.sql_agent = _AuryaReActAgent(
            llm=self.llm_primary, db=None,
            max_iterations=15, verbose=verbose,
        )

        router_template = ChatPromptTemplate.from_messages([
            ("system", ROUTER_PROMPT),
            ("user", "{input}")
        ])
        self.parser = JsonOutputParser()
        self.router_chain = router_template | self.llm_fast | self.parser

        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()
        print("✅ [Atena] Pronta!")

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)
        workflow.add_node("router", self._router_node)
        workflow.add_node("sql_agent", self._sql_agent_node)
        workflow.add_node("rag_agent", self._rag_agent_node)
        workflow.add_node("format_output", self._format_output_node)

        workflow.add_edge(START, "router")
        workflow.add_conditional_edges(
            "router",
            lambda s: "output" if s["category"] == "greetings"
            else ("rag_agent" if s["category"] in RAG_TEMAS else "sql_agent"),
            {"sql_agent": "sql_agent", "rag_agent": "rag_agent", "output": "format_output"}
        )
        workflow.add_edge("sql_agent", "format_output")
        workflow.add_edge("rag_agent", "format_output")
        workflow.add_edge("format_output", END)
        return workflow.compile(checkpointer=self.checkpointer)

    async def _router_node(self, state: AgentState) -> AgentState:
        start = time.time()
        token_cb = TokenUsageCallback()
        try:
            fixed_agent = state.get("agent")
            if fixed_agent and (fixed_agent in TEMA_PREFIX or fixed_agent in RAG_TEMAS):
                state["category"] = fixed_agent
                state["timing"]["router"] = time.time() - start
                return state

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
            print(f"[Atena-Router] Error: {e}")
            state["category"] = "greetings"
            state["output"] = "Olá! Sou a Atena, assistente de inteligência artificial especializada em dados públicos brasileiros. Como posso ajudar?"
            state["timing"]["router"] = time.time() - start
        return state

    async def _sql_agent_node(self, state: AgentState) -> AgentState:
        start = time.time()
        try:
            tema = state.get("category", "saude")
            prev = state["messages"][:-1] if len(state["messages"]) > 1 else []

            db_wrapper = TrinoConnection.get_database(tema)
            self.sql_agent.set_tema(tema, db_wrapper)

            result = await self.sql_agent.run(
                question=state["input"], examples=get_examples(tema),
                request_id="", previous_messages=prev,
            )
            state["output"] = result["output"]
            state["sql_query"] = result["sql_query"]
            state["timing"]["sql_agent"] = time.time() - start
            state["token_usage"]["sql_agent"] = result.get("token_usage", {})
        except Exception as e:
            print(f"[Atena-SQL] Error: {e}")
            state["output"] = "Desculpe, encontrei um erro ao processar sua pergunta."
            state["timing"]["sql_agent"] = time.time() - start
        return state

    async def _rag_agent_node(self, state: AgentState) -> AgentState:
        start = time.time()
        try:
            tema = state.get("category", "iesb")
            prev = state["messages"][:-1] if len(state["messages"]) > 1 else []

            if tema == "educacional":
                prefix = EDUCACIONAL_MODE_PROMPTS.get(
                    state.get("mode") or "aluno", EDUCACIONAL_MODE_PROMPTS["aluno"]
                )
                tag = "apostilas"
            else:
                prefix = TEMA_PREFIX[tema]
                tag = "guias"

            trechos = await asyncio.to_thread(iesb_rag.search, state["input"], 4, tema)

            conversation_context = ""
            if prev:
                conversation_context = "\nHistórico da conversa:\n"
                for msg in prev[-6:]:
                    role = "Usuário" if msg.__class__.__name__ == "HumanMessage" else "Atena"
                    conversation_context += f"{role}: {msg.content}\n\n"

            prompt = (
                f"{prefix}\n\n"
                f"<{tag}>\n{trechos}\n</{tag}>\n"
                f"{conversation_context}\n"
                f"Pergunta: {state['input']}"
            )
            response = await self.llm_primary.ainvoke([HumanMessage(content=prompt)])
            state["output"] = response.content
            state["timing"]["rag_agent"] = time.time() - start
        except Exception as e:
            print(f"[Atena-RAG] Error: {e}")
            state["output"] = (
                "Desculpe, não consegui consultar os guias do IESB agora. "
                "Tente novamente em instantes."
            )
            state["timing"]["rag_agent"] = time.time() - start
        return state

    async def _format_output_node(self, state: AgentState) -> AgentState:
        if state.get("output"):
            state["messages"].append(AIMessage(content=state["output"]))
        return state

    async def ainvoke(self, user_input: str, request_id: str = "", thread_id: str = "default", agent: Optional[str] = None, mode: Optional[str] = None) -> Dict[str, Any]:
        start = time.time()

        cache_key = hashlib.md5(f"{agent or ''}:{mode or ''}:{user_input.strip().lower()}".encode()).hexdigest()
        if cache_key in self._response_cache:
            cached = self._response_cache[cache_key]
            cached["timing"] = {"total": 0.0, "cache": "hit"}
            return cached

        initial: AgentState = {
            "input": user_input, "agent": agent, "mode": mode, "category": None,
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


class _AuryaReActAgent(ReActSQLAgent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tema = "saude"

    def set_tema(self, tema: str, db_wrapper):
        """Define o tema atual e o wrapper de banco."""
        self.tema = tema
        self.db = db_wrapper

    def _build_prompt(self, question: str, examples: str, previous_messages: list = None) -> str:
        prefix = TEMA_PREFIX.get(self.tema, TEMA_PREFIX["saude"])

        system_prefix = f"""Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [sql_db_query, final_answer]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final response in plain text (tables allowed)."""

        conversation_context = ""
        if previous_messages:
            conversation_context = "\n<conversation_history>\n"
            for msg in previous_messages[-6:]:
                role = "Usuário" if msg.__class__.__name__ == "HumanMessage" else "Atena"
                conversation_context += f"{role}: {msg.content}\n\n"
            conversation_context += "</conversation_history>\n"

        return f"""{prefix}

<tools>
1. sql_db_query: Executar uma query SQL no Trino
2. final_answer: Fornecer a resposta final
</tools>

{system_prefix}

{AURYA_SUFFIX}
{conversation_context}
<examples>
{examples or ''}
</examples>

Question: {question}
"""


def create_aurya_agent(verbose: bool = False) -> AuryaAgent:
    return AuryaAgent(verbose=verbose)