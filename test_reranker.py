from reranker import Reranker

soru = "Kamera bağlantısı kesildiğinde ne olur?"

parcalar = [
    {
        "text": "Kamera bağlantısı kesildiğinde alarm oluşturulur.",
        "page": 12
    },
    {
        "text": "Kamera 4K çözünürlüğe sahiptir.",
        "page": 5
    },
    {
        "text": "Ağ bağlantısı kaybolduğunda sistem bildirim gönderir.",
        "page": 18
    }
]

reranker = Reranker()

sonuclar = reranker.sirala(soru, parcalar, top_k=3)

from pathlib import Path

dosya_yolu = Path(__file__).resolve().parent / "reranker_sonuclari.txt"

with open(dosya_yolu, "w", encoding="utf-8") as dosya:
    dosya.write(f"SORU: {soru}\n\n")

    for sira, sonuc in enumerate(sonuclar, start=1):
        dosya.write(f"SONUÇ {sira}\n")
        dosya.write(f"Sayfa: {sonuc['page']}\n")
        dosya.write(f"Puan: {sonuc['rerank_score']:.6f}\n")
        dosya.write(f"Metin: {sonuc['text']}\n")
        dosya.write("-" * 50 + "\n")

print("Reranker sonuçları TXT dosyasına kaydedildi.") 

for sonuc in sonuclar:
    print("Sayfa:", sonuc["page"])
    print("Puan:", sonuc["rerank_score"])
    print("Metin:", sonuc["text"])
    print("--------------------")