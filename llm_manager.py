# will use ollama to call qwen3:8b llm model.
import ollama


# TODO: implement the function to call the LLM model using ollama. send only the query given
def ask_direct_llm(query: str) -> str:
     

    response = ollama.chat(
                                    model="qwen3:4b",
                                    messages=[
                                        {
                                            "role": "user",
                                            "content": query
                                        }
                                    ] ,
                                    
                                    think=False,
                                    options={
                                        "num_ctx": 8192,
                                        "num_predict": 6000,
                                        "temperature": 0.3,
                                        "think": False
                                    }
                                )
    print (response)
    return response.get("content", "")
    

# TODO: implement the function to call the LLM model using ollama. send the query to preprocessing, then ask the result to llm
def ask(query: str) -> str:
    return ask_direct_llm(query)


