"""Ambiente do Alembic. Target = BaseModel.metadata (dual: online async / offline)."""

import asyncio
import importlib
import pkgutil
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from src.support.core.models.base_model import BaseModel
from src.support.core.settings import settings

# Garante que TODOS os models (support + domínio) sejam importados e registrados
# em BaseModel.metadata antes do autogenerate.
import src.support.core.models  # noqa: F401,E402


def _import_all_domain_models() -> None:
    """Autodescobre e importa cada pacote `models` sob src/domain/*."""
    import src.domain as domain_pkg

    for ctx in pkgutil.iter_modules(domain_pkg.__path__):
        models_mod = f"src.domain.{ctx.name}.models"
        try:
            module = importlib.import_module(models_mod)
        except ModuleNotFoundError:
            continue
        # importa submódulos do pacote models/ para registrar cada Model
        if hasattr(module, "__path__"):
            for sub in pkgutil.iter_modules(module.__path__):
                if not sub.name.startswith("_"):
                    importlib.import_module(f"{models_mod}.{sub.name}")


_import_all_domain_models()

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url_async)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = BaseModel.metadata


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    """Exclui a tabela `apscheduler_jobs` do autogenerate (gerida pelo APScheduler)."""
    if type_ == "table" and name == "apscheduler_jobs":
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url_async,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        {"sqlalchemy.url": settings.database_url_async},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
