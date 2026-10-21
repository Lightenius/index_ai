
from pathlib import Path
import hashlib
import json
import re
import uuid
import threading
import datetime

import pymupdf
import streamlit as st


klasor = Path(__file__).resolve().parent
pdf_klasoru = klasor / "documents"
kayit_dosyasi = klasor / "documents.json"

pdf_klasoru.mkdir(exist_ok=True)

kilit = threading.RLock()


def belgeleri_getir():
    with kilit:
        if not kayit_dosyasi.exists():
            return []

        with open(kayit_dosyasi, "r", encoding="utf-8") as f:
            return json.load(f)


def belgeleri_kaydet(belgeler):
    gecici = kayit_dosyasi.with_suffix(".tmp")

    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(
            belgeler,
            f,
            ensure_ascii=False,
            indent=2
        )

    gecici.replace(kayit_dosyasi)


def belge_ekle(yuklenen_dosya):
    icerik = yuklenen_dosya.getvalue()

    if not icerik.startswith(b"%PDF-"):
        raise ValueError("Geçerli bir PDF dosyası seçin.")

    dosya_hash = hashlib.sha256(icerik).hexdigest()

    with kilit:
        belgeler = belgeleri_getir()

        for belge in belgeler:
            if belge["hash"] == dosya_hash:
                return False, belge

        belge_id = uuid.uuid4().hex
        dosya_yolu = pdf_klasoru / f"{belge_id}.pdf"

        dosya_yolu.write_bytes(icerik)

        yeni_belge = {
            "id": belge_id,
            "ad": Path(yuklenen_dosya.name).name,
            "hash": dosya_hash,
            "dosya_yolu": str(dosya_yolu)
        }

        belgeler.append(yeni_belge)
        belgeleri_kaydet(belgeler)

        return True, yeni_belge


def belge_sil(belge_id):
    with kilit:
        belgeler = belgeleri_getir()

        belge = next(
            (b for b in belgeler if b["id"] == belge_id),
            None
        )

        if belge is None:
            return False

        dosya_yolu = Path(belge["dosya_yolu"]).resolve()

        if dosya_yolu.parent != pdf_klasoru.resolve():
            raise ValueError("Geçersiz dosya yolu.")

        if dosya_yolu.exists():
            dosya_yolu.unlink()

        kalanlar = [
            b for b in belgeler if b["id"] != belge_id
        ]

        belgeleri_kaydet(kalanlar)
        pdf_oku.clear()

        return True


# --------------------------------------------------
# TABLO İŞLEMLERİ
# --------------------------------------------------

def tabloyu_markdown_yap(tablo):
    """
    PDF tablosunu Markdown formatına dönüştürür.
    """

    satirlar = tablo.extract()

    if not satirlar:
        return ""

    temiz_satirlar = []

    for satir in satirlar:
        temiz = [
            str(hucre or "")
            .replace("\n", " ")
            .replace("|", "\\|")
            .strip()
            for hucre in satir
        ]

        temiz_satirlar.append(temiz)

    sutun_sayisi = max(
        len(satir) for satir in temiz_satirlar
    )

    if sutun_sayisi < 2:
        return ""

    for satir in temiz_satirlar:
        satir.extend(
            [""] * (sutun_sayisi - len(satir))
        )

    baslik = temiz_satirlar[0]
    govde = temiz_satirlar[1:]

    satir_metni = [
        "| " + " | ".join(baslik) + " |",
        "| " + " | ".join(
            ["---"] * sutun_sayisi
        ) + " |"
    ]

    for satir in govde:
        satir_metni.append(
            "| " + " | ".join(satir) + " |"
        )

    return "\n".join(satir_metni)


def sayfa_metnini_cikar(sayfa):
    """
    PDF sayfasındaki normal metinleri ve tabloları
    konumlarına göre birleştirir.
    """

    tablo_bilgileri = []

    try:
        bulunan_tablolar = sayfa.find_tables()

        for tablo in bulunan_tablolar.tables:
            markdown = tabloyu_markdown_yap(tablo)

            if markdown:
                tablo_bilgileri.append({
                    "bbox": tuple(tablo.bbox),
                    "metin": markdown
                })

    except Exception as hata:
        print(
            f"Tablo algılama hatası: {hata}"
        )

    bloklar = sayfa.get_text("blocks")

    icerikler = []

    for blok in bloklar:
        x0, y0, x1, y1 = blok[:4]

        metin = str(blok[4]).strip()

        if not metin:
            continue

        blok_alani = pymupdf.Rect(
            x0, y0, x1, y1
        )

        tablo_ile_kesisiyor = any(
            blok_alani.intersects(
                pymupdf.Rect(tablo["bbox"])
            )
            for tablo in tablo_bilgileri
        )

        if tablo_ile_kesisiyor:
            continue

        icerikler.append({
            "y": y0,
            "x": x0,
            "metin": metin
        })

    for tablo in tablo_bilgileri:
        icerikler.append({
            "y": tablo["bbox"][1],
            "x": tablo["bbox"][0],
            "metin": tablo["metin"]
        })

    icerikler.sort(
        key=lambda icerik: (
            icerik["y"],
            icerik["x"]
        )
    )

    return "\n\n".join(
        icerik["metin"]
        for icerik in icerikler
    )


# --------------------------------------------------
# PDF OKUMA
# --------------------------------------------------

@st.cache_data(show_spinner=False, max_entries=128)
def pdf_oku(dosya_yolu, dosya_hash):
    sayfalar = []

    with pymupdf.open(dosya_yolu) as pdf:
        for numara, sayfa in enumerate(
            pdf,
            start=1
        ):

            metin = sayfa_metnini_cikar(
                sayfa
            ).strip()

            if metin:
                sayfalar.append({
                    "sayfa": numara,
                    "metin": metin
                })

    return sayfalar


# --------------------------------------------------
# KELİME EŞLEŞTİRME
# --------------------------------------------------

def kelimeler(metin):
    return set(
        re.findall(
            r"[^\W_]+",
            metin.casefold()
        )
    )


def kelime_arama(soru, top_k=50):
    """Mevcut kelime puanlamas?yla ortak formatta aday par?alar d?nd?r?r."""
    if top_k <= 0:
        return []
    gereksiz = {
        "ve", "veya", "ile", "bir", "bu", "şu",
        "için", "bana", "göre", "olan", "nedir",
        "nasıl", "hangi", "hakkında", "özetle",
        "söyle", "yaz", "mısın", "misin", "mi",
        "ne", "kaç", "var", "mı", "mu", "mü",
        "lütfen", "belge", "doküman", "pdf"
    }

    aranan = kelimeler(soru) - gereksiz

    if not aranan:
        return []

    sonuclar = []

    for belge in belgeleri_getir():
        try:
            print(
                "Belge getirme işlemi başladı - "
                + str(
                    datetime.datetime.now(
                        datetime.timezone.utc
                    ).timestamp()
                )
            )

            sayfalar = pdf_oku(
                belge["dosya_yolu"],
                belge["hash"]
            )

            dosya_kelimeleri = (
                kelimeler(belge["ad"]) - gereksiz
            )

            print(
                "Nokta 1 - "
                + str(
                    datetime.datetime.now(
                        datetime.timezone.utc
                    ).timestamp()
                )
            )

            for sayfa in sayfalar:
                metin = sayfa["metin"]

                print(
                    "Nokta 2 - "
                    + str(
                        datetime.datetime.now(
                            datetime.timezone.utc
                        ).timestamp()
                    )
                )

                for baslangic in range(
                    0,
                    len(metin),
                    1200
                ):
                    parca = metin[
                        baslangic:baslangic + 1200
                    ]

                    puan = len(
                        aranan & kelimeler(parca)
                    )

                    if aranan & dosya_kelimeleri:
                        puan += 3

                    if puan > 0:
                        sonuclar.append({
                            "pdf_id": belge["id"],
                            "chunk_id": f"{belge['id']}_{sayfa['sayfa']}_{baslangic}",
                            "page": sayfa["sayfa"],
                            "text": parca,
                            "puan": puan,
                            "ad": belge["ad"],
                            "sayfa": sayfa["sayfa"],
                            "metin": parca
                        })

            print(
                "Nokta 3 - "
                + str(
                    datetime.datetime.now(
                        datetime.timezone.utc
                    ).timestamp()
                )
            )

        except Exception as hata:
            print(
                f"PDF okunamadı: "
                f"{belge['ad']} - {hata}"
            )

            print(
                "Nokta 4 - "
                + str(
                    datetime.datetime.now(
                        datetime.timezone.utc
                    ).timestamp()
                )
            )

    sonuclar.sort(
        key=lambda sonuc: sonuc["puan"],
        reverse=True
    )

    return sonuclar[:top_k]


<<<<<<< HEAD
    return "\n\n---\n\n".join(metinler)


def get_pdf_dicts():
    """
    Kayıtlı tüm PDF belgelerini okur ve her biri için dosya adı ve sayfa içeriklerini 
    barındıran bir sözlük oluşturarak liste halinde döndürür.
    """
    belgeler = belgeleri_getir()
    sonuc_listesi = []
    
    for belge in belgeler:
        # İstenen yapının temelini oluştur (filename anahtarı)
        pdf_verisi = {
            "filename": belge["ad"]
        }
        
        try:
            # Ön belleğe alınmış (cached) okuma fonksiyonu ile PDF sayfalarını al
            sayfalar = pdf_oku(belge["dosya_yolu"], belge["hash"])
            
            # Her bir sayfayı sözlüğe sayfa numarası anahtarı ile ekle
            for sayfa in sayfalar:
                sayfa_no = sayfa["sayfa"]
                metin = sayfa["metin"]
                pdf_verisi[sayfa_no] = metin
                
        except Exception as hata:
            print(f"PDF okunurken hata oluştu ({belge['ad']}): {hata}")
            # Hata olsa bile dosyayı listeye ekliyoruz, sayfaları eksik olacak.
            
        sonuc_listesi.append(pdf_verisi)
        
    return sonuc_listesi
=======
def ilgili_bolumleri_bul(soru, maksimum_bolum=3):
    """Eski metin aray?z?n? korur; puanlama kelime_arama ile ortakt?r."""
    return "\n\n---\n\n".join(
        f"Dosya: {sonuc['ad']}\n"
        f"Sayfa: {sonuc['page']}\n"
        f"{sonuc['text']}"
        for sonuc in kelime_arama(soru, top_k=maksimum_bolum)
    )
>>>>>>> Reranker
