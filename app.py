import os
from pathlib import Path
import importlib.util

import streamlit as st


def load_env_file(file_name=".env"):
    env_path = Path(file_name)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_config():
    load_env_file()
    cfg_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY")
    cfg_model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    return cfg_api_key, cfg_model_name


def get_gemini_response(messages, model):
    transcript = "\n".join(
        f"{entry['role']}: {entry['content']}" for entry in messages
    )
    request_prompt = (
        "Continue this conversation as a helpful assistant.\n\n"
        f"{transcript}\nassistant:"
    )
    response = model.generate_content(request_prompt)
    return (response.text or "").strip()


st.set_page_config(page_title="Gemini Chat", page_icon="chat")
st.title("Gemini Chatbot")

gemini_api_key, gemini_model_name = get_config()
if not gemini_api_key:
    st.error("Missing GEMINI_API_KEY or GEMINI_KEY in .env")
    st.stop()

if importlib.util.find_spec("google.generativeai") is None:
    st.error("Missing dependency: install google-generativeai")
    st.stop()

import google.generativeai as genai

genai.configure(api_key=gemini_api_key)
gemini_model = genai.GenerativeModel(gemini_model_name)

if "messages" not in st.session_state:
    st.session_state.messages = []

for chat_message in st.session_state.messages:
    with st.chat_message(chat_message["role"]):
        st.markdown(chat_message["content"])

if user_prompt := st.chat_input("Type your message"):
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            reply = get_gemini_response(st.session_state.messages, gemini_model)
            if not reply:
                reply = "No response returned."
        st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})
