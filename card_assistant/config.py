"""Настройки из переменных окружения и файла .env."""

import json
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


class ConfigError(Exception):
    """Настройки заданы неверно. Текст сообщения показываем пользователю."""


@dataclass(frozen=True)
class Settings:
    base_url: str
    model: str
    # repr=False: ключ не попадёт в лог, даже если кто-то напечатает Settings
    api_key: str = field(default="", repr=False)
    extra_body: dict = field(default_factory=dict)
    timeout_seconds: float = 120.0
    max_attempts: int = 3

    @property
    def is_local(self) -> bool:
        # host.docker.internal: Ollama на этом компьютере, если сервис запущен в контейнере
        return any(
            host in self.base_url for host in ("localhost", "127.0.0.1", "host.docker.internal")
        )

    def check_ready(self) -> None:
        if not self.is_local and not self.api_key:
            raise ConfigError(
                "Не задан ключ API. Скопируйте .env.example в .env и впишите ключ в LLM_API_KEY."
            )


def load_settings(env_file: str | None = None) -> Settings:
    """Читает настройки. Переменные окружения важнее файла .env."""
    load_dotenv(env_file or ".env", override=False)

    extra_raw = os.getenv("LLM_EXTRA_BODY", "").strip()
    try:
        extra_body = json.loads(extra_raw) if extra_raw else {}
        return Settings(
            base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/"),
            model=os.getenv("LLM_MODEL", "qwen2.5:3b"),
            api_key=os.getenv("LLM_API_KEY", "").strip(),
            extra_body=extra_body,
            timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "120")),
            max_attempts=int(os.getenv("LLM_MAX_ATTEMPTS", "3")),
        )
    except ValueError as exc:
        raise ConfigError(
            "Ошибка в .env: LLM_EXTRA_BODY должен быть JSON, "
            "LLM_TIMEOUT_SECONDS и LLM_MAX_ATTEMPTS должны быть числами."
        ) from exc
