import importlib.util
from typing import Any

from config import get_config

def create_gemini_model() -> Any:
    if importlib.util.find_spec("google.generativeai") is None:
        raise ModuleNotFoundError("Missing dependency: install google-generativeai")

    import google.generativeai as genai

    api_key, model_name = get_config()
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


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
