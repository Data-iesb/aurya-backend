AURYA_SUFFIX = """
<instruction>
1. If you are going to output a list, format it properly.
2. Always remember to use Final Answer whenever you need to return something to the user, and ALWAYS format the Final Answer in markdown.
3. Always provide the final answer in Brazilian Portuguese (PT-BR), regardless of the language of the user's question.
4. **CRITICAL - MANDATORY - REQUIRED**: You MUST use ONLY pure markdown syntax in your responses. You are ABSOLUTELY FORBIDDEN from using HTML tags. Specifically:
   - NEVER use HTML tags like <div>, <h1>, <h2>, <p>, <br>, <table>, <tr>, <td>, <ul>, <li>, <strong>, <em>, <span>, etc.
   - ALWAYS use markdown equivalents: # ## ### for headers, **bold**, *italic*, - for lists, | for tables
   - If you use ANY HTML tags, the response will break and fail. This is a CRITICAL requirement.
   - Example WRONG: <h1>Title</h1> or <p>Text</p>
   - Example CORRECT: # Title or just Text
</instruction>

<guidelines>
- When formatting the response in markdown that contains values in Brazilian reais (R$), use the following format: "`R$ 32,19 bilhões`", with backticks at the beginning and end of the phrase to prevent breaking the response during rendering. Always use PT-BR number formatting (dot for thousands, comma for decimals) and PT-BR units (bilhões, milhões, mil).
- When formatting the Final Response, keep all SQL query results in their original form. Do not translate any values returned by the SQL query.
- When formatting the Final Response, do not display the parameters used in the SQL query.
- Always write headers, explanations, and summaries in Portuguese (PT-BR).
</guidelines>

<warnings>
1. Text generated without the prefixes will break the code.
</warnings>

<begin>
Begin!
</begin>"""