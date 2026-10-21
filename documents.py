
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


@st.cache_data(show_spinner=False, max_entries=128)
def pdf_oku(dosya_yolu, dosya_hash):
    sayfalar = []

    with pymupdf.open(dosya_yolu) as pdf:
        for numara, sayfa in enumerate(pdf, start=1):
            metin = sayfa.get_text("text").strip()

            if metin:
                sayfalar.append({
                    "sayfa": numara,
                    "metin": metin
                })

    return sayfalar


def kelimeler(metin):
    return set(re.findall(r"[^\W_]+", metin.casefold()))


def ilgili_bolumleri_bul(soru, maksimum_bolum=3):
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
        return ""

    sonuclar = []

    for belge in belgeleri_getir():
        try:
            print("Belge getirme işlemi başladı - " + str(datetime.datetime.now(datetime.timezone.utc).timestamp()))
            
            sayfalar = pdf_oku(
                belge["dosya_yolu"],
                belge["hash"]
            )

            dosya_kelimeleri = kelimeler(belge["ad"]) - gereksiz
            print("Nokta 1 - " + str(datetime.datetime.now(datetime.timezone.utc).timestamp()))
            for sayfa in sayfalar:
                metin = sayfa["metin"]
                print("Nokta 2 - " + str(datetime.datetime.now(datetime.timezone.utc).timestamp()))

                for baslangic in range(0, len(metin), 1200):
                    parca = metin[baslangic:baslangic + 1200]

                    puan = len(aranan & kelimeler(parca))

                    if aranan & dosya_kelimeleri:
                        puan += 3

                    if puan > 0:
                        sonuclar.append({
                            "puan": puan,
                            "ad": belge["ad"],
                            "sayfa": sayfa["sayfa"],
                            "metin": parca
                        })
            print("Nokta 3 - " + str(datetime.datetime.now(datetime.timezone.utc).timestamp()))

        except Exception as hata:
            print(f"PDF okunamadı: {belge['ad']} - {hata}")
            print("Nokta 4 - " + str(datetime.datetime.now(datetime.timezone.utc).timestamp()))

    sonuclar.sort(
        key=lambda sonuc: sonuc["puan"],
        reverse=True
    )

    metinler = []
    print("Nokta 5 - " + str(datetime.datetime.now(datetime.timezone.utc).timestamp()))

    for sonuc in sonuclar[:maksimum_bolum]:
        metinler.append(
            f"Dosya: {sonuc['ad']}\n"
            f"Sayfa: {sonuc['sayfa']}\n"
            f"{sonuc['metin']}"
        )
    print("Nokta 6 (Tamamlandı) - " + str(datetime.datetime.now(datetime.timezone.utc).timestamp()))

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