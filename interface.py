import streamlit as st

def run():
    # Web arayüzüne ilişkin kod burada bulunacak.
    st.set_page_config(
        page_title="Axxon AI",
        page_icon="✦",
        layout="wide",
        initial_sidebar_state="expanded",
        )

    sidebar = st.sidebar
    sidebar.container()
   
    st.title("Axxon AI")
    st.subheader("")

    tab_chat, tab_docs = st.tabs(["Chat", "Documents"], key="active_tab")

    user_input = ""
    


    with tab_chat:
        user_input = st.chat_input("Chat...")
    with tab_docs:
        user_input = ""
        

    tab_docs.write("Dokümanlarınızı buradan yükleyebilirsiniz.")
    f_uploader = tab_docs.file_uploader(label="PDF Yükle", type="PDF")
    
    
    if user_input:
        c = st.chat_message(name="user")
        c.write(user_input)
        c = st.chat_message(name="ai")
        c.write("Ok bruder. you sadid: " + user_input)
        