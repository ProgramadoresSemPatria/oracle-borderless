"""Configuração de logging da aplicação."""

import logging
from logging.config import dictConfig

from src.support.core.settings import settings


def configure_logging() -> None:
    """Configura o logging raiz conforme o ambiente."""
    level = "DEBUG" if settings.DEBUG else "INFO"

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                },
            },
            "root": {
                "handlers": ["console"],
                "level": level,
            },
            "loggers": {
                "uvicorn.access": {"level": "INFO"},
                "sqlalchemy.engine": {"level": "WARNING"},
                "apscheduler": {"level": "INFO"},
            },
        }
    )
    logging.getLogger(__name__).debug("Logging configurado (level=%s)", level)
