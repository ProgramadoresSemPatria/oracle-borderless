"""Runner de seeds com tracking idempotente via tabela `seeds_executions`.

Cada seed é uma classe com `@staticmethod async def seed()`. Registre-a na lista
`seeders` abaixo. Rode com `python -m database.seeds`.
"""

import logging

from sqlalchemy import select

from src.support.core.context import CurrentAsyncSessionContext
from src.support.core.database import AsyncSessionLocal
from src.support.core.models.seed_execution import SeedExecution
from src.support.core.settings import settings

logger = logging.getLogger(__name__)


async def is_seed_executed(session, seed_name: str) -> bool:
    result = await session.execute(
        select(SeedExecution).where(SeedExecution.seed_name == seed_name)
    )
    return result.scalar_one_or_none() is not None


async def mark_seed_executed(session, seed_name: str) -> None:
    session.add(SeedExecution(seed_name=seed_name))
    await session.flush()


def _collect_seeders() -> list:
    """Lista ordenada de seeds. Adicione novas seeds aqui (ordem = dependência)."""
    seeders: list = [
        # from database.seeds.document_sources_seed import DocumentSourcesSeed
        # DocumentSourcesSeed,
    ]

    if settings.ENVIRONMENT == "development":
        from database.seeds.dev_documents_seed import DevDocumentsSeed
        seeders.append(DevDocumentsSeed)

    return seeders


async def run_all_seeders() -> None:
    async with AsyncSessionLocal() as session:
        CurrentAsyncSessionContext.set(session)

        for seeder in _collect_seeders():
            seed_name = seeder.__name__
            if await is_seed_executed(session, seed_name):
                logger.info("Pulando seed já executada: %s", seed_name)
                continue

            await seeder.seed()
            await mark_seed_executed(session, seed_name)
            logger.info("Seed executada: %s", seed_name)

        await session.commit()
        CurrentAsyncSessionContext.clear()
