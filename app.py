
import base64
import json
import re
import uuid
import threading

from datetime import datetime
from pathlib import Path

import streamlit as st
from ollama import Client

from documents import (
    belgeleri_getir,
    belge_ekle,
    belge_sil,
    ilgili_bolumleri_bul
)

import documents
import SemanticRetriever
print("Semantik indexleme başladı.")
pdf_dicts = documents.get_pdf_dicts()
retriever = SemanticRetriever.SemanticRetriever()
retriever.index(pdf_dicts)
print("Semantik indexleme tamamlandı.")

st.set_page_config(
    page_title="Şirket AI",
    layout="wide",
    initial_sidebar_state="expanded"
)


klasor = Path(__file__).resolve().parent
sohbet_dosyasi = klasor / "chats.json"

client = Client(host="http://127.0.0.1:11434")

sohbet_kilidi = threading.RLock()


# ARAYÜZ
st.markdown("""
<style>
.block-container {
    max-width: 100%;
    padding: 1.2rem 2.5rem 2rem;
}

h1 {
    font-size: 28px !important;
    font-weight: 600 !important;
}

/* Sol menü */
section[data-testid="stSidebar"] {
    background-color: #f9f9f9;
    width: 280px !important;
    min-width: 280px !important;
    border-right: 1px solid #ececec;
}

section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    padding: 0.5rem 0.75rem 1rem;
}

section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    gap: 0.35rem;
}

section[data-testid="stSidebar"] button {
    border: none;
    background: transparent;
    color: #333;
    text-align: left;
    justify-content: flex-start;
    box-shadow: none;
    border-radius: 8px;
    min-height: 40px;
    padding: 0.5rem 0.75rem;
    font-size: 14px;
}

section[data-testid="stSidebar"] button p {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    text-align: left;
    font-size: 14px;
}

section[data-testid="stSidebar"] button[kind="primary"] {
    background: #e9e9e9;
    color: #111;
    font-weight: 500;
}

.sidebar-brand {
    font-size: 19px;
    font-weight: 650;
    color: #202123;
    padding: 0.25rem 0.75rem 1rem;
}

.sidebar-label {
    font-size: 12px;
    font-weight: 500;
    color: #777;
    padding: 1.1rem 0.75rem 0.4rem;
}

section[data-testid="stSidebar"] [data-testid="stTextInput"] input {
    font-size: 13px;
}

.st-key-sohbet_listesi {
    max-height: calc(100dvh - 330px);
    min-height: 120px;
    overflow-y: auto;
    overflow-x: hidden;
    scrollbar-width: thin;
}

.st-key-sohbet_islemleri {
    border-top: 1px solid #e6e6e6;
    margin-top: 1rem;
    padding-top: 0.6rem;
}

section[data-testid="stSidebar"] button:hover {
    background: #eaeaea;
    color: #111;
}

/* Sohbet mesajları */
[data-testid="stChatMessage"] {
    padding: 10px 14px;
    border-radius: 7px;
    margin-bottom: 6px;
}

/* Doküman tekrar uyarısı */
[data-testid="stExpander"]:has(.tekrar-belge) {
    border: 1px solid #d4a72c;
}

[data-testid="stExpander"]:has(.tekrar-belge) summary {
    background: #fff3cd;
    border-radius: 5px;
}
</style>
""", unsafe_allow_html=True)


# SOHBET DOSYASI İŞLEMLERİ

def sohbetleri_getir():
    with sohbet_kilidi:
        if not sohbet_dosyasi.exists():
            return []

        with open(sohbet_dosyasi, "r", encoding="utf-8") as f:
            return json.load(f)


def sohbetleri_kaydet(sohbetler):
    gecici = sohbet_dosyasi.with_suffix(".tmp")

    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(
            sohbetler,
            f,
            ensure_ascii=False,
            indent=2
        )

    gecici.replace(sohbet_dosyasi)


def sohbet_bul(sohbet_id):
    for sohbet in sohbetleri_getir():
        if sohbet["id"] == sohbet_id:
            return sohbet

    return None


def mesaj_ekle(sohbet_id, rol, metin):
    with sohbet_kilidi:
        sohbetler = sohbetleri_getir()

        sohbet = next(
            (s for s in sohbetler if s["id"] == sohbet_id),
            None
        )

        if sohbet is None:
            sohbet = {
                "id": sohbet_id,
                "baslik": "Yeni sohbet",
                "mesajlar": [],
                "tarih": datetime.now().isoformat(
                    timespec="seconds"
                )
            }
            sohbetler.insert(0, sohbet)

        sohbet["mesajlar"].append({
            "role": rol,
            "content": metin
        })

        if rol == "user" and sohbet["baslik"] == "Yeni sohbet":
            sohbet["baslik"] = (
                metin[:40] + ("..." if len(metin) > 40 else "")
            )

        sohbetleri_kaydet(sohbetler)


def sohbet_sil(sohbet_id):
    with sohbet_kilidi:
        sohbetler = [
            s for s in sohbetleri_getir()
            if s["id"] != sohbet_id
        ]

        sohbetleri_kaydet(sohbetler)


def selamlama_mi(metin):
    temiz = re.sub(
        r"[^\w\s]",
        "",
        metin.casefold()
    ).strip()

    return temiz in {
        "selam",
        "merhaba",
        "hey",
        "günaydın",
        "iyi günler",
        "iyi akşamlar",
        "selamlar"
    }


# OTURUM DEĞİŞKENLERİ

if "aktif_sohbet" not in st.session_state:
    st.session_state.aktif_sohbet = None

if "upload_key" not in st.session_state:
    st.session_state.upload_key = 0

if "tekrar_belge" not in st.session_state:
    st.session_state.tekrar_belge = None

if "silme_onayi" not in st.session_state:
    st.session_state.silme_onayi = None

if "bildirim" not in st.session_state:
    st.session_state.bildirim = None

if "sohbet_silme_onayi" not in st.session_state:
    st.session_state.sohbet_silme_onayi = False


# SOL SOHBET MENÜSÜ

with st.sidebar:
    st.markdown('<div class="sidebar-brand">Şirket AI</div>', unsafe_allow_html=True)

    if st.button(
        "Yeni sohbet",
        icon=":material/edit_square:",
        use_container_width=True
    ):
        # Henüz dosyaya kaydedilmez
        st.session_state.aktif_sohbet = None
        st.session_state.sohbet_silme_onayi = False
        st.rerun()

    arama = st.text_input(
        "Sohbetlerde ara",
        placeholder="Sohbetlerde ara",
        label_visibility="collapsed",
        key="sohbet_arama"
    ).strip().casefold()

    st.markdown('<div class="sidebar-label">Sohbetlerin</div>', unsafe_allow_html=True)

    sohbetler = [
        sohbet for sohbet in sohbetleri_getir()
        if not arama or arama in sohbet["baslik"].casefold()
    ]

    with st.container(key="sohbet_listesi"):
        if not sohbetler:
            st.caption("Sohbet bulunamadı." if arama else "İlk sohbetini başlat.")

        for sohbet in sohbetler:
            if st.button(
                sohbet["baslik"],
                key=f"sohbet_{sohbet['id']}",
                type="primary" if sohbet["id"] == st.session_state.aktif_sohbet else "secondary",
                use_container_width=True
            ):
                st.session_state.aktif_sohbet = sohbet["id"]
                st.session_state.sohbet_silme_onayi = False
                st.rerun()

    aktif_id = st.session_state.aktif_sohbet

    if aktif_id is not None and sohbet_bul(aktif_id):
        with st.container(key="sohbet_islemleri"):
            silme_istendi = st.button("Sohbeti sil", icon=":material/delete:", use_container_width=True)

        if silme_istendi:
            st.session_state.sohbet_silme_onayi = True
            st.rerun()

        if st.session_state.sohbet_silme_onayi:
            st.caption("Bu sohbet silinsin mi?")

            sil, iptal = st.columns(2)

            with sil:
                if st.button("Sil", key="sohbet_sil_onay"):
                    sohbet_sil(aktif_id)
                    st.session_state.aktif_sohbet = None
                    st.session_state.sohbet_silme_onayi = False
                    st.rerun()

            with iptal:
                if st.button("İptal", key="sohbet_sil_iptal"):
                    st.session_state.sohbet_silme_onayi = False
                    st.rerun()


# ANA SAYFA

st.title("Şirket AI")

sohbet_tab, dokuman_tab = st.tabs([
    "Sohbet",
    "Dokümanlar"
])


# SOHBET

with sohbet_tab:
    sol_bos, orta, sag_bos = st.columns([1, 4, 1])

    with orta:
        aktif_id = st.session_state.aktif_sohbet

        if aktif_id is None:
            gecmis = []
        else:
            sohbet = sohbet_bul(aktif_id)
            gecmis = sohbet["mesajlar"] if sohbet else []

        mesaj_alani = st.container(
            height=540,
            border=False
        )

        with mesaj_alani:
            if not gecmis:
                st.markdown("#### Nasıl yardımcı olabilirim?")

            for mesaj in gecmis:
                with st.chat_message(mesaj["role"]):
                    st.write(mesaj["content"])

        soru = st.chat_input(
            "Bir mesaj yazın...",
            key="mesaj_girisi"
        )

        if soru:
            # İlk mesaj gönderildiğinde sohbet oluştur
            if st.session_state.aktif_sohbet is None:
                st.session_state.aktif_sohbet = uuid.uuid4().hex

            aktif_id = st.session_state.aktif_sohbet

            # Kullanıcının mesajını hemen kaydet
            mesaj_ekle(aktif_id, "user", soru)

            # Mesajı model yanıtından önce ekranda göster
            with mesaj_alani:
                with st.chat_message("user"):
                    st.write(soru)

                with st.chat_message("assistant"):
                    try:
                        if selamlama_mi(soru):
                            cevap = "Merhaba! Nasıl yardımcı olabilirim?"

                        else:
                            with st.spinner("Yanıt hazırlanıyor..."):
                                #ilgili = ilgili_bolumleri_bul(soru)
                                

                                bols = retriever.retrieve(soru, 20)
                                print("Semantik arama gerçekleştirildi")
                                bolumler = ""

                                for bol in bols:
                                    bolumler += "\n--- File: " + bol["filename"] + " | Page :" + bol["page_number"] + " ---\n" + bol["content"] + "\n--- END of PASSAGE ---\n"
                                
                                sistem_mesaji = {
                                    "role": "system",
                                    "content": f"""
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
Dokümandan yararlandığında dosya adını ve sayfasını belirt.

Genel soruları kendi bilginle cevaplayabilirsin.
Verdiğin cevaplarda kendi bilgin veya yorumun olan kısımlar ile kaynak gösterebileceğin kanıtlı kısımları iki ayrı grupta yaz ve grup başlıklarında bu konudan bahset.

Düzgün bir türkçe kullan. Terimleri ise çevirmeden, orjinal dillerinde yaz.

İlgili doküman bölümleri:
{bolumler if bolumler else "İlgili bölüm bulunamadı."}
"""}
                                
                                onceki_mesajlar = sohbet_bul(
                                    aktif_id
                                )["mesajlar"][-6:]

                                print("\n\nGönderilen Prompt:\n\n" + str([sistem_mesaji]+onceki_mesajlar))

                                response = client.chat(
                                    model="qwen3:4b",
                                    messages=[
                                        sistem_mesaji
                                    ] + onceki_mesajlar,
                                    
                                    think=False,
                                    options={
                                        "num_ctx": 8192,
                                        "num_predict": 6000,
                                        "temperature": 0.3,
                                        "think": False
                                    }
                                )

                                print("CONTENT:", repr(response.message.content))
                                print("THINKING:", repr(getattr(response.message, "thinking", None)))
                                
                                ham_yanit = (
                                    response.message.content
                                    or "Yanıt oluşturulamadı."
                                )

                                temiz_yanit = re.sub(r".*?</think>", "", ham_yanit, flags=re.DOTALL).strip()
                                cevap = temiz_yanit if temiz_yanit else ham_yanit

                        st.write(cevap)
                        mesaj_ekle(
                            aktif_id,
                            "assistant",
                            cevap
                        )

                    except Exception as hata:
                        st.error(f"Bağlantı hatası: {hata}")

            st.rerun()


# DOKÜMANLAR

with dokuman_tab:
    st.subheader("Şirket Dokümanları")

    sol, sag = st.columns(
        [1, 1.3],
        gap="large"
    )

    with sol:
        st.markdown("#### Dosya Ekle")

        dosya = st.file_uploader(
            "PDF seçin",
            type=["pdf"],
            key=f"dosya_{st.session_state.upload_key}"
        )

        if st.button("Ekle"):
            if dosya is None:
                st.warning("Bir dosya seçin.")

            else:
                try:
                    eklendi, belge = belge_ekle(dosya)

                    if eklendi:
                        st.session_state.bildirim = (
                            f"{belge['ad']} eklendi."
                        )
                        st.session_state.tekrar_belge = None

                    else:
                        st.session_state.bildirim = None
                        st.session_state.tekrar_belge = belge["id"]

                    st.session_state.upload_key += 1
                    st.rerun()

                except Exception as hata:
                    st.error(f"Dosya eklenemedi: {hata}")

        if st.session_state.bildirim:
            st.success(st.session_state.bildirim)

    with sag:
        st.markdown("#### Kayıtlı Dosyalar")

        belgeler = belgeleri_getir()

        if not belgeler:
            st.info("Henüz dosya eklenmedi.")

        for belge in belgeler:
            belge_id = belge["id"]

            tekrar = (
                st.session_state.tekrar_belge == belge_id
            )

            with st.expander(
                belge["ad"],
                expanded=tekrar
            ):
                if tekrar:
                    st.markdown(
                        '<span class="tekrar-belge"></span>',
                        unsafe_allow_html=True
                    )
                    st.caption("Bu dosya zaten kayıtlı.")

                try:
                    with open(belge["dosya_yolu"], "rb") as f:
                        pdf = f.read()

                    pdf64 = base64.b64encode(
                        pdf
                    ).decode("ascii")

                    st.markdown(
                        f"""
                        <iframe
                            src="data:application/pdf;base64,{pdf64}"
                            width="100%"
                            height="430"
                            style="border:1px solid #ddd;">
                        </iframe>
                        """,
                        unsafe_allow_html=True
                    )

                    st.download_button(
                        "Dosyayı İndir",
                        data=pdf,
                        file_name=belge["ad"],
                        mime="application/pdf",
                        key=f"indir_{belge_id}"
                    )

                except Exception as hata:
                    st.error(f"PDF açılamadı: {hata}")

                if st.session_state.silme_onayi == belge_id:
                    st.write("Bu dosya silinsin mi?")

                    sil, iptal, bos = st.columns(
                        [1, 1, 6],
                        gap="small"
                    )

                    with sil:
                        if st.button(
                            "Sil",
                            key=f"sil_onay_{belge_id}",
                            use_container_width=True
                        ):
                            try:
                                belge_sil(belge_id)

                                st.session_state.silme_onayi = None
                                st.session_state.tekrar_belge = None
                                st.session_state.bildirim = (
                                    "Dosya silindi."
                                )

                                st.rerun()

                            except Exception as hata:
                                st.error(f"Silinemedi: {hata}")

                    with iptal:
                        if st.button(
                            "İptal",
                            key=f"iptal_{belge_id}",
                            use_container_width=True
                        ):
                            st.session_state.silme_onayi = None
                            st.rerun()

                else:
                    if st.button(
                        "Dosyayı Sil",
                        key=f"sil_{belge_id}"
                    ):
                        st.session_state.silme_onayi = belge_id
                        st.rerun()
