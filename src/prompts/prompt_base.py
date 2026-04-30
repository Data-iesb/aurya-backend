from langchain_core.prompts import PromptTemplate
from src.prompts.temas import *
from src.prompts.react_prompts import *
from src.prompts.response_prompts import *
from src.prompts.router_prompts import *

# Create PromptTemplate
aurya_template = "\n\n".join([
    AURYA_PREFIX,
    "{tools}",
    system_prefix_sql,
    AURYA_SUFFIX,
])

claude_sql_prompt = PromptTemplate.from_template(aurya_template)
