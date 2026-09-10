# Aurya — Agente de Dados do SUS (FUNASA)

Agente conversacional que responde perguntas sobre dados públicos de saúde do SUS usando linguagem natural. Converte perguntas em SQL, executa no datalake via Trino e retorna respostas formatadas.

## Arquitetura

```
Usuário (WebSocket)
    │
    ▼
┌─────────────────────────────────────────────┐
│  FastAPI (main.py)                          │
│  ├── WebSocket /ws/{session_id}             │
│  ├── Sessions + concurrency control         │
│  └── API Key auth (x-api-key header)        │
├─────────────────────────────────────────────┤
│  Aurya FUNASA (aurya_funasa.py)             │
│  ├── Router Node    → classifica a pergunta │
│  ├── SQL Agent Node → gera e executa SQL    │
│  └── Format Node    → formata resposta      │
├─────────────────────────────────────────────┤
│  LLM Provider (llm_provider.py)             │
│  ├── Gemini (default)                       │
│  └── Bedrock (fallback)                     │
├─────────────────────────────────────────────┤
│  Trino FUNASA (trino_funasa.py)             │
│  └── catalog isolado → gold.sus_aih apenas  │
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

## Datalake — Tabela `gold.sus_aih`

Dados mensais de procedimentos hospitalares do SUS (AIH/DATASUS), agregados por município.

- **445.613 linhas** | Anos: 2019-2025 | 27 UFs | ~5.300 municípios
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

## API

| Endpoint | Método | Auth | Descrição |
|----------|--------|------|-----------|
| `/` | GET | Não | Info do serviço |
| `/health` | GET | Não | Health check |
| `/ws/{session_id}` | WebSocket | Sim | Chat (enviar JSON com `input_string`) |
| `/reset_history/` | POST | Sim | Limpar histórico de sessão |
| `/feedback/` | POST | Sim | Enviar feedback |

### Autenticação

Todas as rotas (exceto `/` e `/health`) exigem API key:

```bash
# Via header
curl -H "x-api-key: SUA_CHAVE" https://api.dataiesb.com/aurya/sessions

# Via query param
curl https://api.dataiesb.com/aurya/sessions?api_key=SUA_CHAVE
```

### Exemplo — WebSocket

```python
import asyncio, json, websockets

API_KEY = ""  # Solicite a chave de acesso

async def ask(question):
    url = f"wss://api.dataiesb.com/aurya/ws/minha-sessao?api_key={API_KEY}"
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({"input_string": question}))
        resp = json.loads(await ws.recv())
        print(resp["answer"])

asyncio.run(ask("Qual o gasto do SUS por região em 2025?"))
```

Resposta:

```json
{
  "answer": "## Gasto por região\n| Região | Valor |...",
  "query": "SELECT regiao, SUM(vl_total)...",
  "category": "saude",
  "timing": {"router": 0.5, "sql_agent": 3.2, "total": 3.7}
}
```

## Setup local

### 1. Instalar dependências

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r src/requirements.txt
```

### 2. Configurar `.env`

Criar `.env` na raiz:

```env
# LLM (Bedrock)
LLM_PROVIDER=bedrock
AWS_ACCESS_KEY_ID=***
AWS_SECRET_ACCESS_KEY=***
AWS_REGION=us-east-1
FAST_MODEL=us.anthropic.claude-haiku-4-5-20251001-v1:0
PRIMARY_MODEL=us.anthropic.claude-sonnet-4-6

# Trino (catálogo seaweedfs)
TRINO_HOST=trino.dataiesb.com
TRINO_PORT=443
TRINO_HTTP_SCHEME=https
TRINO_USER=***
TRINO_PASSWORD=***
TRINO_CATALOG=seaweedfs
TRINO_SCHEMA=gold

# Auth
API_KEY=***

# Concorrência
MAX_CONCURRENT_REQUESTS=50
MAX_LLM_CONCURRENT=6
REQUEST_TIMEOUT_SECONDS=300
```

O `.env` está no `.gitignore` — nunca versione credenciais.

### 3. Iniciar

```bash
./start.sh
```

### 4. Testar

```bash
python3 example.py "Quantos procedimentos o SUS realizou em 2025?"
```

## Deploy (Kubernetes)

O deploy é automático via GitHub Actions ao fazer push na branch `v1`.

Pipeline: push → build Docker → push ECR → apply k8s → rollout

### Manifests

```bash
kubectl apply -f k8s/configmap.yaml   # Env vars (LLM_PROVIDER, TRINO_HOST, etc.)
kubectl apply -f k8s/backend.yaml     # Deployment + Service
```

### Secrets

O `aurya-secret` no namespace `custom` contém:
- `TRINO_PASSWORD` — senha do Trino
- `TRINO_USER` — usuário do Trino
- `API_KEY` — chave de acesso da API
- `DATABASE_URL` — conexão Postgres (catálogo)

### Endpoints em produção

| URL | Descrição |
|-----|-----------|
| `https://api.dataiesb.com/aurya/` | API REST |
| `wss://api.dataiesb.com/aurya/ws/{session}` | WebSocket |
| `https://api.dataiesb.com/aurya/health` | Health check |

## Estrutura do projeto

```
src/
├── api/
│   └── main.py                 # FastAPI + WebSocket + auth
├── core/
│   ├── aurya_funasa.py         # Agente FUNASA (LangGraph, saude only)
│   ├── trino_funasa.py         # Conexão Trino isolada (gold.sus_aih)
│   ├── react_agent.py          # ReAct loop (Thought→Action→Observation)
│   ├── llm_provider.py         # Factory: Gemini / Bedrock
│   ├── bedrock_lazy.py         # Wrapper lazy para Bedrock
│   └── token_callback.py       # Tracking de tokens
├── prompts/
│   ├── funasa_prompts.py       # Prompts FUNASA (router + SQL agent)
│   ├── react_prompts.py        # Prompt base do agente SQL
│   ├── temas.py                # Exemplos de queries por tema
│   ├── response_prompts.py     # Regras de formatação
│   └── prompt_base.py          # Composição dos prompts
├── requirements.txt
└── .env

k8s/
├── backend.yaml                # Deployment + Service
├── configmap.yaml              # Env vars
├── namespace.yaml
└── serviceaccount.yaml

.github/workflows/
└── deploy.yaml                 # CI/CD GitHub Actions

example.py                      # Script exemplo de uso
start.sh                        # Iniciar servidor local
```
