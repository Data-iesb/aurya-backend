-- 003: Seed new domains (educacao, seguranca, demografia) + sus_procedimento_ambulatorial
-- Run after 002_seed_catalogue.sql

-- ══════════════════════════════════════════════════════════════
-- SCHEMAS
-- ══════════════════════════════════════════════════════════════

INSERT INTO "dataiesb-aurya".catalogue (pk, sk, data) VALUES
('schema:gold', 'sus_procedimento_ambulatorial', '{
  "table_name": "gold.sus_procedimento_ambulatorial",
  "description": "SUS outpatient procedures by municipality/month. 111,420 rows.",
  "columns": [
    {"name": "ano", "type": "INTEGER", "desc": "Ano"},
    {"name": "mes", "type": "INTEGER", "desc": "Mês (1-12)"},
    {"name": "municipio", "type": "VARCHAR", "desc": "Nome do município"},
    {"name": "cod_municipio", "type": "VARCHAR", "desc": "Código IBGE"},
    {"name": "uf", "type": "VARCHAR", "desc": "Sigla UF"},
    {"name": "uf_nome", "type": "VARCHAR", "desc": "Nome do estado"},
    {"name": "regiao", "type": "VARCHAR", "desc": "Região"},
    {"name": "capital", "type": "BOOLEAN", "desc": "Se é capital"},
    {"name": "qtd_total", "type": "INTEGER", "desc": "Total de procedimentos"},
    {"name": "qtd_prevencao", "type": "INTEGER", "desc": "Grupo 01: Prevenção"},
    {"name": "qtd_diagnostico", "type": "INTEGER", "desc": "Grupo 02: Diagnóstico"},
    {"name": "qtd_clinico", "type": "INTEGER", "desc": "Grupo 03: Clínico"},
    {"name": "qtd_cirurgico", "type": "INTEGER", "desc": "Grupo 04: Cirúrgico"},
    {"name": "qtd_transplante", "type": "INTEGER", "desc": "Grupo 05: Transplante"},
    {"name": "qtd_medicamento", "type": "INTEGER", "desc": "Grupo 06: Medicamento"},
    {"name": "qtd_ortese_protese", "type": "INTEGER", "desc": "Grupo 07: Órteses/Próteses"},
    {"name": "qtd_complementar", "type": "INTEGER", "desc": "Grupo 08: Complementar"}
  ]
}'),
('schema:gold', 'educacao_basica', '{
  "table_name": "gold.educacao_basica",
  "description": "Censo Escolar 2024 agregado por município. 5,570 municípios.",
  "columns": [
    {"name": "ano", "type": "INTEGER", "desc": "Ano do censo (2024)"},
    {"name": "municipio", "type": "VARCHAR", "desc": "Nome do município"},
    {"name": "cod_municipio", "type": "VARCHAR", "desc": "Código IBGE"},
    {"name": "uf", "type": "VARCHAR", "desc": "Sigla UF"},
    {"name": "uf_nome", "type": "VARCHAR", "desc": "Nome do estado"},
    {"name": "regiao", "type": "VARCHAR", "desc": "Região"},
    {"name": "qt_escolas", "type": "INTEGER", "desc": "Total de escolas"},
    {"name": "qt_escolas_publica", "type": "INTEGER", "desc": "Escolas públicas"},
    {"name": "qt_escolas_privada", "type": "INTEGER", "desc": "Escolas privadas"},
    {"name": "qt_escolas_urbana", "type": "INTEGER", "desc": "Escolas urbanas"},
    {"name": "qt_escolas_rural", "type": "INTEGER", "desc": "Escolas rurais"},
    {"name": "qt_mat_total", "type": "INTEGER", "desc": "Total matrículas"},
    {"name": "qt_mat_infantil", "type": "INTEGER", "desc": "Matrículas infantil"},
    {"name": "qt_mat_fundamental", "type": "INTEGER", "desc": "Matrículas fundamental"},
    {"name": "qt_mat_medio", "type": "INTEGER", "desc": "Matrículas médio"},
    {"name": "qt_mat_eja", "type": "INTEGER", "desc": "Matrículas EJA"},
    {"name": "qt_mat_especial", "type": "INTEGER", "desc": "Matrículas especial"},
    {"name": "qt_mat_profissional", "type": "INTEGER", "desc": "Matrículas profissional"},
    {"name": "qt_docentes", "type": "INTEGER", "desc": "Total de docentes"},
    {"name": "qt_turmas", "type": "INTEGER", "desc": "Total de turmas"},
    {"name": "qt_escolas_internet", "type": "INTEGER", "desc": "Escolas com internet"},
    {"name": "qt_escolas_biblioteca", "type": "INTEGER", "desc": "Escolas com biblioteca"},
    {"name": "qt_escolas_lab_info", "type": "INTEGER", "desc": "Escolas com lab informática"},
    {"name": "qt_escolas_quadra", "type": "INTEGER", "desc": "Escolas com quadra"}
  ]
}'),
('schema:gold', 'educacao_superior', '{
  "table_name": "gold.educacao_superior",
  "description": "Censo da Educação Superior por município/área/rede. 31,599 registros.",
  "columns": [
    {"name": "ano", "type": "INTEGER", "desc": "Ano do censo"},
    {"name": "municipio", "type": "VARCHAR", "desc": "Nome do município"},
    {"name": "cod_municipio", "type": "VARCHAR", "desc": "Código IBGE"},
    {"name": "uf", "type": "VARCHAR", "desc": "Sigla UF"},
    {"name": "uf_nome", "type": "VARCHAR", "desc": "Nome do estado"},
    {"name": "regiao", "type": "VARCHAR", "desc": "Região"},
    {"name": "capital", "type": "BOOLEAN", "desc": "Se é capital"},
    {"name": "area_conhecimento", "type": "VARCHAR", "desc": "Área geral CINE"},
    {"name": "tp_rede", "type": "VARCHAR", "desc": "Pública/Privada"},
    {"name": "qt_cursos", "type": "INTEGER", "desc": "Total de cursos"},
    {"name": "qt_vagas", "type": "INTEGER", "desc": "Total de vagas"},
    {"name": "qt_ingressantes", "type": "INTEGER", "desc": "Total de ingressantes"},
    {"name": "qt_matriculas", "type": "INTEGER", "desc": "Total de matrículas"},
    {"name": "qt_concluintes", "type": "INTEGER", "desc": "Total de concluintes"},
    {"name": "qt_ing_feminino", "type": "INTEGER", "desc": "Ingressantes feminino"},
    {"name": "qt_ing_masculino", "type": "INTEGER", "desc": "Ingressantes masculino"},
    {"name": "qt_mat_fies", "type": "INTEGER", "desc": "Matrículas com FIES"},
    {"name": "qt_mat_prouni", "type": "INTEGER", "desc": "Matrículas com ProUni"}
  ]
}'),
('schema:gold', 'enem_2024', '{
  "table_name": "gold.enem_2024",
  "description": "Médias do ENEM 2024 por município. 1,746 municípios.",
  "columns": [
    {"name": "ano", "type": "INTEGER", "desc": "Ano (2024)"},
    {"name": "municipio", "type": "VARCHAR", "desc": "Município da prova"},
    {"name": "cod_municipio", "type": "VARCHAR", "desc": "Código IBGE"},
    {"name": "uf", "type": "VARCHAR", "desc": "Sigla UF"},
    {"name": "uf_nome", "type": "VARCHAR", "desc": "Nome do estado"},
    {"name": "regiao", "type": "VARCHAR", "desc": "Região"},
    {"name": "capital", "type": "BOOLEAN", "desc": "Se é capital"},
    {"name": "qt_participantes", "type": "INTEGER", "desc": "Participantes"},
    {"name": "media_cn", "type": "DOUBLE", "desc": "Média Ciências da Natureza"},
    {"name": "media_ch", "type": "DOUBLE", "desc": "Média Ciências Humanas"},
    {"name": "media_lc", "type": "DOUBLE", "desc": "Média Linguagens e Códigos"},
    {"name": "media_mt", "type": "DOUBLE", "desc": "Média Matemática"},
    {"name": "media_redacao", "type": "DOUBLE", "desc": "Média Redação"},
    {"name": "media_geral", "type": "DOUBLE", "desc": "Média geral 5 notas"}
  ]
}'),
('schema:gold', 'acidentes_transito', '{
  "table_name": "gold.acidentes_transito",
  "description": "Acidentes de trânsito por município/ano/mês. 2,613 registros.",
  "columns": [
    {"name": "ano", "type": "INTEGER", "desc": "Ano"},
    {"name": "mes", "type": "INTEGER", "desc": "Mês"},
    {"name": "municipio", "type": "VARCHAR", "desc": "Nome do município"},
    {"name": "cod_municipio", "type": "VARCHAR", "desc": "Código IBGE"},
    {"name": "uf", "type": "VARCHAR", "desc": "Sigla UF"},
    {"name": "qt_acidentes", "type": "INTEGER", "desc": "Total de acidentes"},
    {"name": "qt_acidentes_obito", "type": "INTEGER", "desc": "Acidentes com óbito"},
    {"name": "qt_envolvidos", "type": "INTEGER", "desc": "Total de envolvidos"},
    {"name": "qt_feridos", "type": "INTEGER", "desc": "Total de feridos"},
    {"name": "qt_obitos", "type": "INTEGER", "desc": "Total de óbitos"}
  ]
}'),
('schema:gold', 'ocorrencias_criminais', '{
  "table_name": "gold.ocorrencias_criminais",
  "description": "Ocorrências criminais por município/ano/evento. 2,610 registros.",
  "columns": [
    {"name": "ano", "type": "INTEGER", "desc": "Ano"},
    {"name": "municipio", "type": "VARCHAR", "desc": "Nome do município"},
    {"name": "cod_municipio", "type": "VARCHAR", "desc": "Código IBGE"},
    {"name": "uf", "type": "VARCHAR", "desc": "Sigla UF"},
    {"name": "evento", "type": "VARCHAR", "desc": "Tipo de evento criminal"},
    {"name": "qt_feminino", "type": "DOUBLE", "desc": "Vítimas feminino"},
    {"name": "qt_masculino", "type": "DOUBLE", "desc": "Vítimas masculino"},
    {"name": "qt_total", "type": "DOUBLE", "desc": "Total de vítimas"}
  ]
}'),
('schema:gold', 'demografia_municipios', '{
  "table_name": "gold.demografia_municipios",
  "description": "População por município do Censo 2022. 5,570 municípios.",
  "columns": [
    {"name": "ano", "type": "INTEGER", "desc": "Ano do censo (2022)"},
    {"name": "municipio", "type": "VARCHAR", "desc": "Nome do município"},
    {"name": "cod_municipio", "type": "VARCHAR", "desc": "Código IBGE"},
    {"name": "uf", "type": "VARCHAR", "desc": "Sigla UF"},
    {"name": "uf_nome", "type": "VARCHAR", "desc": "Nome do estado"},
    {"name": "regiao", "type": "VARCHAR", "desc": "Região"},
    {"name": "capital", "type": "BOOLEAN", "desc": "Se é capital"},
    {"name": "populacao_total", "type": "INTEGER", "desc": "População total"},
    {"name": "populacao_masculina", "type": "INTEGER", "desc": "População masculina"},
    {"name": "populacao_feminina", "type": "INTEGER", "desc": "População feminina"},
    {"name": "pop_0_14", "type": "INTEGER", "desc": "Jovens (0-14 anos)"},
    {"name": "pop_15_64", "type": "INTEGER", "desc": "Adultos (15-64 anos)"},
    {"name": "pop_65_mais", "type": "INTEGER", "desc": "Idosos (65+ anos)"}
  ]
}');

-- ══════════════════════════════════════════════════════════════
-- METADATA
-- ══════════════════════════════════════════════════════════════

INSERT INTO "dataiesb-aurya".catalogue (pk, sk, data) VALUES
('metadata:table', 'gold.sus_procedimento_ambulatorial', '{"row_count": 111420, "granularity": "municipality/month"}'),
('metadata:table', 'gold.educacao_basica', '{"row_count": 5570, "granularity": "municipality"}'),
('metadata:table', 'gold.educacao_superior', '{"row_count": 31599, "granularity": "municipality/area/network"}'),
('metadata:table', 'gold.enem_2024', '{"row_count": 1746, "granularity": "municipality", "years": [2024]}'),
('metadata:table', 'gold.acidentes_transito', '{"row_count": 2613, "granularity": "municipality/year/month"}'),
('metadata:table', 'gold.ocorrencias_criminais', '{"row_count": 2610, "granularity": "municipality/year/event"}'),
('metadata:table', 'gold.demografia_municipios', '{"row_count": 5570, "granularity": "municipality", "years": [2022]}');

-- ══════════════════════════════════════════════════════════════
-- RULES
-- ══════════════════════════════════════════════════════════════

INSERT INTO "dataiesb-aurya".catalogue (pk, sk, data) VALUES
('rules:educacao', 'general', '{
  "query_rules": [
    "educacao_basica já é agregado por município — use SUM() ao agrupar por uf ou regiao",
    "educacao_superior tem area_conhecimento e tp_rede como dimensões extras",
    "enem_2024 médias são por município — use AVG() ao agrupar por uf/regiao",
    "Sempre prefixe com gold.: gold.educacao_basica, gold.educacao_superior, gold.enem_2024",
    "Use LIMIT, não TOP. Sintaxe Trino SQL",
    "Percentuais com 2 casas decimais e NULLIF para divisão por zero"
  ],
  "best_practices": [
    "Use aliases descritivos em português",
    "Para rankings, ordene DESC com LIMIT",
    "Hierarquia geográfica: regiao > uf/uf_nome > municipio"
  ],
  "response_format": "PT-BR markdown, no HTML"
}'),
('rules:seguranca', 'general', '{
  "query_rules": [
    "acidentes_transito tem dimensões temporais ano/mes",
    "ocorrencias_criminais tem coluna evento para filtrar tipo de crime",
    "qt_feminino/qt_masculino/qt_total são DOUBLE — use ROUND()",
    "Nenhuma tabela de segurança tem regiao ou uf_nome — use apenas uf",
    "Sempre prefixe com gold.: gold.acidentes_transito, gold.ocorrencias_criminais",
    "Use SUM() para agregar métricas ao agrupar por uf ou ano"
  ],
  "best_practices": [
    "Use aliases descritivos em português",
    "Temporal: ORDER BY ano, mes ASC",
    "ROUND() para métricas DOUBLE"
  ],
  "response_format": "PT-BR markdown, no HTML"
}'),
('rules:demografia', 'general', '{
  "query_rules": [
    "Dados do Censo 2022 — snapshot único, sem dimensão temporal",
    "Já agregado por município — use SUM() ao agrupar por uf ou regiao",
    "capital é BOOLEAN: WHERE capital = true",
    "Use NULLIF para divisão por zero em cálculos de percentual",
    "Sempre prefixe: gold.demografia_municipios"
  ],
  "best_practices": [
    "Use aliases descritivos em português",
    "Percentuais com 2 casas decimais",
    "Hierarquia geográfica: regiao > uf/uf_nome > municipio",
    "Para per capita, divida pelo populacao_total"
  ],
  "response_format": "PT-BR markdown, no HTML"
}');

-- ══════════════════════════════════════════════════════════════
-- EXAMPLES
-- ══════════════════════════════════════════════════════════════

INSERT INTO "dataiesb-aurya".catalogue (pk, sk, data) VALUES
-- educacao
('example:educacao', '001', '{"question": "Quantas escolas públicas existem por estado?", "sql": "SELECT uf, uf_nome, SUM(qt_escolas_publica) AS escolas_publicas FROM gold.educacao_basica GROUP BY uf, uf_nome ORDER BY escolas_publicas DESC", "tags": ["geographic", "schools"]}'),
('example:educacao', '002', '{"question": "Qual a média do ENEM por região?", "sql": "SELECT regiao, ROUND(AVG(media_geral), 2) AS media FROM gold.enem_2024 GROUP BY regiao ORDER BY media DESC", "tags": ["enem", "region"]}'),
('example:educacao', '003', '{"question": "Quantas matrículas no ensino médio por estado?", "sql": "SELECT uf, uf_nome, SUM(qt_mat_medio) AS matriculas_medio FROM gold.educacao_basica GROUP BY uf, uf_nome ORDER BY matriculas_medio DESC", "tags": ["enrollment", "state"]}'),
('example:educacao', '004', '{"question": "Quais áreas de conhecimento têm mais vagas no ensino superior?", "sql": "SELECT area_conhecimento, SUM(qt_vagas) AS vagas FROM gold.educacao_superior GROUP BY area_conhecimento ORDER BY vagas DESC LIMIT 10", "tags": ["higher_ed", "ranking"]}'),
('example:educacao', '005', '{"question": "Qual o percentual de escolas com internet por região?", "sql": "SELECT regiao, ROUND(100.0 * SUM(qt_escolas_internet) / NULLIF(SUM(qt_escolas), 0), 2) AS pct_internet FROM gold.educacao_basica GROUP BY regiao ORDER BY pct_internet DESC", "tags": ["infrastructure", "percentage"]}'),
-- seguranca
('example:seguranca', '001', '{"question": "Quantos acidentes com óbito por estado?", "sql": "SELECT uf, SUM(qt_acidentes_obito) AS acidentes_obito FROM gold.acidentes_transito GROUP BY uf ORDER BY acidentes_obito DESC", "tags": ["accidents", "state"]}'),
('example:seguranca', '002', '{"question": "Evolução mensal de acidentes?", "sql": "SELECT ano, mes, SUM(qt_acidentes) AS acidentes, SUM(qt_obitos) AS obitos FROM gold.acidentes_transito GROUP BY ano, mes ORDER BY ano, mes", "tags": ["temporal", "accidents"]}'),
('example:seguranca', '003', '{"question": "Quais tipos de ocorrência criminal são mais frequentes?", "sql": "SELECT evento, ROUND(SUM(qt_total), 0) AS total_vitimas FROM gold.ocorrencias_criminais GROUP BY evento ORDER BY total_vitimas DESC LIMIT 10", "tags": ["criminal", "ranking"]}'),
('example:seguranca', '004', '{"question": "Comparação de vítimas por sexo?", "sql": "SELECT ROUND(SUM(qt_feminino), 0) AS vitimas_feminino, ROUND(SUM(qt_masculino), 0) AS vitimas_masculino, ROUND(SUM(qt_total), 0) AS total FROM gold.ocorrencias_criminais", "tags": ["criminal", "gender"]}'),
('example:seguranca', '005', '{"question": "Quais municípios têm mais óbitos em acidentes?", "sql": "SELECT municipio, uf, SUM(qt_obitos) AS obitos FROM gold.acidentes_transito GROUP BY municipio, uf ORDER BY obitos DESC LIMIT 15", "tags": ["accidents", "municipality"]}'),
-- demografia
('example:demografia', '001', '{"question": "Qual a população por região?", "sql": "SELECT regiao, SUM(populacao_total) AS populacao FROM gold.demografia_municipios GROUP BY regiao ORDER BY populacao DESC", "tags": ["population", "region"]}'),
('example:demografia', '002', '{"question": "Qual o percentual de idosos por estado?", "sql": "SELECT uf, uf_nome, ROUND(100.0 * SUM(pop_65_mais) / NULLIF(SUM(populacao_total), 0), 2) AS pct_idosos FROM gold.demografia_municipios GROUP BY uf, uf_nome ORDER BY pct_idosos DESC", "tags": ["age", "percentage"]}'),
('example:demografia', '003', '{"question": "Quais capitais têm maior população?", "sql": "SELECT municipio, uf, populacao_total FROM gold.demografia_municipios WHERE capital = true ORDER BY populacao_total DESC LIMIT 10", "tags": ["capital", "ranking"]}'),
('example:demografia', '004', '{"question": "Distribuição por faixa etária no Brasil?", "sql": "SELECT SUM(pop_0_14) AS jovens_0_14, SUM(pop_15_64) AS adultos_15_64, SUM(pop_65_mais) AS idosos_65_mais, SUM(populacao_total) AS total FROM gold.demografia_municipios", "tags": ["age", "national"]}'),
('example:demografia', '005', '{"question": "Razão homem/mulher por região?", "sql": "SELECT regiao, ROUND(CAST(SUM(populacao_masculina) AS DOUBLE) / NULLIF(SUM(populacao_feminina), 0), 3) AS razao_masc_fem FROM gold.demografia_municipios GROUP BY regiao ORDER BY razao_masc_fem DESC", "tags": ["gender", "ratio"]}');
