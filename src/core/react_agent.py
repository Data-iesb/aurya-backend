"""
Custom ReAct SQL Agent - Full control over ReAct loop
======================================================

Implementação customizada do padrão ReAct (Reasoning + Acting) para SQL.

Vantagens sobre LangChain SQL Agent:
- Controle total sobre o loop ReAct
- Não depende de APIs instáveis do LangChain
- Parsing explícito e controlado
- Logging detalhado de cada iteração
- Token tracking via callbacks

Baseado no ReActSQLAgent do findit_example.py adaptado para PostgreSQL.
"""

import re
import asyncio
from typing import Any, Dict, Optional
from datetime import datetime
from langchain_core.messages import HumanMessage
from langchain_community.utilities import SQLDatabase

from src.prompts.react_prompts import AURYA_PREFIX, system_prefix_sql
from src.prompts.response_prompts import AURYA_SUFFIX
from src.core.token_callback import TokenUsageCallback


class ReActSQLAgent:
    """
    Custom ReAct SQL Agent implementando o padrão Reasoning + Acting.

    Loop: Question → Thought → Action → Observation → ... → Final Answer

    Args:
        llm: LangChain LLM (BedrockWrapper)
        db: SQLDatabase instance
        max_iterations: Máximo de iterações do loop ReAct (default: 5)
        verbose: Habilitar logs detalhados (default: True)
        model_id: ID do modelo para logging
    """

    def __init__(
        self,
        llm: Any,
        db: SQLDatabase,
        max_iterations: int = 5,
        verbose: bool = True,
        model_id: str = ""
    ):
        self.llm = llm
        self.db = db
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.model_id = model_id

    @staticmethod
    def _clean_output(text: str) -> str:
        return re.sub(r'(?:^|\n)\s*Thought:.*?(?=\n(?:##|[A-Z]|\|)|$)', '', text, flags=re.DOTALL | re.IGNORECASE).strip()

    async def run(self, question: str, examples: str = "", request_id: str = "", previous_messages: list = None) -> Dict[str, Any]:
        """
        Executa o loop ReAct para responder a pergunta.

        Args:
            question: Pergunta do usuário
            examples: Exemplos SQL específicos da categoria
            request_id: ID da requisição para logging
            previous_messages: Histórico de mensagens anteriores (para contexto conversacional)

        Returns:
            Dict com 'output', 'sql_query', 'iterations', 'token_usage'
        """
        # Construir prompt completo com histórico conversacional
        prompt = self._build_prompt(question, examples, previous_messages or [])

        conversation_history = []
        sql_query = None
        iterations = 0
        total_input_tokens = 0
        total_output_tokens = 0

        while iterations < self.max_iterations:
            iterations += 1

            if self.verbose:
                print(f"\n[ReAct] Iteration {iterations}/{self.max_iterations} (Request: {request_id})")

            # Construir conversa completa
            full_prompt = prompt
            if conversation_history:
                full_prompt += "\n\n" + "\n\n".join(conversation_history)

            # Chamar LLM
            try:
                llm_start = datetime.now()

                # Criar callback para capturar tokens
                token_callback = TokenUsageCallback()

                response = await self.llm.ainvoke(
                    [HumanMessage(content=full_prompt)],
                    config={"callbacks": [token_callback]}
                )
                response_text = response.content

                llm_elapsed = (datetime.now() - llm_start).total_seconds()

                # Acumular tokens
                total_input_tokens += token_callback.input_tokens
                total_output_tokens += token_callback.output_tokens

                if self.verbose:
                    print(f"[ReAct] LLM call completed: {llm_elapsed:.2f}s")
                    if token_callback.total_tokens > 0:
                        print(f"[ReAct] Tokens - Input: {token_callback.input_tokens}, "
                              f"Output: {token_callback.output_tokens}, "
                              f"Total: {token_callback.total_tokens}")

                # Parsear resposta
                thought, action, action_input = self._parse_react_response(response_text)

                if self.verbose:
                    print(f"[ReAct] Thought: {thought[:100]}...")
                    print(f"[ReAct] Action: {action}")

                if not action:
                    # LLM não seguiu formato, retornar texto diretamente
                    return {
                        "output": self._clean_output(response_text),
                        "sql_query": sql_query,
                        "iterations": iterations,
                        "token_usage": {
                            "input_tokens": total_input_tokens,
                            "output_tokens": total_output_tokens,
                            "total_tokens": total_input_tokens + total_output_tokens
                        }
                    }

                # Adicionar ao histórico
                conversation_history.append(f"Thought: {thought}")
                conversation_history.append(f"Action: {action}")
                conversation_history.append(f"Action Input: {action_input}")

                # Executar ação
                if action == "final_answer":
                    return {
                        "output": self._clean_output(action_input),
                        "sql_query": sql_query,
                        "iterations": iterations,
                        "token_usage": {
                            "input_tokens": total_input_tokens,
                            "output_tokens": total_output_tokens,
                            "total_tokens": total_input_tokens + total_output_tokens
                        }
                    }

                elif action == "sql_db_query":
                    sql_query = action_input

                    if self.verbose:
                        print(f"[ReAct] Executing SQL query...")
                        print(f"[SQL] {action_input[:300]}...")

                    db_start = datetime.now()
                    observation = await self._execute_sql(action_input)
                    db_elapsed = (datetime.now() - db_start).total_seconds()

                    if self.verbose:
                        print(f"[ReAct] SQL execution completed: {db_elapsed:.2f}s")
                        print(f"[SQL] Result length: {len(observation)} chars")

                    conversation_history.append(f"Observation: {observation}")

                else:
                    observation = f"Unknown action: {action}. Use sql_db_query or final_answer."
                    conversation_history.append(f"Observation: {observation}")

            except Exception as e:
                if self.verbose:
                    print(f"[ReAct] Error: {e}")
                return {
                    "output": f"Desculpe, encontrei um erro ao processar sua pergunta: {str(e)}",
                    "sql_query": sql_query,
                    "iterations": iterations,
                    "token_usage": {
                        "input_tokens": total_input_tokens,
                        "output_tokens": total_output_tokens,
                        "total_tokens": total_input_tokens + total_output_tokens
                    }
                }

        # Máximo de iterações atingido
        return {
            "output": "Desculpe, não consegui completar a análise dentro do limite de iterações. "
                     "Por favor, tente reformular sua pergunta de forma mais específica.",
            "sql_query": sql_query,
            "iterations": iterations,
            "token_usage": {
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "total_tokens": total_input_tokens + total_output_tokens
            }
        }

    def _build_prompt(self, question: str, examples: str, previous_messages: list = None) -> str:
        """Constrói prompt completo do ReAct com histórico conversacional"""
        # Substituir {dialect} no prefix
        prefix = AURYA_PREFIX

        # Substituir {tool_names} no system prefix
        system_prefix = system_prefix_sql.replace("{tool_names}", "sql_db_query, final_answer")

        # Construir histórico conversacional se existir
        conversation_context = ""
        if previous_messages and len(previous_messages) > 0:
            conversation_context = "\n<conversation_history>\nHistórico da conversa anterior:\n\n"
            for i, msg in enumerate(previous_messages[-6:]):  # Últimas 3 interações (6 mensagens)
                role = "Usuário" if msg.__class__.__name__ == "HumanMessage" else "Aurya"
                conversation_context += f"{role}: {msg.content}\n\n"
            conversation_context += "</conversation_history>\n"

        # Montar prompt (usar AURYA_SUFFIX diretamente, como no findit_example.py)
        prompt = f"""{prefix}

<tools>
Você tem acesso às seguintes ferramentas:

1. sql_db_query: Executar uma query SQL no Trino (datalake)
   Input: Uma query SQL válida em Trino (use layer.table, ex: gold.sus_aih)
   Output: Resultado da query

2. final_answer: Fornecer a resposta final ao usuário
   Input: Resposta formatada em markdown
   Output: Retorna a resposta ao usuário
</tools>

{system_prefix}

{AURYA_SUFFIX}
{conversation_context}
<examples>
{examples or 'Nenhum exemplo específico para esta categoria.'}
</examples>

<react_format>
Você DEVE usar o seguinte formato:

Thought: [Seu raciocínio sobre o que fazer a seguir]
Action: [Uma de: sql_db_query, final_answer]
Action Input: [O input para a ação - para sql_db_query forneça a query SQL, para final_answer forneça a resposta em markdown]
</react_format>

Question: {question}

Comece! Lembre-se de seguir o formato ReAct exatamente.
"""
        return prompt

    def _parse_react_response(self, text: str) -> tuple:
        """
        Parseia Thought, Action e Action Input da resposta do LLM.

        Returns:
            (thought, action, action_input)
        """
        thought = ""
        action = ""
        action_input = ""

        # Extrair Thought
        thought_match = re.search(
            r'Thought:\s*(.+?)(?=\nAction:|\n\n|$)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        if thought_match:
            thought = thought_match.group(1).strip()

        # Extrair Action
        action_match = re.search(r'Action:\s*(\w+)', text, re.IGNORECASE)
        if action_match:
            action = action_match.group(1).strip().lower()

        # Extrair Action Input
        action_input_match = re.search(
            r'Action Input:\s*(.+?)(?=\nObservation:|\n\n(?:Thought|Action|$)|$)',
            text,
            re.DOTALL | re.IGNORECASE
        )
        if action_input_match:
            action_input = action_input_match.group(1).strip()

            # Limpar SQL se estiver em code blocks
            if action_input.startswith('```'):
                action_input = re.sub(r'```(?:sql)?\n?', '', action_input)
                action_input = action_input.strip()

        return thought, action, action_input

    async def _execute_sql(self, sql: str) -> str:
        """
        Executa query SQL de forma assíncrona.

        Args:
            sql: Query SQL

        Returns:
            str: Resultado formatado ou mensagem de erro
        """
        try:
            # Executar em thread pool para não bloquear
            result = await asyncio.to_thread(self.db.run, sql)

            if not result:
                return "Query executada com sucesso mas não retornou resultados."

            # Limitar tamanho do resultado
            result_str = str(result)
            if len(result_str) > 5000:
                return result_str[:5000] + f"\n... (resultado truncado, {len(result_str)} chars total)"

            return result_str

        except Exception as e:
            return f"Erro ao executar query: {str(e)}"
