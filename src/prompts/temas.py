sociodemograficos = """
<context>
This subcategory focuses on Brazilian sociodemographic data from IBGE Censo 2022.
The main tables available are:
- Censo_20222_Populacao_Idade_Sexo: Census 2022 population data by age, gender, and municipality
- municipio
- unidade_federacao
- regiao
</context>

<query_patterns>
Common query patterns for this subcategory:
1. Population queries: Use Censo_20222_Populacao_Idade_Sexo table with SUM("TOTAL")
2. Aggregations: Usually group by geographical levels (municipality, UF/state, region)
3. Joins: Always use proper foreign key: "CO_MUNICIPIO" = codigo_municipio_dv
4. Ordering: Sort results by population (DESC) or geography for readability
</query_patterns>

<examples>
<example id="1">
<business_question>
Qual o total da população brasileira em 2022?
</business_question>

<sql_query>
SELECT SUM("TOTAL") AS populacao_total
FROM iesb.public."Censo_20222_Populacao_Idade_Sexo";
</sql_query>
</example id="1">

<example id="2">
<business_question>
Qual o total da população brasileira em 2022 por município?
</business_question>

<sql_query>
SELECT
  mu.codigo_municipio_dv,
  mu.nome_municipio,
  SUM(pop."TOTAL") AS populacao_total
FROM
  iesb.public."Censo_20222_Populacao_Idade_Sexo" pop
  INNER JOIN iesb.public.municipio mu ON pop."CO_MUNICIPIO" = mu.codigo_municipio_dv
GROUP BY
  mu.codigo_municipio_dv,
  mu.nome_municipio
ORDER BY
  populacao_total DESC;
</sql_query>
</example id="2">

<example id="3">
<business_question>
Segundo o Censo de 2022, qual era o total da população do Distrito Federal?
</business_question>

<sql_query>
SELECT 
    SUM(pop."TOTAL") AS populacao_total
FROM 
    iesb.public."Censo_20222_Populacao_Idade_Sexo" AS pop
INNER JOIN 
    iesb.public.municipio AS mu 
    ON pop."CO_MUNICIPIO" = mu.codigo_municipio_dv
INNER JOIN 
    iesb.public.unidade_federacao AS uf 
    ON mu.cd_uf = uf.cd_uf
WHERE 
    uf.sigla_uf = 'DF';
</sql_query>
</example id="3">

<example id="4">
<business_question>
Qual o total da população brasileira em 2022 por região?
</business_question>

<sql_query>
SELECT 
    r.nome_regiao,
    SUM(pop."TOTAL") AS populacao_total
FROM 
    iesb.public."Censo_20222_Populacao_Idade_Sexo" AS pop
INNER JOIN 
    iesb.public.municipio AS mu 
    ON pop."CO_MUNICIPIO" = mu.codigo_municipio_dv
INNER JOIN 
    iesb.public.unidade_federacao AS uf 
    ON mu.cd_uf = uf.cd_uf
INNER JOIN 
    iesb.public.regiao AS r 
    ON uf.cd_regiao = r.cd_regiao
GROUP BY 
    r.nome_regiao
ORDER BY 
    populacao_total DESC;
</sql_query>
</example id="4">

<example id="5">
<business_question>
Qual era o total da população da região Nordeste em 2022?
</business_question>

<sql_query>
SELECT 
    r.nome_regiao,
    SUM(pop."TOTAL") AS populacao_total
FROM 
    iesb.public."Censo_20222_Populacao_Idade_Sexo" AS pop
INNER JOIN 
    iesb.public.municipio AS mu 
    ON pop."CO_MUNICIPIO" = mu.codigo_municipio_dv
INNER JOIN 
    iesb.public.unidade_federacao AS uf 
    ON mu.cd_uf = uf.cd_uf
INNER JOIN 
    iesb.public.regiao AS r 
    ON uf.cd_regiao = r.cd_regiao
GROUP BY 
    r.nome_regiao
ORDER BY 
    populacao_total DESC;
</sql_query>
</example id="5">

<example id="6">
<business_question>
Qual era o total da população do Rio de Janeiro do sexo feminino em 2022?
</business_question>

<sql_query>
SELECT 
    SUM(pop."TOTAL") AS populacao_feminina_total
FROM 
    iesb.public."Censo_20222_Populacao_Idade_Sexo" AS pop
INNER JOIN 
    iesb.public.municipio AS mu 
    ON pop."CO_MUNICIPIO" = mu.codigo_municipio_dv
INNER JOIN 
    iesb.public.unidade_federacao AS uf 
    ON mu.cd_uf = uf.cd_uf
WHERE 
    uf.sigla_uf = 'RJ'
    AND pop."SEXO" = 'Mulheres';
</sql_query>
</example id="6">

<example id="7">
<business_question>
Qual era o total da população do estado de São Paulo do sexo masculino com 18 anos ou mais em 2022?
</business_question>

<sql_query>
SELECT 
    SUM(pop."TOTAL") AS populacao_total
FROM 
    iesb.public."Censo_20222_Populacao_Idade_Sexo" AS pop
INNER JOIN 
    iesb.public.municipio AS mu 
    ON pop."CO_MUNICIPIO" = mu.codigo_municipio_dv
INNER JOIN 
    iesb.public.unidade_federacao AS uf 
    ON mu.cd_uf = uf.cd_uf
WHERE 
    uf.sigla_uf = 'SP'
    AND pop."SEXO" = 'Homens'
    AND pop."IDADE" >= 18;
</sql_query>
</example id="7">

<example id="8">
<business_question>
Qual é a população brasileira de 0 a 17 anos (crianças e adolescentes) em 2022?
</business_question>

<sql_query>
SELECT 
    SUM("TOTAL") AS populacao_0_a_17_anos
FROM 
    iesb.public."Censo_20222_Populacao_Idade_Sexo"
WHERE 
    "IDADE" BETWEEN 0 AND 17;
</sql_query>
</example id="8">

<example id="9">
<business_question>
Qual a população de 0 a 5 anos (primeira infância) por região em 2022?
</business_question>

<sql_query>
SELECT 
    r.nome_regiao,
    SUM(pop."TOTAL") AS populacao_0_a_5_anos
FROM 
    iesb.public."Censo_20222_Populacao_Idade_Sexo" AS pop
INNER JOIN 
    iesb.public.municipio AS mu 
    ON pop."CO_MUNICIPIO" = mu.codigo_municipio_dv
INNER JOIN 
    iesb.public.unidade_federacao AS uf 
    ON mu.cd_uf = uf.cd_uf
INNER JOIN 
    iesb.public.regiao AS r 
    ON uf.cd_regiao = r.cd_regiao
WHERE 
    pop."IDADE" BETWEEN 0 AND 5
GROUP BY 
    r.nome_regiao
ORDER BY 
    populacao_0_a_5_anos DESC;
</sql_query>
</example id="9">

<example id="10">
<business_question>
Quais são os 20 municípios mais populosos do Brasil em 2022?
</business_question>

<sql_query>
SELECT 
    mu.codigo_municipio_dv,
    mu.nome_municipio,
    uf.sigla_uf,
    SUM(pop."TOTAL") AS populacao_total
FROM 
    iesb.public."Censo_20222_Populacao_Idade_Sexo" AS pop
INNER JOIN 
    iesb.public.municipio AS mu 
    ON pop."CO_MUNICIPIO" = mu.codigo_municipio_dv
INNER JOIN 
    iesb.public.unidade_federacao AS uf 
    ON mu.cd_uf = uf.cd_uf
GROUP BY 
    mu.codigo_municipio_dv,
    mu.nome_municipio,
    uf.sigla_uf
ORDER BY 
    populacao_total DESC
LIMIT 20;
</sql_query>
</example id="10">

<example id="11">
<business_question>
Qual a diferença entre a população masculina e feminina no Brasil?
</business_question>

<sql_query>
SELECT 
    SUM(CASE WHEN "SEXO" = 'Homens' THEN "TOTAL" ELSE 0 END) AS populacao_masculina,
    SUM(CASE WHEN "SEXO" = 'Mulheres' THEN "TOTAL" ELSE 0 END) AS populacao_feminina,
    SUM(CASE WHEN "SEXO" = 'Homens' THEN "TOTAL" ELSE 0 END) 
        - SUM(CASE WHEN "SEXO" = 'Mulheres' THEN "TOTAL" ELSE 0 END) AS diferenca,
    ROUND(
        100.0 * SUM(CASE WHEN "SEXO" = 'Homens' THEN "TOTAL" ELSE 0 END) 
        / SUM("TOTAL"), 
        2
    ) AS perc_homens,
    ROUND(
        100.0 * SUM(CASE WHEN "SEXO" = 'Mulheres' THEN "TOTAL" ELSE 0 END) 
        / SUM("TOTAL"), 
        2
    ) AS perc_mulheres
FROM 
    iesb.public."Censo_20222_Populacao_Idade_Sexo";
</sql_query>
</example id="11">

<example id="12">
<business_question>
Qual a população dos municípios que são capitais estaduais?
</business_question>

<sql_query>
SELECT 
    mu.nome_municipio,
    uf.sigla_uf,
    SUM(pop."TOTAL") AS populacao_total
FROM 
    iesb.public."Censo_20222_Populacao_Idade_Sexo" AS pop
INNER JOIN 
    iesb.public.municipio AS mu 
    ON pop."CO_MUNICIPIO" = mu.codigo_municipio_dv
INNER JOIN 
    iesb.public.unidade_federacao AS uf 
    ON mu.cd_uf = uf.cd_uf
WHERE 
    mu.municipio_capital = 'Sim'
GROUP BY 
    mu.nome_municipio,
    uf.sigla_uf
ORDER BY 
    populacao_total DESC;
</sql_query>
</example id="12">

<example id="13">
<business_question>
Qual a população feminina entre 18 e 29 anos na região Sudeste?
</business_question>

<sql_query>
SELECT 
    SUM(pop."TOTAL") AS populacao_feminina_18_a_29_anos
FROM 
    iesb.public."Censo_20222_Populacao_Idade_Sexo" AS pop
INNER JOIN 
    iesb.public.municipio AS mu 
    ON pop."CO_MUNICIPIO" = mu.codigo_municipio_dv
INNER JOIN 
    iesb.public.unidade_federacao AS uf 
    ON mu.cd_uf = uf.cd_uf
INNER JOIN 
    iesb.public.regiao AS r 
    ON uf.cd_regiao = r.cd_regiao
WHERE 
    r.nome_regiao = 'Sudeste'
    AND pop."SEXO" = 'Mulheres'
    AND pop."IDADE" BETWEEN 18 AND 29;
</sql_query>
</example id="13">

<example id="14">
<business_question>
Quantos homens com 65 anos ou mais existem nos municípios que são capitais?
</business_question>

<sql_query>
SELECT 
    SUM(pop."TOTAL") AS populacao_homens_65_mais
FROM 
    iesb.public."Censo_20222_Populacao_Idade_Sexo" AS pop
INNER JOIN 
    iesb.public.municipio AS mu 
    ON pop."CO_MUNICIPIO" = mu.codigo_municipio_dv
WHERE 
    mu.municipio_capital = 'Sim'
    AND pop."SEXO" = 'Homens'
    AND pop."IDADE" >= 65;
</sql_query>
</example id="14">

<example id="15">
<business_question>
Quais municípios têm a maior proporção de crianças (0-14 anos)?
</business_question>

<sql_query>
SELECT 
    mu.nome_municipio,
    uf.sigla_uf,
    SUM(CASE WHEN pop."IDADE" BETWEEN 0 AND 14 THEN pop."TOTAL" ELSE 0 END) AS populacao_criancas,
    SUM(pop."TOTAL") AS populacao_total,
    ROUND(
        100.0 * SUM(CASE WHEN pop."IDADE" BETWEEN 0 AND 14 THEN pop."TOTAL" ELSE 0 END) 
        / NULLIF(SUM(pop."TOTAL"), 0), 
        2
    ) AS percentual_criancas
FROM 
    iesb.public."Censo_20222_Populacao_Idade_Sexo" AS pop
INNER JOIN 
    iesb.public.municipio AS mu 
    ON pop."CO_MUNICIPIO" = mu.codigo_municipio_dv
INNER JOIN 
    iesb.public.unidade_federacao AS uf 
    ON mu.cd_uf = uf.cd_uf
GROUP BY 
    mu.nome_municipio,
    uf.sigla_uf
ORDER BY 
    percentual_criancas DESC
LIMIT 20;
</sql_query>
</example id="15">

<example id="16">
<business_question>
Qual a população total da região Centro-Oeste por faixa etária decenal (0-9, 10-19, etc.)?
</business_question>

<sql_query>
SELECT 
    CASE 
        WHEN pop."IDADE" BETWEEN 0 AND 9 THEN '0-9 anos'
        WHEN pop."IDADE" BETWEEN 10 AND 19 THEN '10-19 anos'
        WHEN pop."IDADE" BETWEEN 20 AND 29 THEN '20-29 anos'
        WHEN pop."IDADE" BETWEEN 30 AND 39 THEN '30-39 anos'
        WHEN pop."IDADE" BETWEEN 40 AND 49 THEN '40-49 anos'
        WHEN pop."IDADE" BETWEEN 50 AND 59 THEN '50-59 anos'
        WHEN pop."IDADE" BETWEEN 60 AND 69 THEN '60-69 anos'
        WHEN pop."IDADE" BETWEEN 70 AND 79 THEN '70-79 anos'
        WHEN pop."IDADE" BETWEEN 80 AND 89 THEN '80-89 anos'
        WHEN pop."IDADE" >= 90 THEN '90+ anos'
    END AS faixa_etaria,
    SUM(pop."TOTAL") AS populacao_total
FROM 
    iesb.public."Censo_20222_Populacao_Idade_Sexo" AS pop
INNER JOIN 
    iesb.public.municipio AS mu 
    ON pop."CO_MUNICIPIO" = mu.codigo_municipio_dv
INNER JOIN 
    iesb.public.unidade_federacao AS uf 
    ON mu.cd_uf = uf.cd_uf
INNER JOIN 
    iesb.public.regiao AS r 
    ON uf.cd_regiao = r.cd_regiao
WHERE 
    r.nome_regiao = 'Centro-Oeste'
GROUP BY 
    faixa_etaria
ORDER BY 
    MIN(pop."IDADE");
</sql_query>
</example id="16">

<example id="17">
<business_question>
Quais são os 5 municípios mais populosos de cada região?
</business_question>

<sql_query>
WITH populacao_municipio AS (
    SELECT 
        r.nome_regiao,
        mu.nome_municipio,
        uf.sigla_uf,
        SUM(pop."TOTAL") AS populacao_total
    FROM 
        iesb.public."Censo_20222_Populacao_Idade_Sexo" AS pop
    INNER JOIN 
        iesb.public.municipio AS mu 
        ON pop."CO_MUNICIPIO" = mu.codigo_municipio_dv
    INNER JOIN 
        iesb.public.unidade_federacao AS uf 
        ON mu.cd_uf = uf.cd_uf
    INNER JOIN 
        iesb.public.regiao AS r 
        ON uf.cd_regiao = r.cd_regiao
    GROUP BY 
        r.nome_regiao,
        mu.nome_municipio,
        uf.sigla_uf
),
ranked_municipios AS (
    SELECT 
        nome_regiao,
        nome_municipio,
        sigla_uf,
        populacao_total,
        ROW_NUMBER() OVER (PARTITION BY nome_regiao ORDER BY populacao_total DESC) AS ranking
    FROM 
        populacao_municipio
)
SELECT 
    nome_regiao,
    nome_municipio,
    sigla_uf,
    populacao_total,
    ranking
FROM 
    ranked_municipios
WHERE 
    ranking <= 5
ORDER BY 
    nome_regiao,
    ranking;
</sql_query>
</example id="17">
</examples>

<best_practices>
1. Always use proper table aliases for readability (pop for population table, mu for municipio)
2. Include ORDER BY clauses to return results in meaningful order (usually DESC for population totals)
3. Use descriptive column aliases in SELECT statements (e.g., populacao_total instead of just sum)
4. When joining tables, always specify the join condition explicitly using INNER JOIN
5. For string comparisons in WHERE clauses, use exact matches with proper capitalization
6. Remember that "TOTAL" column in census table MUST be quoted due to uppercase naming
7. Always aggregate with SUM() when working with population data from the census table
</best_practices>

<important_notes>
- The Censo_20222_Populacao_Idade_Sexo table has "TOTAL" in uppercase and REQUIRES quotes
- The census table uses "CO_MUNICIPIO" (uppercase with quotes) for the join key
- Municipality reference table uses codigo_municipio_dv (lowercase) as the foreign key
- All population queries should use SUM("TOTAL") to aggregate demographic segments
</important_notes>

<instructions>
- If the user's question matches closely with one of the examples above, adapt the query pattern accordingly
- Always include proper table aliases and descriptive column names
- For geographic breakdowns, use appropriate GROUP BY based on the requested level of detail
</instructions>
"""

saude = """
<context>
This subcategory focuses on Brazilian healthcare data from DATASUS (Departamento de Informática do SUS).
The main table is:
- sus_procedimento_ambulatorial: Outpatient procedure data with quantities and values organized by temporal and geographic dimensions
</context>

<query_patterns>
Common query patterns for this subcategory:
1. Temporal aggregations: GROUP BY year and/or month
2. Geographic aggregations: GROUP BY region, UF (state), and/or municipality
3. Procedure type filters: Use specific qtd_XX or vl_XX columns for procedure groups/types
4. Combined dimensions: Mix temporal + geographic + procedure type
5. Always use SUM() for quantities and values
6. Always use ORDER BY to return results in logical sequence
</query_patterns>

<examples>
<example id="1">
<business_question>
Quantos atendimentos ambulatoriais foram realizados pelo SUS por ano?
</business_question>

<sql_query>
SELECT
  ano_producao_ambulatorial,
  SUM(qtd_total) AS quantidade_total
FROM
  iesb.public.sus_procedimento_ambulatorial
GROUP BY
  ano_producao_ambulatorial
ORDER BY
  ano_producao_ambulatorial;
</sql_query>
</example id="1">

<example id="2">
<business_question>
Qual o total investido pelo SUS nos atendimentos ambulatoriais por ano?
</business_question>

<sql_query>
SELECT
  ano_producao_ambulatorial,
  SUM(vl_total) AS valor_total
FROM
  iesb.public.sus_procedimento_ambulatorial
GROUP BY
  ano_producao_ambulatorial
ORDER BY
  ano_producao_ambulatorial;
</sql_query>
</example id="2">

<example id="3">
<business_question>
Qual a quantidade de atendimentos ambulatoriais e total investido pelo SUS por ano/mês?
</business_question>

<sql_query>
SELECT
  ano_producao_ambulatorial,
  mes_producao_ambulatorial,
  SUM(qtd_total) AS quantidade_total,
  SUM(vl_total) AS valor_total
FROM
  iesb.public.sus_procedimento_ambulatorial
GROUP BY
  ano_producao_ambulatorial,
  mes_producao_ambulatorial
ORDER BY
  ano_producao_ambulatorial,
  mes_producao_ambulatorial;
</sql_query>
/example id="3">

<example id="4">
<business_question>
Qual a quantidade de atendimentos ambulatoriais e total investido pelo SUS por ano/UF/mês?
</business_question>

<sql_query>
SELECT
  ano_producao_ambulatorial,
  uf_nome,
  mes_producao_ambulatorial,
  SUM(qtd_total) AS quantidade_total,
  SUM(vl_total) AS valor_total
FROM
  iesb.public.sus_procedimento_ambulatorial
GROUP BY
  ano_producao_ambulatorial,
  uf_nome,
  mes_producao_ambulatorial
ORDER BY
  ano_producao_ambulatorial,
  uf_nome,
  mes_producao_ambulatorial;
</sql_query>
</example id="4">

<example id="5">
<business_question>
Qual a quantidade de atendimentos ambulatoriais e total investido pelo SUS por ano/UF/mês, no estado de São Paulo (SP)?
</business_question>

<sql_query>
SELECT
  ano_producao_ambulatorial,
  uf_nome,
  mes_producao_ambulatorial,
  SUM(qtd_total) AS quantidade_total,
  SUM(vl_total) AS valor_total
FROM
  iesb.public.sus_procedimento_ambulatorial
WHERE
  uf_sigla = 'SP'
GROUP BY
  ano_producao_ambulatorial,
  uf_nome,
  mes_producao_ambulatorial
ORDER BY
  ano_producao_ambulatorial,
  uf_nome,
  mes_producao_ambulatorial;
</sql_query>
</example id="5">

<example id="6">
<business_question>
Qual o total de atendimentos ambulatoriais e valores investidos de "Procedimentos clínicos" no SUS por ano?
</business_question>

<sql_query>
SELECT
  ano_producao_ambulatorial,
  SUM(qtd_03) AS quantidade_procedimentos_clinicos,
  SUM(vl_03) AS valor_procedimentos_clinicos
FROM
  iesb.public.sus_procedimento_ambulatorial
GROUP BY
  ano_producao_ambulatorial
ORDER BY
  ano_producao_ambulatorial;
</sql_query>
</example id="6">

<example id="7">
<business_question>
Qual o total de atendimentos ambulatoriais e valores investidos de "Procedimentos clínicos" no SUS por ano/mês?
</business_question>

<sql_query>
SELECT
  ano_producao_ambulatorial,
  mes_producao_ambulatorial,
  SUM(qtd_03) AS quantidade_procedimentos_clinicos,
  SUM(vl_03) AS valor_procedimentos_clinicos
FROM
  iesb.public.sus_procedimento_ambulatorial
GROUP BY
  ano_producao_ambulatorial,
  mes_producao_ambulatorial
ORDER BY
  ano_producao_ambulatorial,
  mes_producao_ambulatorial;
</sql_query>
</example id="7">

<example id="8">
<business_question>
Qual o total de atendimentos ambulatoriais e valores investidos de "Procedimentos clínicos" no SUS por ano/mês/região?
</business_question>

<sql_query>
SELECT
  ano_producao_ambulatorial,
  mes_producao_ambulatorial,
  regiao_nome,
  SUM(qtd_03) AS quantidade_procedimentos_clinicos,
  SUM(vl_03) AS valor_procedimentos_clinicos
FROM
  iesb.public.sus_procedimento_ambulatorial
GROUP BY
  ano_producao_ambulatorial,
  mes_producao_ambulatorial,
  regiao_nome
ORDER BY
  ano_producao_ambulatorial,
  mes_producao_ambulatorial,
  regiao_nome;
</sql_query>
</example id="8">

<example id="9">
<business_question>
Qual o total de atendimentos ambulatoriais e valores investidos de "Procedimentos clínicos" no SUS por ano/mês/região/UF?
</business_question>

<sql_query>
SELECT
  ano_producao_ambulatorial,
  mes_producao_ambulatorial,
  regiao_nome,
  uf_nome,
  SUM(qtd_03) AS quantidade_procedimentos_clinicos,
  SUM(vl_03) AS valor_procedimentos_clinicos
FROM
  iesb.public.sus_procedimento_ambulatorial
GROUP BY
  ano_producao_ambulatorial,
  mes_producao_ambulatorial,
  regiao_nome,
  uf_nome
ORDER BY
  ano_producao_ambulatorial,
  mes_producao_ambulatorial,
  regiao_nome,
  uf_nome;
</sql_query>
</example id="9">

<example id="10">
<business_question>
Qual o total de atendimentos ambulatoriais e valores investidos de "Tratamentos em nefrologia" no SUS por ano/mês/região/UF?
</business_question>

<sql_query>
SELECT
  ano_producao_ambulatorial,
  mes_producao_ambulatorial,
  regiao_nome,
  uf_nome,
  SUM(qtd_0305) AS quantidade_tratamentos_nefrologia,
  SUM(vl_0305) AS valor_tratamentos_nefrologia
FROM
  iesb.public.sus_procedimento_ambulatorial
GROUP BY
  ano_producao_ambulatorial,
  mes_producao_ambulatorial,
  regiao_nome,
  uf_nome
ORDER BY
  ano_producao_ambulatorial,
  mes_producao_ambulatorial,
  regiao_nome,
  uf_nome;
</sql_query>
</example id="10">

<example id="11">
<business_question>
Qual a evolução mensal de exames laboratoriais clínicos em São Paulo?
</business_question>

<sql_query>
SELECT
  ano_producao_ambulatorial,
  mes_producao_ambulatorial,
  SUM(qtd_0202) AS quantidade_exames_laboratoriais,
  SUM(vl_0202) AS valor_exames_laboratoriais
FROM
  sus_procedimento_ambulatorial
WHERE
  uf_sigla = 'SP'
GROUP BY
  ano_producao_ambulatorial,
  mes_producao_ambulatorial
ORDER BY
  ano_producao_ambulatorial,
  mes_producao_ambulatorial;
</sql_query>
</example id="11">

<example id="12">
<business_question>
Qual o valor total gasto com medicamentos ambulatoriais pelo SUS por ano?
</business_question>

<sql_query>
SELECT 
    ano_producao_ambulatorial, 
    SUM(vl_06) AS valor_total_medicamentos
FROM 
    sus_procedimento_ambulatorial
GROUP BY 
    ano_producao_ambulatorial
ORDER BY 
    ano_producao_ambulatorial;
</sql_query>
</example id="12">

<example id="13">
<business_question>
Quanto foi investido em medicamentos hospitalares vs. componentes especializados por ano/mês?
</business_question>

<sql_query>
SELECT
  ano_producao_ambulatorial,
  mes_producao_ambulatorial,
  SUM(vl_0603) AS valor_medicamentos_hospitalares,
  SUM(vl_0604) AS valor_componentes_especializados
FROM
  sus_procedimento_ambulatorial
GROUP BY
  ano_producao_ambulatorial,
  mes_producao_ambulatorial
ORDER BY
  ano_producao_ambulatorial,
  mes_producao_ambulatorial;
</sql_query>
</example id="13">

<example id="14">
<business_question>
Qual o trimestre com maior número de procedimentos ambulatoriais em 2024?
</business_question>

<sql_query>
SELECT 
  CASE 
    WHEN mes_producao_ambulatorial IN ('01', '02', '03') THEN 'Q1'
    WHEN mes_producao_ambulatorial IN ('04', '05', '06') THEN 'Q2'
    WHEN mes_producao_ambulatorial IN ('07', '08', '09') THEN 'Q3'
    WHEN mes_producao_ambulatorial IN ('10', '11', '12') THEN 'Q4'
  END AS trimestre,
  SUM(qtd_total) AS quantidade_total
FROM 
  sus_procedimento_ambulatorial
WHERE 
  ano_producao_ambulatorial = '2024'
GROUP BY 
  CASE 
    WHEN mes_producao_ambulatorial IN ('01', '02', '03') THEN 'Q1'
    WHEN mes_producao_ambulatorial IN ('04', '05', '06') THEN 'Q2'
    WHEN mes_producao_ambulatorial IN ('07', '08', '09') THEN 'Q3'
    WHEN mes_producao_ambulatorial IN ('10', '11', '12') THEN 'Q4'
  END
ORDER BY 
  quantidade_total DESC;
</sql_query>
</example id="14">
</examples>

<best_practices>
1. Always use SUM() for aggregating quantities (qtd_*) and values (vl_*)
2. Use descriptive column aliases that clearly indicate what is being measured
3. For temporal queries, always order by year and month in ascending order
4. For geographic queries, include region/UF/municipality in ORDER BY for consistent, readable results
5. When filtering by state, use uf_sigla (2-letter code like 'SP') in WHERE clause, but display uf_nome in SELECT
6. Remember the hierarchy: qtd_total = sum of qtd_01 through qtd_09
7. Group-level columns (qtd_03) are aggregations of subgroup columns (qtd_0301, qtd_0302, qtd_0303, etc.)
8. All column names are lowercase with underscores (no special characters)
</best_practices>

<important_notes>
- All quantity columns start with qtd_ and all value columns start with vl_
- Geographic hierarchy: regiao_nome > uf_nome (uf_sigla) > municipio_nome
- Procedure hierarchy: Groups (01-09) > Subgroups (0101-0905)
- Always aggregate with SUM() since data is already at municipality+month granularity
- Years are stored as character strings (e.g., '2024')
- Months are stored as 2-digit character strings: '01' through '12'
- Value columns represent monetary values in Brazilian Reais (R$)
</important_notes>

<instructions>
- If the user's question matches closely with one of the examples above, adapt the query pattern accordingly
- Always include proper ORDER BY clauses for temporal and/or geographic sorting
- Use descriptive column aliases that make results easy to interpret
- For questions about specific procedure types, identify the correct qtd_XX/vl_XX columns from the schema
- Remember to use SUM() aggregation even for already-aggregated columns (qtd_total, vl_total, etc.)
</instructions>
"""