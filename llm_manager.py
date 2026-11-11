# will use ollama to call qwen3:8b llm model.
import re
import time

from logger import Logger
from urllib import response

import ollama


def _format_response(output, start_time: float, benchmark: bool) -> str:
    end_time = time.perf_counter()
    raw_output = output.message.content
    if not raw_output or not raw_output.strip():
        raise RuntimeError("The LLM returned an empty response.")

    response = re.sub(
        r".*?</think>",
        "",
        raw_output,
        flags=re.DOTALL,
    ).strip()
    if not response:
        raise RuntimeError("The LLM returned no response outside its thinking block.")

    Logger.perf(
        f"Time taken for LLM response: {end_time - start_time:.6f} seconds"
    )
    print(response)
    if benchmark:
        response += (
            "\n\nTime taken for LLM response: "
            f"{end_time - start_time:.6f} seconds"
        )

    return response


# TODO: implement the function to call the LLM model using ollama. send only the query given
def ask_direct_llm(query: str, llm_name = "qwen3:8b", benchmark = True) -> str:
    start_time = time.perf_counter()
    Logger.info(f"Sending message to LLM ({llm_name}). Awaiting response.")

    output = ollama.chat(
                                    model=llm_name,
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

    return _format_response(output, start_time, benchmark)


async def ask_direct_llm_async(
    query: str,
    llm_name: str = "qwen3:8b",
    benchmark: bool = True,
) -> str:
    start_time = time.perf_counter()
    Logger.info(f"Sending message to LLM ({llm_name}). Awaiting response.")

    async with ollama.AsyncClient() as client:
        output = await client.chat(
            model=llm_name,
            messages=[{"role": "user", "content": query}],
            think=False,
            options={
                "num_ctx": 8192,
                "num_predict": 6000,
                "temperature": 0.3,
                "think": False,
            },
        )

    return _format_response(output, start_time, benchmark)

# TODO: implement the function to call the LLM model using ollama. send the query to preprocessing, then ask the result to llm
def ask(query: str) -> str:
    return ask_direct_llm(query)
