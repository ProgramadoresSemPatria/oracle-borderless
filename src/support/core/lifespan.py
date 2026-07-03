"""LifespanManager — centraliza startup/shutdown da aplicação FastAPI."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from src.support.core.database import dispose_engines
from src.support.core.logging import configure_logging
from src.support.core.settings import settings

logger = logging.getLogger(__name__)


class LifespanManager:
    """Orquestra warmup e teardown: logging, scheduler, pools de DB."""

    def __init__(self) -> None:
        self._scheduler = None

    async def startup(self) -> None:
        configure_logging()
        logger.info("Iniciando %s (env=%s)", settings.APP_NAME, settings.ENVIRONMENT)

        if settings.ENABLE_SCHEDULER:
            self._boot_scheduler()

    def _boot_scheduler(self) -> None:
        # Import tardio: só carrega o scheduler/registro quando habilitado.
        from src.app.console.schedule import schedule
        from src.support.core.scheduling import JobScheduler

        self._scheduler = JobScheduler()
        self._scheduler.register(schedule)
        self._scheduler.start()

    async def shutdown(self) -> None:
        if self._scheduler is not None:
            self._scheduler.shutdown()
        await dispose_engines()
        logger.info("%s encerrado.", settings.APP_NAME)


@asynccontextmanager
async def lifespan(app) -> AsyncIterator[None]:
    """Lifespan para `FastAPI(lifespan=lifespan)`."""
    manager = LifespanManager()
    await manager.startup()
    try:
        yield
    finally:
        await manager.shutdown()
