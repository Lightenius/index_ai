# will use ollama to call qwen3:8b llm model.
import re
import time

from urllib import response

import ollama

from embedding import Embedding


# TODO: implement the function to call the LLM model using ollama. send only the query given
def ask_direct_llm(query: str) -> str:
    start_time = time.perf_counter()

    output = ollama.chat(
                                    model="qwen3:8b",
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

    end_time = time.perf_counter()

    raw_output = (
        output.message.content
        or "Failed to generate response."
    )

    clean_output = re.sub(r".*?</think>", "", raw_output, flags=re.DOTALL).strip()
    response = clean_output if clean_output else raw_output

    print(f"Time taken for LLM response: {end_time - start_time:.6f} seconds")
    print (response)
    return response + "\n\nTime taken for LLM response: {:.6f} seconds".format(end_time - start_time)

# TODO: implement the function to call the LLM model using ollama. send the query to preprocessing, then ask the result to llm
def ask(query: str) -> str:
    return ask_direct_llm(query)

def get_ctx_for(history: list) -> list:
    embedding = Embedding("data/vector_db.db")
    ctx = embedding.search(history[-1]["content"], n=3)
    return ctx

def ask_msglist_llm(history: list) -> str:
    if history == []:
        return "No message history available."
    start_time = time.perf_counter()

    system_msg = [
        {
            "role": "system",
            "content": """
            


            """
        }
    ]

    ctx_msg = get_ctx_for(history)

    msg_list = history[0: -2] + system_msg + ctx_msg + history[-1]

    output = ollama.chat(
                                    model="qwen3:8b",
                                    messages= msg_list,

                                    think=False,
                                    options={
                                        "num_ctx": 8192,
                                        "num_predict": 6000,
                                        "temperature": 0.3,
                                        "think": False
                                    }
                                )

    end_time = time.perf_counter()

    raw_output = (
        output.message.content
        or "Failed to generate response."
    )

    clean_output = re.sub(r".*?</think>", "", raw_output, flags=re.DOTALL).strip()
    response = clean_output if clean_output else raw_output

    print(f"Time taken for LLM response: {end_time - start_time:.6f} seconds")
    print (response)
    return response + "\n\nTime taken for LLM response: {:.6f} seconds".format(end_time - start_time)

