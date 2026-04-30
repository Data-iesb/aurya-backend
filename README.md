# Aurya — Agente de Dados do SUS (FUNASA)

Agente conversacional que responde perguntas sobre dados públicos de saúde do SUS usando linguagem natural. Converte perguntas em SQL, executa no datalake via Trino e retorna respostas formatadas.

## Arquitetura

```
Usuário (WebSocket)
    │
    ▼
┌─────────────────────────────────────────────┐
│  FastAPI (main_v3.py)                       │
│  ├── WebSocket /ws/{session_id}             │
│  ├── Sessions + concurrency control         │
│  └── LangGraph state management             │
├─────────────────────────────────────────────┤
│  Aurya V3 (aurya_v3.py)                     │
│  ├── Router Node    → classifica a pergunta │
│  ├── SQL Agent Node → gera e executa SQL    │
│  └── Format Node    → formata resposta      │
├─────────────────────────────────────────────┤
│  LLM Provider (llm_provider.py)             │
│  ├── Gemini (default)                       │
│  └── Bedrock (fallback)                     │
├─────────────────────────────────────────────┤
│  Trino (postgres_pool.py)                   │
│  └── seaweedfs catalog → bronze/silver/gold │
└─────────────────────────────────────────────┘
```

### Fluxo de uma pergunta

1. **Router** (LLM rápido) — classifica: `greetings` ou `saude`
2. Se `greetings` → resposta direta
3. Se `saude` → **ReAct SQL Agent** (LLM principal):
   - Pensa sobre a pergunta
   - Gera query SQL (Trino)
   - Executa no datalake
   - Observa resultado
   - Repete se necessário (até 5 iterações)
   - Formata resposta final em Markdown

## Datalake — Arquitetura Medalhão

```
SQL Server (fonte)          SeaweedFS (S3-compatible storage)
    │                           │
    │  Trino sqlserver catalog  │  Trino seaweedfs catalog
    │                           │
    ▼                           ▼
┌──────────┐  CTAS   ┌──────────────────────────────────────┐
│ dbo.*    │ ──────► │  bronze.*    dados brutos (Parquet)  │
└──────────┘         │  silver.*    limpos e tipados        │
                     │  gold.*      prontos para consumo    │
                     └──────────────────────────────────────┘
                                    ▲
                                    │
                              Aurya consulta aqui
```

### Camadas

| Camada | Schema | Regra | Uso |
|--------|--------|-------|-----|
| **Bronze** | `bronze.*` | Cópia fiel da fonte. Nunca alterar. | Lineage, reprocessamento |
| **Silver** | `silver.*` | Limpo, tipado, padronizado. | Análise detalhada |
| **Gold** | `gold.*` | Curado, enriquecido, colunas legíveis. | **Agente usa por padrão** |

### Tabela principal: `gold.sus_aih`

Dados mensais de procedimentos hospitalares do SUS (AIH/DATASUS), agregados por município.

- **108.224 linhas** | Anos: 2019, 2025 | 27 UFs | ~5.300 municípios
- Cada linha = 1 município em 1 mês

**Colunas principais:**

| Coluna | Tipo | Descrição |
|--------|------|-----------|
| `ano`, `mes` | INTEGER | Período |
| `municipio`, `uf`, `regiao` | VARCHAR | Geografia |
| `capital` | BOOLEAN | Se é capital |
| `qtd_total` | INTEGER | Total de procedimentos |
| `vl_total` | DOUBLE | Valor total (R$) |
| `qtd_clinico`, `qtd_cirurgico`, `qtd_diagnostico`... | INTEGER | Quantidade por grupo |
| `vl_clinico`, `vl_cirurgico`, `vl_diagnostico`... | DOUBLE | Valor por grupo (R$) |
| `qtd_oncologia`, `qtd_nefrologia`, `qtd_fisioterapia`... | INTEGER | Subgrupos clínicos |

### Catálogos Trino

| Catálogo | Conector | Descrição |
|----------|----------|-----------|
| `seaweedfs` | Hive (S3) | Datalake medalhão (bronze/silver/gold) |
| `sqlserver` | SQL Server | Fonte original (FUNASA SQL Server) |
| `tpch` | TPC-H | Benchmark/testes |

### Ingestão (SQL Server → Bronze)

```sql
-- Via Trino (sem scripts Python)
CREATE TABLE bronze.sus_aih WITH (format = 'PARQUET') AS
SELECT * FROM sqlserver.dbo.sus_aih;
```

## LLM Provider

Troca de modelo via variável de ambiente — sem alterar código.

| Provider | `LLM_PROVIDER` | Modelos default | Requer |
|----------|----------------|-----------------|--------|
| **Gemini** | `gemini` | flash-lite (router), flash (agent) | `GOOGLE_API_KEY` |
| **Bedrock** | `bedrock` | Haiku 3.5 (router), Haiku 4.5 (agent) | AWS credentials |

Override de modelos:
```bash
FAST_MODEL=gemini-2.0-flash-lite    # router
PRIMARY_MODEL=gemini-2.0-flash       # sql agent
```

## Setup local

### 1. Instalar dependências

```bash
pip install -r src/requirements.txt
```

### 2. Configurar `.env`

Criar `src/.env`:

```env
# LLM
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# Trino
TRINO_HOST=trino.dataiesb.com
TRINO_PORT=443
TRINO_USER=admin
TRINO_PASSWORD=...
TRINO_CATALOG=seaweedfs
```

### 3. Iniciar

```bash
./start.sh
```

### 4. Testar

```bash
python3 test_api.py
```

## API

| Endpoint | Método | Descrição |
|----------|--------|-----------|
| `/` | GET | Info do serviço |
| `/health` | GET | Health check |
| `/sessions` | GET | Sessões ativas |
| `/ws/{session_id}` | WebSocket | Chat (enviar JSON com `input_string`) |
| `/reset_history/` | POST | Limpar histórico de sessão |
| `/feedback/` | POST | Enviar feedback |
| `/cache-stats` | GET | Estatísticas de cache |
| `/cache-clear` | POST | Limpar caches |

### WebSocket — formato de mensagem

```json
// Enviar
{"input_string": "Qual o gasto do SUS por região?", "message_id": "msg-1"}

// Receber
{
  "answer": "## Gasto por região\n| Região | Valor |...",
  "query": "SELECT regiao, SUM(vl_total)...",
  "category": "saude",
  "timing": {"router": 0.5, "sql_agent": 3.2, "total": 3.7},
  "message_id": "msg-1"
}
```

## Deploy (Kubernetes)

```bash
# Aplicar manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/serviceaccount.yaml
kubectl apply -f k8s/backend.yaml
kubectl apply -f k8s/ingress.yaml
```

## Estrutura do projeto

```
src/
├── api/
│   └── main_v3.py              # FastAPI + WebSocket
├── core/
│   ├── aurya_v3.py             # Agente principal (LangGraph)
│   ├── react_agent.py          # ReAct loop (Thought→Action→Observation)
│   ├── llm_provider.py         # Factory: Gemini / Bedrock
│   ├── bedrock_lazy.py         # Wrapper lazy para Bedrock
│   ├── postgres_pool.py        # Conexão Trino (SQLAlchemy)
│   └── token_callback.py       # Tracking de tokens
├── prompts/
│   ├── react_prompts.py        # Prompt do agente SQL (schema, regras)
│   ├── router_prompts.py       # Prompt do classificador
│   ├── temas.py                # Exemplos de queries por tema
│   ├── response_prompts.py     # Regras de formatação
│   └── prompt_base.py          # Composição dos prompts
├── requirements.txt
└── .env

k8s/
├── backend.yaml                # Deployment + Service
├── configmap.yaml              # Env vars
├── ingress.yaml                # Ingress rules
├── namespace.yaml
└── serviceaccount.yaml

start.sh                        # Iniciar servidor local
test_api.py                     # Testes HTTP + WebSocket
```
