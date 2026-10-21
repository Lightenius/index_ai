from sentence_transformers import CrossEncoder


class Reranker:

    def __init__(self):
        self.model = CrossEncoder("BAAI/bge-reranker-v2-m3")

    def sirala(self, soru, parcalar, top_k=15):

        if not parcalar:
            return []

        eslesmeler = [
            (soru, parca["text"])
            for parca in parcalar
        ]

        puanlar = self.model.predict(eslesmeler)

        sonuclar = []

        for parca, puan in zip(parcalar, puanlar):
            sonuc = parca.copy()
            sonuc["rerank_score"] = float(puan)
            sonuclar.append(sonuc)

        sonuclar.sort(
            key=lambda x: x["rerank_score"],
            reverse=True
        )

        return sonuclar[:top_k]