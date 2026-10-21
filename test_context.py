
from context import (
    sayfalari_genislet,
    baglam_hazirla,
    baglami_txt_kaydet
)

from documents import belgeleri_getir


# Kayıtlı PDF'leri getir
belgeler = belgeleri_getir()

if not belgeler:
    print("Test için önce sisteme bir PDF yüklemelisin.")

else:
    belge = belgeler[0]

    # Reranker'ın 2. sayfayı seçtiğini varsayıyoruz.
    ornek_sonuclar = [
        {
            "pdf_id": belge["id"],
            "page": 2,
            "text": "Test metni"
        }
    ]

    # Komşu sayfaları getir
    sayfalar = sayfalari_genislet(
        ornek_sonuclar,
        komsu=1
    )

    print("Seçilen sayfalar:")
    for sayfa in sayfalar:
        print(sayfa["sayfa"])

    # LLM'ye gönderilecek metni hazırla
    baglam = baglam_hazirla(
        sayfalar,
        max_karakter=16000
    )

    # TXT dosyasına kaydet
    dosya = baglami_txt_kaydet(
        "Test sorusu",
        baglam
    )

    print("TXT oluşturuldu:", dosya)
