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
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    if not api_key:
        raise GeminiConfigError("Missing GEMINI_API_KEY or GEMINI_KEY in .env")
    return api_key, model_name


def get_optional_serper_api_key() -> str | None:
    load_env_file()
    return os.getenv("SERPER_API_KEY") or os.getenv("SERPER_KEY")


def get_database_url() -> str:
    load_env_file()

    direct_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("DB_URL")
        or os.getenv("POSTGRES_URL")
    )
    if direct_url:
        return direct_url

    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME")
    db_driver = os.getenv("DB_DRIVER", "postgresql+psycopg")

    required = {
        "DB_USER": db_user,
        "DB_PASSWORD": db_password,
        "DB_HOST": db_host,
        "DB_NAME": db_name,
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        raise GeminiConfigError(
            "Missing database configuration. Set DATABASE_URL/DB_URL or provide "
            + ", ".join(missing)
            + " in .env"
        )

    return f"{db_driver}://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
