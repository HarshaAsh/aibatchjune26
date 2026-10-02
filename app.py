"""Streamlit entry point for the financial intelligence chat interface."""

import streamlit as st


CHAT_PASSWORD = "password"


st.set_page_config(
    page_title="Enterprise Financial Intelligence Chatbot",
    layout="wide",
)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "chat_authenticated" not in st.session_state:
    st.session_state.chat_authenticated = False

st.title("Enterprise Financial Intelligence Chatbot")

with st.sidebar:
    st.subheader("Chat controls")
    password = st.text_input("Password", type="password")
    if st.button("Unlock chat", use_container_width=True):
        if password == CHAT_PASSWORD:
            st.session_state.chat_authenticated = True
            st.success("Chat unlocked.")
        else:
            st.session_state.chat_authenticated = False
            st.error("Incorrect password.")

    if st.button("Clear chat", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

if st.session_state.chat_authenticated:
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask a financial question")
    if prompt:
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        st.session_state.chat_history.append(
            {"role": "assistant", "content": f"You said: {prompt}"}
        )
        st.rerun()
else:
    st.info("Enter the password in the sidebar to start chatting.")