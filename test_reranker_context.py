
from pathlib import Path

from documents import belgeleri_getir, pdf_oku
from reranker import Reranker
from context import (
    sayfalari_genislet,
    baglam_hazirla,
    baglami_txt_kaydet
)


# 1. Kullanıcının sorusu
soru = "Kamera bağlantısı kesildiğinde ne olur?"


# 2. Kayıtlı PDF'leri getir
belgeler = belgeleri_getir()

if not belgeler:
    print("Sistemde kayıtlı PDF bulunamadı.")

else:
    parcalar = []

    # 3. Gerçek PDF'lerden metin parçaları oluştur
    for belge in belgeler:
        sayfalar = pdf_oku(
            belge["dosya_yolu"],
            belge["hash"]
        )

        for sayfa in sayfalar:
            metin = sayfa["metin"]

            for baslangic in range(0, len(metin), 1200):
                parca = metin[baslangic:baslangic + 1200]

                if not parca.strip():
                    continue

                parcalar.append({
                    "pdf_id": belge["id"],
                    "page": sayfa["sayfa"],
                    "text": parca,
                    "chunk_id": (
                        f"{belge['id']}_{sayfa['sayfa']}_{baslangic}"
                    )
                })

    print("Toplam parça sayısı:", len(parcalar))

    if not parcalar:
        print("PDF'lerde okunabilir metin bulunamadı.")

    else:
        # 4. Reranker modelini çalıştır
        reranker = Reranker()

        siralanmis = reranker.sirala(
            soru,
            parcalar,
            top_k=3
        )

        # 5. Reranker sonuçlarını TXT dosyasına kaydet
        cikti = (
            Path(__file__).resolve().parent
            / "reranker_sonuclari.txt"
        )

        with open(cikti, "w", encoding="utf-8") as dosya:
            dosya.write(f"SORU: {soru}\n\n")

            for sira, sonuc in enumerate(siralanmis, start=1):
                dosya.write(f"SONUÇ {sira}\n")
                dosya.write(f"PDF ID: {sonuc['pdf_id']}\n")
                dosya.write(f"Sayfa: {sonuc['page']}\n")
                dosya.write(
                    f"Puan: {sonuc['rerank_score']:.6f}\n"
                )
                dosya.write(f"Metin:\n{sonuc['text']}\n")
                dosya.write("-" * 50 + "\n\n")

        print("\nReranker sonuçları:")
        for sonuc in siralanmis:
            print(
                "Sayfa:", sonuc["page"],
                "Puan:", round(sonuc["rerank_score"], 4)
            )

        # 6. Context ile komşu sayfaları getir
        secilen_sayfalar = sayfalari_genislet(
            siralanmis,
            komsu=1
        )

        print("\nContext sayfaları:")
        for sayfa in secilen_sayfalar:
            print(sayfa["ad"], "- Sayfa:", sayfa["sayfa"])

        # 7. LLM'ye gönderilecek metni hazırla
        baglam = baglam_hazirla(
            secilen_sayfalar,
            max_karakter=16000
        )

        # 8. Context sonucunu TXT'ye kaydet
        baglami_txt_kaydet(soru, baglam)

        print("\nTest tamamlandı.")
        print("reranker_sonuclari.txt oluşturuldu.")
        print("llm_context.txt oluşturuldu.")
