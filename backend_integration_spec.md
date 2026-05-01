# Backend Integration Spec — New Gold Layers

## Overview

Wire 7 new gold tables into the Aurya agent so it can answer questions about educação, segurança, economia, and demografia — in addition to the existing saúde domain.

## Infrastructure (DONE)

- `TRINO_CATALOG` changed from `seaweedfs` → `datalake` in `k8s/configmap.yaml`
- All 8 gold tables live in `datalake.gold.*`, accessible by `aurya` user
- Trino uses HMS backed by Postgres for the `datalake` catalog

## Gold Tables Available

| Table | Domain | Rows | Granularity |
|-------|--------|------|-------------|
| gold.sus_aih | saude | 445,613 | município/mês |
| gold.sus_procedimento_ambulatorial | saude | 111,420 | município/mês |
| gold.educacao_basica | educacao | 5,570 | município |
| gold.educacao_superior | educacao | 31,599 | município/área/rede |
| gold.enem_2024 | educacao | 1,746 | município |
| gold.acidentes_transito | seguranca | 2,613 | município/ano/mês |
| gold.ocorrencias_criminais | seguranca | 2,610 | município/ano/evento |
| gold.demografia_municipios | demografia | 5,570 | município |

---

## 1. Router (`src/prompts/router_prompts.py`)

Add new categories to `prompt_router`:

```
4. 'educacao' - Questions about schools, enrollment, ENEM scores, higher education, teachers
5. 'seguranca' - Questions about traffic accidents, criminal occurrences, violence
6. 'economia' - Questions about GDP, PIB per capita (future — no gold table yet)
7. 'demografia' - Questions about population, age distribution, census data
```

Update `CATEGORY_MAP`:
```python
from src.prompts.temas import saude, educacao, seguranca, demografia

CATEGORY_MAP = {
    "saude": saude,
    "educacao": educacao,
    "seguranca": seguranca,
    "demografia": demografia,
}
```

---

## 2. Temas (`src/prompts/temas.py`)

Add new tema strings following the same XML pattern as `saude`. Each tema needs:
- `<context>` — domain description
- `<schema>` — table columns with types and descriptions
- `<query_rules>` — domain-specific SQL rules
- `<examples>` — 5-8 pre-validated SQL examples
- `<best_practices>` — formatting and aggregation tips

### educacao

Tables: `gold.educacao_basica`, `gold.educacao_superior`, `gold.enem_2024`

Key columns:
- educacao_basica: ano, municipio, uf, regiao, qt_escolas, qt_escolas_publica/privada, qt_mat_total/infantil/fundamental/medio/eja, qt_docentes, qt_turmas, qt_escolas_internet/biblioteca/lab_info/quadra
- educacao_superior: ano, municipio, uf, regiao, capital, area_conhecimento, tp_rede, qt_cursos, qt_vagas, qt_ingressantes, qt_matriculas, qt_concluintes, qt_mat_fies, qt_mat_prouni
- enem_2024: ano, municipio, uf, regiao, capital, qt_participantes, media_cn/ch/lc/mt/redacao/geral

Example queries:
1. "Quantas escolas públicas existem por estado?" → `SELECT uf, SUM(qt_escolas_publica) FROM gold.educacao_basica GROUP BY uf ORDER BY 2 DESC`
2. "Qual a média do ENEM por região?" → `SELECT regiao, ROUND(AVG(media_geral),2) FROM gold.enem_2024 GROUP BY regiao ORDER BY 2 DESC`
3. "Quantas matrículas no ensino médio por estado?" → `SELECT uf, SUM(qt_mat_medio) FROM gold.educacao_basica GROUP BY uf ORDER BY 2 DESC`
4. "Quais áreas de conhecimento têm mais vagas no ensino superior?" → `SELECT area_conhecimento, SUM(qt_vagas) FROM gold.educacao_superior GROUP BY 1 ORDER BY 2 DESC LIMIT 10`
5. "Quantos alunos usam FIES por estado?" → `SELECT uf, SUM(qt_mat_fies) FROM gold.educacao_superior GROUP BY uf ORDER BY 2 DESC`

Rules:
- educacao_basica is aggregated by município — no need to SUM unless grouping by uf/regiao
- educacao_superior has area_conhecimento and tp_rede dimensions
- enem_2024 medias are already averaged per município — use AVG() when grouping by uf/regiao
- All tables have uf, regiao for geographic grouping

### seguranca

Tables: `gold.acidentes_transito`, `gold.ocorrencias_criminais`

Key columns:
- acidentes_transito: ano, mes, municipio, cod_municipio, uf, qt_acidentes, qt_acidentes_obito, qt_envolvidos, qt_feridos, qt_obitos
- ocorrencias_criminais: ano, municipio, cod_municipio, uf, evento, qt_feminino, qt_masculino, qt_total

Example queries:
1. "Quantos acidentes com óbito por estado?" → `SELECT uf, SUM(qt_acidentes_obito) FROM gold.acidentes_transito GROUP BY uf ORDER BY 2 DESC`
2. "Qual o total de homicídios por região?" → needs JOIN with municipio for regiao, or filter by evento
3. "Evolução mensal de acidentes em 2024?" → `SELECT mes, SUM(qt_acidentes) FROM gold.acidentes_transito WHERE ano = 2024 GROUP BY mes ORDER BY mes`
4. "Quais tipos de ocorrência criminal são mais frequentes?" → `SELECT evento, SUM(qt_total) FROM gold.ocorrencias_criminais GROUP BY evento ORDER BY 2 DESC LIMIT 10`
5. "Comparação de vítimas por sexo nas ocorrências criminais?" → `SELECT SUM(qt_feminino), SUM(qt_masculino) FROM gold.ocorrencias_criminais`

Rules:
- acidentes_transito has ano/mes temporal dimensions
- ocorrencias_criminais has evento (type of crime) dimension
- qt_feminino/qt_masculino/qt_total are DOUBLE (can have decimals)
- Neither table has regiao/uf_nome — need to state this in rules or JOIN with a lookup

### demografia

Table: `gold.demografia_municipios`

Key columns: ano, municipio, cod_municipio, uf, uf_nome, regiao, capital, populacao_total, populacao_masculina, populacao_feminina, pop_0_14, pop_15_64, pop_65_mais

Example queries:
1. "Qual a população por região?" → `SELECT regiao, SUM(populacao_total) FROM gold.demografia_municipios GROUP BY regiao ORDER BY 2 DESC`
2. "Qual o percentual de idosos por estado?" → `SELECT uf, ROUND(100.0*SUM(pop_65_mais)/NULLIF(SUM(populacao_total),0),2) FROM gold.demografia_municipios GROUP BY uf ORDER BY 2 DESC`
3. "Quais capitais têm maior população?" → `SELECT municipio, uf, populacao_total FROM gold.demografia_municipios WHERE capital = true ORDER BY populacao_total DESC LIMIT 10`
4. "Distribuição por faixa etária no Brasil?" → `SELECT SUM(pop_0_14), SUM(pop_15_64), SUM(pop_65_mais) FROM gold.demografia_municipios`
5. "Razão homem/mulher por região?" → `SELECT regiao, ROUND(CAST(SUM(populacao_masculina) AS DOUBLE)/NULLIF(SUM(populacao_feminina),0),3) FROM gold.demografia_municipios GROUP BY regiao`

Rules:
- Data is from Censo 2022 — single year snapshot
- Already aggregated by município — SUM when grouping by uf/regiao
- Has capital BOOLEAN for filtering capitals
- Use NULLIF for division-by-zero protection

---

## 3. AURYA_PREFIX (`src/prompts/react_prompts.py`)

Update the `<schema>` section to list all 8 gold tables with their key columns. Keep `gold.sus_aih` as the primary table for saude, add brief descriptions for the others. The detailed schema comes from the catalogue via `build_context()`.

Add a `<table>` block for each new gold table with:
- Table name and description
- Row count and granularity
- Key dimensions and measures
- Domain-specific rules

---

## 4. Catalogue Seed (`migrations/003_seed_new_domains.sql`)

New migration file. Insert into `"dataiesb-aurya".catalogue`:

### Schema entries (PK=`schema:gold`)
One per table with full column definitions in JSON.

### Metadata entries (PK=`metadata:table`)
One per table with row_count, granularity, etc.

### Rules entries (PK=`rules:{category}`)
One per new category with query_rules and best_practices arrays.

### Example entries (PK=`example:{category}`)
5-8 per category with question, sql, tags.

---

## 5. Deployment Steps

1. Apply configmap: `kubectl apply -f k8s/configmap.yaml`
2. Run migration: `psql -f migrations/003_seed_new_domains.sql`
3. Update source files: `router_prompts.py`, `temas.py`, `react_prompts.py`
4. Build and deploy: `docker build && kubectl rollout restart deployment/aurya-backend -n custom`
5. Test: ask the agent questions from each domain
