# will use ollama to call qwen3:8b llm model.

# TODO: implement the function to call the LLM model using ollama. send only the query given
def ask_direct_llm(query: str) -> str:
    return ""

# TODO: implement the function to call the LLM model using ollama. send the query to preprocessing, then ask the result to llm
def ask(query: str) -> str:
    return ask_direct_llm(query)


