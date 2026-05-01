-- Seed: populate catalogue from existing hardcoded prompts
-- Run after 001_create_catalogue.sql

-- Schema: gold.sus_aih
INSERT INTO "dataiesb-aurya".catalogue (pk, sk, data) VALUES
('schema:gold', 'sus_aih', '{
  "table_name": "gold.sus_aih",
  "description": "SUS hospital procedures (AIH) aggregated monthly by municipality. 108,224 rows | Years: 2019, 2025 | 27 UFs | ~5,300 municipalities.",
  "columns": [
    {"name": "ano",              "type": "INTEGER", "desc": "Ano (2019, 2025)"},
    {"name": "mes",              "type": "INTEGER", "desc": "Mês (1-12)"},
    {"name": "municipio",        "type": "VARCHAR", "desc": "Nome do município"},
    {"name": "uf",               "type": "VARCHAR", "desc": "Sigla do estado (2 letras)"},
    {"name": "uf_nome",          "type": "VARCHAR", "desc": "Nome do estado"},
    {"name": "regiao",           "type": "VARCHAR", "desc": "Norte, Nordeste, Sudeste, Sul, Centro-Oeste"},
    {"name": "cod_municipio",    "type": "VARCHAR", "desc": "Código IBGE 7 dígitos"},
    {"name": "capital",          "type": "BOOLEAN", "desc": "Se é capital do estado"},
    {"name": "latitude",         "type": "DECIMAL", "desc": "Latitude do município"},
    {"name": "longitude",        "type": "DECIMAL", "desc": "Longitude do município"},
    {"name": "qtd_total",        "type": "INTEGER", "desc": "Quantidade total de procedimentos"},
    {"name": "vl_total",         "type": "DOUBLE",  "desc": "Valor total em R$"},
    {"name": "qtd_prevencao",    "type": "INTEGER", "desc": "Grupo 01: Promoção e prevenção"},
    {"name": "qtd_diagnostico",  "type": "INTEGER", "desc": "Grupo 02: Finalidade diagnóstica"},
    {"name": "qtd_clinico",      "type": "INTEGER", "desc": "Grupo 03: Procedimentos clínicos"},
    {"name": "qtd_cirurgico",    "type": "INTEGER", "desc": "Grupo 04: Procedimentos cirúrgicos"},
    {"name": "qtd_transplante",  "type": "INTEGER", "desc": "Grupo 05: Transplantes"},
    {"name": "qtd_medicamento",  "type": "INTEGER", "desc": "Grupo 06: Medicamentos"},
    {"name": "qtd_ortese_protese","type": "INTEGER","desc": "Grupo 07: Órteses e próteses"},
    {"name": "qtd_complementar", "type": "INTEGER", "desc": "Grupo 08: Ações complementares"},
    {"name": "vl_diagnostico",   "type": "DOUBLE",  "desc": "Valor gasto em diagnósticos"},
    {"name": "vl_clinico",       "type": "DOUBLE",  "desc": "Valor gasto em procedimentos clínicos"},
    {"name": "vl_cirurgico",     "type": "DOUBLE",  "desc": "Valor gasto em cirurgias"},
    {"name": "vl_transplante",   "type": "DOUBLE",  "desc": "Valor gasto em transplantes"},
    {"name": "vl_medicamento",   "type": "DOUBLE",  "desc": "Valor gasto em medicamentos"},
    {"name": "vl_ortese_protese","type": "DOUBLE",  "desc": "Valor gasto em órteses/próteses"},
    {"name": "vl_complementar",  "type": "DOUBLE",  "desc": "Valor gasto em ações complementares"},
    {"name": "qtd_consultas",    "type": "INTEGER", "desc": "Consultas/atendimentos"},
    {"name": "qtd_fisioterapia", "type": "INTEGER", "desc": "Fisioterapia"},
    {"name": "qtd_oncologia",    "type": "INTEGER", "desc": "Tratamentos oncológicos"},
    {"name": "qtd_nefrologia",   "type": "INTEGER", "desc": "Diálise/hemodiálise"},
    {"name": "qtd_odontologia",  "type": "INTEGER", "desc": "Tratamentos odontológicos"},
    {"name": "vl_consultas",     "type": "DOUBLE",  "desc": "Valor de consultas"},
    {"name": "vl_fisioterapia",  "type": "DOUBLE",  "desc": "Valor de fisioterapia"},
    {"name": "vl_oncologia",     "type": "DOUBLE",  "desc": "Valor de tratamentos oncológicos"},
    {"name": "vl_nefrologia",    "type": "DOUBLE",  "desc": "Valor de tratamentos nefrológicos"},
    {"name": "vl_odontologia",   "type": "DOUBLE",  "desc": "Valor de tratamentos odontológicos"}
  ]
}');

-- Schema: bronze.sus_aih
INSERT INTO "dataiesb-aurya".catalogue (pk, sk, data) VALUES
('schema:bronze', 'sus_aih', '{
  "table_name": "bronze.sus_aih",
  "description": "Raw source data from DATASUS. Original column names (ano_aih, mes_aih, qtd_01..qtd_09, vl_01..vl_09). Use only if user asks about raw/original data.",
  "columns": []
}');

-- Metadata
INSERT INTO "dataiesb-aurya".catalogue (pk, sk, data) VALUES
('metadata:table', 'gold.sus_aih', '{
  "row_count": 108224,
  "granularity": "município/mês",
  "years": "2019, 2025"
}');

-- Rules
INSERT INTO "dataiesb-aurya".catalogue (pk, sk, data) VALUES
('rules:saude', 'general', '{
  "query_rules": [
    "Sempre use SUM() para agregar quantidades (qtd_*) e valores (vl_*) — os dados são por município/mês.",
    "Use ORDER BY para resultados em sequência lógica (temporal ou geográfica).",
    "Para filtrar por estado, use uf (sigla 2 letras) no WHERE, mas mostre uf_nome no SELECT.",
    "ano e mes são INTEGER — compare sem aspas: WHERE ano = 2025.",
    "Valores monetários estão em Reais (R$). Para bilhões: ROUND(SUM(vl_total)/1e9, 2).",
    "Use LIMIT para limitar resultados, nunca TOP.",
    "Sempre prefixe a tabela com o schema: gold.sus_aih."
  ],
  "best_practices": [
    "Sempre use SUM() para agregar — cada linha é um município/mês.",
    "Use aliases descritivos em português.",
    "Para queries temporais, ordene por ano e mês ascendente.",
    "Para queries geográficas, ordene por valor ou quantidade descendente.",
    "Quando filtrar por estado, use uf no WHERE mas mostre uf_nome no SELECT.",
    "Para valores grandes, divida por 1e6 (milhões) ou 1e9 (bilhões) e arredonde.",
    "Use NULLIF para evitar divisão por zero em cálculos de média.",
    "Hierarquia geográfica: regiao > uf/uf_nome > municipio.",
    "Hierarquia de procedimentos: qtd_total > grupos (qtd_clinico, qtd_cirurgico...) > subgrupos (qtd_consultas, qtd_oncologia...)."
  ]
}');

-- Examples
INSERT INTO "dataiesb-aurya".catalogue (pk, sk, data) VALUES
('example:saude', '01', '{
  "question": "Quantos procedimentos hospitalares foram realizados pelo SUS por ano?",
  "sql": "SELECT ano, SUM(qtd_total) AS total_procedimentos FROM gold.sus_aih GROUP BY ano ORDER BY ano"
}'),
('example:saude', '02', '{
  "question": "Qual o total investido pelo SUS em internações por ano?",
  "sql": "SELECT ano, ROUND(SUM(vl_total)/1e9, 2) AS valor_bilhoes FROM gold.sus_aih GROUP BY ano ORDER BY ano"
}'),
('example:saude', '03', '{
  "question": "Qual a evolução mensal de procedimentos e valores em 2025?",
  "sql": "SELECT mes, SUM(qtd_total) AS procedimentos, ROUND(SUM(vl_total)/1e6, 1) AS valor_milhoes FROM gold.sus_aih WHERE ano = 2025 GROUP BY mes ORDER BY mes"
}'),
('example:saude', '04', '{
  "question": "Quais estados gastam mais com o SUS?",
  "sql": "SELECT uf, uf_nome, SUM(qtd_total) AS procedimentos, ROUND(SUM(vl_total)/1e6, 1) AS valor_milhoes FROM gold.sus_aih GROUP BY uf, uf_nome ORDER BY valor_milhoes DESC LIMIT 10"
}'),
('example:saude', '05', '{
  "question": "Qual o gasto do SUS por região em 2025?",
  "sql": "SELECT regiao, SUM(qtd_total) AS procedimentos, ROUND(SUM(vl_total)/1e9, 2) AS valor_bilhoes FROM gold.sus_aih WHERE ano = 2025 GROUP BY regiao ORDER BY valor_bilhoes DESC"
}'),
('example:saude', '06', '{
  "question": "Quanto o SUS gastou em cirurgias vs procedimentos clínicos por ano?",
  "sql": "SELECT ano, SUM(qtd_clinico) AS qtd_clinicos, ROUND(SUM(vl_clinico)/1e6, 1) AS vl_clinicos_mi, SUM(qtd_cirurgico) AS qtd_cirurgicos, ROUND(SUM(vl_cirurgico)/1e6, 1) AS vl_cirurgicos_mi FROM gold.sus_aih GROUP BY ano ORDER BY ano"
}'),
('example:saude', '07', '{
  "question": "Quais os municípios com mais internações em São Paulo em 2025?",
  "sql": "SELECT municipio, SUM(qtd_total) AS procedimentos, ROUND(SUM(vl_total)/1e6, 1) AS valor_milhoes FROM gold.sus_aih WHERE uf = ''SP'' AND ano = 2025 GROUP BY municipio ORDER BY procedimentos DESC LIMIT 15"
}'),
('example:saude', '08', '{
  "question": "Qual o gasto com tratamentos oncológicos por estado?",
  "sql": "SELECT uf, uf_nome, SUM(qtd_oncologia) AS qtd_oncologia, ROUND(SUM(vl_oncologia)/1e6, 1) AS valor_milhoes FROM gold.sus_aih GROUP BY uf, uf_nome ORDER BY valor_milhoes DESC LIMIT 10"
}'),
('example:saude', '09', '{
  "question": "Qual a proporção de cada tipo de procedimento no total nacional em 2025?",
  "sql": "SELECT ROUND(100.0 * SUM(qtd_clinico) / SUM(qtd_total), 1) AS pct_clinico, ROUND(100.0 * SUM(qtd_cirurgico) / SUM(qtd_total), 1) AS pct_cirurgico, ROUND(100.0 * SUM(qtd_diagnostico) / SUM(qtd_total), 1) AS pct_diagnostico, ROUND(100.0 * SUM(qtd_complementar) / SUM(qtd_total), 1) AS pct_complementar, ROUND(100.0 * SUM(qtd_prevencao) / SUM(qtd_total), 1) AS pct_prevencao, ROUND(100.0 * SUM(qtd_transplante) / SUM(qtd_total), 1) AS pct_transplante FROM gold.sus_aih WHERE ano = 2025"
}'),
('example:saude', '10', '{
  "question": "Quanto o SUS gastou com nefrologia (diálise/hemodiálise) por região?",
  "sql": "SELECT regiao, SUM(qtd_nefrologia) AS qtd_nefrologia, ROUND(SUM(vl_nefrologia)/1e6, 1) AS valor_milhoes FROM gold.sus_aih GROUP BY regiao ORDER BY valor_milhoes DESC"
}'),
('example:saude', '11', '{
  "question": "Quais capitais têm mais procedimentos cirúrgicos?",
  "sql": "SELECT municipio, uf, SUM(qtd_cirurgico) AS cirurgias, ROUND(SUM(vl_cirurgico)/1e6, 1) AS valor_milhoes FROM gold.sus_aih WHERE capital = true GROUP BY municipio, uf ORDER BY cirurgias DESC LIMIT 10"
}'),
('example:saude', '12', '{
  "question": "Qual a evolução mensal de gastos com fisioterapia no Nordeste em 2025?",
  "sql": "SELECT mes, SUM(qtd_fisioterapia) AS qtd_fisio, ROUND(SUM(vl_fisioterapia)/1e6, 1) AS valor_milhoes FROM gold.sus_aih WHERE regiao = ''Nordeste'' AND ano = 2025 GROUP BY mes ORDER BY mes"
}'),
('example:saude', '13', '{
  "question": "Compare o gasto total do SUS entre 2019 e 2025 por região.",
  "sql": "SELECT regiao, ano, ROUND(SUM(vl_total)/1e9, 2) AS valor_bilhoes FROM gold.sus_aih GROUP BY regiao, ano ORDER BY regiao, ano"
}'),
('example:saude', '14', '{
  "question": "Qual o custo médio por procedimento por estado em 2025?",
  "sql": "SELECT uf, uf_nome, SUM(qtd_total) AS procedimentos, ROUND(SUM(vl_total) / NULLIF(SUM(qtd_total), 0), 2) AS custo_medio_por_procedimento FROM gold.sus_aih WHERE ano = 2025 GROUP BY uf, uf_nome ORDER BY custo_medio_por_procedimento DESC"
}');
