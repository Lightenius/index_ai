
from pathlib import Path

from documents import belgeleri_getir, pdf_oku


def sayfalari_genislet(siralanmis_parcalar, komsu=1):
    """
    Reranker sonuçlarının bulunduğu sayfaları ve
    komşu sayfalarını bulur. Tekrarları kaldırır.
    """

    belgeler = {
        belge["id"]: belge
        for belge in belgeleri_getir()
    }

    secilen = set()
    oncelik = {}

    # Reranker sonuçları en yüksek puandan başlar.
    for sira, parca in enumerate(siralanmis_parcalar):

        belge_id = parca["pdf_id"]
        sayfa_no = int(parca["page"])

        if belge_id not in belgeler:
            continue

        belge = belgeler[belge_id]

        sayfalar = pdf_oku(
            belge["dosya_yolu"],
            belge["hash"]
        )

        mevcut = {s["sayfa"] for s in sayfalar}

        for numara in range(
            sayfa_no - komsu,
            sayfa_no + komsu + 1
        ):
            if numara in mevcut:
                anahtar = (belge_id, numara)
                secilen.add(anahtar)

                # Sayfanın en iyi eşleşme sırasını sakla.
                if anahtar not in oncelik:
                    oncelik[anahtar] = sira

    # PDF sayfalarını tekrar tekrar okumamak için
    # belge başına bir kez sözlük oluşturuyoruz.
    sayfa_indeksleri = {}

    for belge_id, _ in secilen:
        if belge_id not in sayfa_indeksleri:
            belge = belgeler[belge_id]

            sayfalar = pdf_oku(
                belge["dosya_yolu"],
                belge["hash"]
            )

            sayfa_indeksleri[belge_id] = {
                s["sayfa"]: s["metin"]
                for s in sayfalar
            }

    sonuc = []

    for belge_id, sayfa_no in sorted(
        secilen,
        key=lambda x: (
            oncelik[x],
            x[0],
            x[1]
        )
    ):
        sonuc.append({
            "pdf_id": belge_id,
            "ad": belgeler[belge_id]["ad"],
            "sayfa": sayfa_no,
            "metin": sayfa_indeksleri[belge_id][sayfa_no]
        })

    return sonuc


def baglam_hazirla(sayfalar, max_karakter=16000):
    """
    Sayfa metinlerini LLM için düzenler.

    Karakter sınırı uygular. Bu, kesin bir
    token sayımı değildir.
    """

    metinler = []
    kullanilan = 0

    for sayfa in sayfalar:

        baslik = (
            f"Dosya: {sayfa['ad']}\n"
            f"Sayfa: {sayfa['sayfa']}\n"
        )

        icerik = sayfa["metin"].strip()

        blok = baslik + icerik + "\n\n---\n\n"

        kalan = max_karakter - kullanilan


        if len(blok) > kalan:
            print(f"Context budget: skipped {sayfa['ad']} / {sayfa['sayfa']}")
            # Sayfayı ortasından kesmek yerine
            # bu sürümde sayfayı atlıyoruz.
            continue

        metinler.append(blok)
        kullanilan += len(blok)

    return "".join(metinler)


def baglami_txt_kaydet(soru, baglam):
    """
    LLM'ye gönderilecek kaynak metnini TXT'ye yazar.
    """

    dosya_yolu = (
        Path(__file__).resolve().parent
        / "llm_context.txt"
    )

    with open(dosya_yolu, "w", encoding="utf-8") as dosya:
        dosya.write("KULLANICI SORUSU:\n")
        dosya.write(soru + "\n\n")
        dosya.write("LLM'YE GÖNDERİLECEK KAYNAKLAR:\n\n")
        dosya.write(baglam if baglam else "Kaynak bulunamadı.")

    return dosya_yolu
