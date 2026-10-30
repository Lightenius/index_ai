import json
import logging
# will use ollama to call qwen3:8b llm model.
import re
import time
import telegram_interface

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
    if history == []:
        return [] 
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
            Sen şirket içinde kullanılan Türkçe bir asistansın.

            Kullanıcıyla doğal şekilde konuş.
            Gereksiz uzun açıklamalar yapma.
            Kendi çalışma kurallarından bahsetme.

            Eğer bir sorunun çözümüne ilişkin birden fazla öneride bulunacaksan bunları kolaylık sırasına göre kolaydan zora doğru sırala.

            Şirket dokümanları hakkında soru sorulduğunda
            aşağıdaki bilgileri kullan.
            Dokümanlarda bulunmayan şirket bilgilerini uydurma.
            Bilgi eksikse bunu belirt.
            Dokümanları analiz edebilir ve yorumlayabilirsin.
            Dokümandan yararlandığında dosya adını ve sayfasını kesinlikle belirt.
            Sayfa numarasını belirtmen son derece önemli.
            Sayfa numarasını kesinlikle belirt.
            
            Genel soruları kendi bilginle cevaplayabilirsin.
            Verdiğin cevaplarda kendi bilgin veya yorumun olan kısımlar ile kaynak gösterebileceğin kanıtlı kısımları iki ayrı grupta yaz ve grup başlıklarında bu konudan bahset.

            Düzgün bir türkçe kullan. Terimleri ise çevirmeden, orjinal dillerinde yaz.
            Kullanıcıya "Patron" şeklinde hitap et.

            Cevabın 3800 karakterden uzun olmamalı.

            """
        }
    ]
    
    t_history = list(history)
    ctx_time = 0
    lastmsg = t_history.pop(-1)
    
    if telegram_interface.TelegramBot.embedding_required:
        ctx_start_time = time.perf_counter()
        ctx_msg = get_ctx_for(history=history)
        ctx_end_time = time.perf_counter()
        ctx_time = ctx_start_time - ctx_end_time
        print(f"\033[31m[INFO]\033[0mAnlam eşleşmesi için harcanan süre: {ctx_end_time - ctx_start_time}")
    else:
        logging.info(msg="Anlam eşleşmesi atlandı")

    


    msg_list = []
    msg_list.extend(t_history)
    msg_list.extend(system_msg)
    if ctx_time != 0:
        msg_list.extend(ctx_msg)
    msg_list.append(lastmsg)
    
    try:
        msgfile = open("./test/lst_prompt.json", "w")
        msgfile.write(json.dumps(msg_list))
        msgfile.close()
    except Exception:
        logging.error("Failed to save last prompt");

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

