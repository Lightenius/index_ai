
from pathlib import Path
import re
import uuid

import streamlit as st
import file_manager
import data_manager

# These must already exist in your project:
# data_manager
# file_manager

DOCUMENTS_DIR = Path("./documents").resolve()
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


def safe_pdf_name(filename: str) -> str:
    """Return a safe, simple PDF filename."""
    filename = Path(filename).name
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)
    filename = filename.strip(" .")

    if not filename:
        filename = f"belge_{uuid.uuid4().hex[:8]}.pdf"

    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    return filename


def get_document_info(doc_id):
    """Read document metadata without assuming the ID is a filename."""
    try:
        data = data_manager.document.get_document_data(doc_id)
        if not isinstance(data, dict):
            return {"name": str(doc_id), "size": 0}
        return data
    except Exception:
        return {"name": str(doc_id), "size": 0}


def get_file_path(filename: str) -> Path:
    """Resolve a document path without allowing directory traversal."""
    path = (DOCUMENTS_DIR / Path(filename).name).resolve()

    if path.parent != DOCUMENTS_DIR:
        raise ValueError("Geçersiz dosya yolu.")

    return path


def format_size(size):
    try:
        size = float(size)
    except (TypeError, ValueError):
        return "Bilinmiyor"

    if size < 1024:
        return f"{size:.0f} B"
    if size < 1024**2:
        return f"{size / 1024:.1f} KB"
    if size < 1024**3:
        return f"{size / 1024**2:.1f} MB"
    return f"{size / 1024**3:.2f} GB"


def load_chat_ids():
    data_manager.chat.load_chat_data()
    try:
        return list(data_manager.chat.get_chat_ids())
    except Exception as exc:
        st.error(f"Sohbetler yüklenemedi: {exc}")
        return []


def render_sidebar():
    with st.sidebar:
        st.title("✦ Axxon AI")
        st.caption("Teknik bilgi asistanı")

        if st.button(
            "＋  Yeni sohbet",
            key="new_chat",
            use_container_width=True,
        ):
            # The actual chat must be created by your chat manager.
            # This only clears the current selection.
            st.session_state.selected_chat_id = None
            st.rerun()

        st.divider()
        st.subheader("Sohbet geçmişi")

        chat_ids = load_chat_ids()
        print(f"Loaded chat IDs: {chat_ids}", flush=True)

        if not chat_ids:
            st.caption("Henüz kayıtlı sohbet yok.")

        for chat_id in chat_ids:
            try:
                name = data_manager.chat.get_chat_name(chat_id)
            except Exception:
                name = None

            label = str(name if name else "Yeni sohbet").strip()
            if not label:
                label = "Yeni sohbet"

            is_selected = (
                st.session_state.selected_chat_id == chat_id
            )

            # A compact navigation item instead of a default button.
            st.markdown(
                """
                <style>
                div[data-testid="stSidebar"] div.stButton > button {
                    text-align: left;
                    border: none;
                    box-shadow: none;
                    background: transparent;
                    justify-content: flex-start;
                    padding: 0.45rem 0.65rem;
                    border-radius: 0.5rem;
                }
                div[data-testid="stSidebar"] div.stButton > button:hover {
                    background: rgba(128, 128, 128, 0.15);
                }
                </style>
                """,
                unsafe_allow_html=True,
            )

            prefix = "▸ " if is_selected else "　"
            if st.button(
                prefix + label,
                key=f"chat_{chat_id}",
                use_container_width=True,
                type="secondary",
            ):
                st.session_state.selected_chat_id = chat_id
                st.rerun()

        st.divider()
        st.caption("Şirket içi teknik bilgi sistemi")


def render_chat():
    st.header("Sohbet")

    chat_id = st.session_state.selected_chat_id

    if chat_id is None:
        st.info(
            "Yeni bir sohbet başlatmak için aşağıdaki alana "
            "mesajınızı yazın."
        )
    else:
        try:
            messages = data_manager.chat.get_chat(chat_id) or []
        except Exception as exc:
            messages = []
            st.error(f"Sohbet geçmişi yüklenemedi: {exc}")

        for item in messages:
            if not isinstance(item, dict):
                continue

            role_name = str(item.get("name", "")).strip().lower()
            content = item.get("content", "")
            date = item.get("date", "")

            if content is None:
                continue

            # Map stored author names to Streamlit chat roles.
            if role_name in ("user", "human", "kullanıcı"):
                role = "user"
            else:
                role = "assistant"

            with st.chat_message(role):
                st.markdown(str(content))
                if date:
                    st.caption(str(date))

    # Streamlit places chat_input at the bottom of the chat page.
    prompt = st.chat_input("Mesajınızı yazın...")

    if prompt:
        if st.session_state.selected_chat_id is None:
            #st.warning(
            #    "Mesaj gönderme işlemi için sohbet oluşturma "
            #    "fonksiyonunun chat manager üzerinden bağlanması gerekiyor."
            #)
            
            st.session_state.selected_chat_id = data_manager.chat.create_new_chat_with_msg(prompt)

            st.rerun()    
            return

        data_manager.chat.add_message(
            st.session_state.selected_chat_id,
            "user",
            prompt,
        )

        st.rerun()
        # Connect your existing LLM/chat service here.
        # Save the user message and assistant response using
        # your chat manager's actual write methods.
        st.info(
            "Mesaj alındı. LLM çağrısı ve sohbet kayıt fonksiyonları "
            "mevcut veri yöneticinizin API'sine bağlanmalıdır."
        )


def render_documents():
    st.header("Dokümanlar")
    st.caption("PDF dosyalarını yükleyin ve mevcut dokümanları yönetin.")

    with st.expander("＋ Yeni PDF yükle", expanded=False):
        uploaded_file = st.file_uploader(
            "PDF dosyası seçin",
            type=["pdf"],
            accept_multiple_files=False,
            key="pdf_uploader",
        )

        if uploaded_file is not None:
            if st.button(
                "Dokümanı yükle",
                type="primary",
                key="upload_document",
            ):
                filename = safe_pdf_name(uploaded_file.name)
                print(f"Trying to upload: {filename}")
                try:
                    target = get_file_path(filename)

                    if target.exists():
                        st.error(
                            "Bu isimde bir dosya zaten mevcut. "
                            "Lütfen dosya adını değiştirin."
                        )
                    else:
                        content = uploaded_file.getvalue()

                        if not content.startswith(b"%PDF-"):
                            st.error("Geçerli bir PDF dosyası seçin.")
                        else:
                            # Create through the application's file manager.
                            file_manager.create_file(filename, content)
                            st.success(f"{filename} yüklendi.")
                            st.rerun()

                except Exception as exc:
                    st.error(f"Yükleme başarısız: {exc}")

    st.divider()

    try:
        doc_ids = data_manager.document.get_doc_ids() or []
    except Exception as exc:
        st.error(f"Doküman listesi alınamadı: {exc}")
        return

    if not doc_ids:
        st.info("Henüz yüklenmiş doküman bulunmuyor.")
        return

    for doc_id in doc_ids:
        info = get_document_info(doc_id)
        filename = str(info.get("name") or doc_id)
        size = info.get("size", 0)

        with st.container(border=True):
            col_info, col_actions = st.columns([4, 2])

            with col_info:
                st.markdown(f"**📄 {filename}**")
                st.caption(f"Boyut: {format_size(size)}")

            with col_actions:
                rename_key = f"rename_{doc_id}"
                delete_key = f"delete_{doc_id}"

                if st.button(
                    "Adını değiştir",
                    key=rename_key,
                    use_container_width=True,
                ):
                    st.session_state[f"renaming_{doc_id}"] = True

                if st.button(
                    "Sil",
                    key=delete_key,
                    use_container_width=True,
                ):
                    st.session_state[f"deleting_{doc_id}"] = True

            if st.session_state.get(f"renaming_{doc_id}", False):
                with st.form(f"rename_form_{doc_id}"):
                    new_name = st.text_input(
                        "Yeni dosya adı",
                        value=Path(filename).stem,
                        key=f"new_name_{doc_id}",
                    )
                    confirm = st.form_submit_button("Kaydet")
                    cancel = st.form_submit_button("İptal")

                    if cancel:
                        st.session_state[f"renaming_{doc_id}"] = False
                        st.rerun()

                    if confirm:
                        new_filename = safe_pdf_name(new_name)

                        if new_filename == filename:
                            st.session_state[f"renaming_{doc_id}"] = False
                            st.rerun()

                        try:
                            old_path = get_file_path(filename)
                            new_path = get_file_path(new_filename)

                            if not old_path.exists():
                                st.error("Kaynak dosya bulunamadı.")
                            elif new_path.exists():
                                st.error("Bu isimde bir dosya zaten mevcut.")
                            else:
                                # Expected signature:
                                # rename_file(old_filename, new_filename)
                                file_manager.rename_file(
                                    filename,
                                    new_filename,
                                )
                                st.session_state[
                                    f"renaming_{doc_id}"
                                ] = False
                                st.success("Doküman adı değiştirildi.")
                                st.rerun()

                        except Exception as exc:
                            st.error(f"Ad değiştirme başarısız: {exc}")

            if st.session_state.get(f"deleting_{doc_id}", False):
                st.warning(
                    f"'{filename}' dokümanını silmek istediğinizden "
                    "emin misiniz?"
                )

                yes_col, no_col = st.columns(2)

                with yes_col:
                    if st.button(
                        "Evet, sil",
                        key=f"confirm_delete_{doc_id}",
                        type="primary",
                    ):
                        try:
                            file_manager.delete_file(filename)
                            st.session_state.pop(
                                f"deleting_{doc_id}", None
                            )
                            st.success("Doküman silindi.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Silme başarısız: {exc}")

                with no_col:
                    if st.button(
                        "Vazgeç",
                        key=f"cancel_delete_{doc_id}",
                    ):
                        st.session_state.pop(
                            f"deleting_{doc_id}", None
                        )
                        st.rerun()


def run():
    st.set_page_config(
        page_title="Axxon AI",
        page_icon="✦",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if "selected_chat_id" not in st.session_state:
        st.session_state.selected_chat_id = None

    render_sidebar()

    tab_chat, tab_docs = st.tabs(["Sohbet", "Dokümanlar"])

    with tab_chat:
        render_chat()

    with tab_docs:
        render_documents()


if __name__ == "__main__":
    run()
