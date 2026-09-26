import importlib.util
import os
from typing import Any

from config import get_config

def create_gemini_model() -> Any:
    if importlib.util.find_spec("google.generativeai") is None:
        raise ModuleNotFoundError("Missing dependency: install google-generativeai")

    import google.generativeai as genai

    api_key, model_name = get_config()
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


def create_langchain_gemini_model(
    temperature: float = 0.2,
    model_name: str | None = None,
) -> Any:
    if importlib.util.find_spec("langchain_google_genai") is None:
        raise ModuleNotFoundError("Missing dependency: install langchain-google-genai")

    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key, default_model_name = get_config()
    resolved_model_name = model_name or os.getenv("GEMINI_MODEL") or default_model_name

    return ChatGoogleGenerativeAI(
        model=resolved_model_name,
        google_api_key=api_key,
        temperature=temperature,
    )


def get_gemini_response(messages: list[dict[str, str]], model: Any) -> str:
    transcript = "\n".join(
        f"{entry['role']}: {entry['content']}" for entry in messages
    )
    request_prompt = (
        "Continue this conversation as a helpful assistant.\n\n"
        f"{transcript}\nassistant:"
    )
    response = model.generate_content(request_prompt)
    return (response.text or "").strip()


def get_langchain_gemini_response(prompt: str, model: Any | None = None) -> str:
    active_model = model or create_langchain_gemini_model()
    response = active_model.invoke(prompt)
    content = getattr(response, "content", "")

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part).strip()

    return str(content or "").strip()
