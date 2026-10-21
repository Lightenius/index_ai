from ollama import Client
import time

client = Client(host="http://127.0.0.1:11434", timeout=120.0)

messages = [
    {"role": "system", "content": "Sen şirket içinde kullanılan Türkçe bir asistansın."},
    {"role": "user", "content": "yardımcı ol"}
]

print("İstek gönderiliyor", flush=True)
t0 = time.perf_counter()

stream = client.chat(
    model="qwen3:4b",
    messages=messages,
    stream=True,
    think=False,
    options={
        "num_ctx": 4096,
        "num_predict": 350,
        "temperature": 0.4
    }
)

print("Akış alındı; parçalar bekleniyor", flush=True)

for chunk in stream:
    print(
        f"\n[parça] {chunk.message.content!r} "
        f"done={chunk.done}",
        flush=True
    )

print(f"Toplam süre: {time.perf_counter() - t0:.2f} sn")