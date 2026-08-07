import os
from pathlib import Path


class GeminiConfigError(Exception):
    """Raised when required Gemini configuration is missing or invalid."""


def load_env_file(file_name: str = ".env") -> None:
    env_path = Path(file_name)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def get_config() -> tuple[str, str]:
    load_env_file()
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_KEY")
    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    if not api_key:
        raise GeminiConfigError("Missing GEMINI_API_KEY or GEMINI_KEY in .env")
    return api_key, model_name
