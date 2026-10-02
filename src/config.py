"""Load and validate application configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


REQUIRED_ENV_VARS = (
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "OPENAI_API_KEY",
    "SERPER_API_KEY",
    "DB_USER",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_PASSWORD",
)


@dataclass(frozen=True)
class AppConfig:
    """Validated application settings."""

    supabase_url: str
    supabase_key: str = field(repr=False)
    openai_api_key: str = field(repr=False)
    serper_api_key: str = field(repr=False)
    db_user: str
    db_host: str
    db_port: int
    db_name: str
    db_password: str = field(repr=False)


def load_config(env_file: str | Path | None = None) -> AppConfig:
    """Load required settings from the environment and an optional dotenv file.

    Existing environment values take precedence over values in ``env_file``.
    Raises:
        ValueError: If required variables are missing or invalid.
    """
    load_dotenv(dotenv_path=env_file, override=False)

    values = {name: os.getenv(name, "").strip() for name in REQUIRED_ENV_VARS}
    missing = [name for name, value in values.items() if not value]
    if missing:
        missing_names = ", ".join(missing)
        raise ValueError(
            f"Missing required environment variable(s): {missing_names}. "
            "Set them in the environment or in the dotenv file."
        )

    supabase_url = values["SUPABASE_URL"]
    parsed_url = urlsplit(supabase_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("SUPABASE_URL must be an absolute HTTP or HTTPS URL.")

    try:
        db_port = int(values["DB_PORT"])
    except ValueError as exc:
        raise ValueError("DB_PORT must be an integer between 1 and 65535.") from exc

    if not 1 <= db_port <= 65535:
        raise ValueError("DB_PORT must be an integer between 1 and 65535.")

    return AppConfig(
        supabase_url=supabase_url,
        supabase_key=values["SUPABASE_KEY"],
        openai_api_key=values["OPENAI_API_KEY"],
        serper_api_key=values["SERPER_API_KEY"],
        db_user=values["DB_USER"],
        db_host=values["DB_HOST"],
        db_port=db_port,
        db_name=values["DB_NAME"],
        db_password=values["DB_PASSWORD"],
    )
