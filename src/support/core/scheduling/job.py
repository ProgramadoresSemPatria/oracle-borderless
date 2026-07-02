"""Base class de jobs agendados — idempotência via advisory lock + job_executions."""

import logging
from abc import ABC, abstractmethod
from zlib import crc32

from sqlalchemy import text

from src.support.core.context import CurrentAsyncSessionContext
from src.support.core.database import AsyncSessionLocal
from src.support.core.models.job_execution import JobExecution

logger = logging.getLogger(__name__)


class Job(ABC):
    """Job agendado idempotente.

    Subclasses implementam `action()`. `execute()` (chamado pelo scheduler) envolve
    a lógica com um PostgreSQL advisory lock (evita execução concorrente entre
    réplicas) e registra a execução em `job_executions`.

    A lógica de `action()` ainda deve TOLERAR re-execução — o lock protege contra
    concorrência, não contra retentativas legítimas.
    """

    # Intervalo mínimo (segundos) entre execuções — opcional, checado pela subclasse.
    min_execution_interval: int | None = None

    @property
    def name(self) -> str:
        return type(self).__name__

    def _lock_key(self) -> int:
        # advisory lock usa bigint; crc32 do nome cabe em 32 bits assinados.
        return crc32(self.name.encode()) - 2**31

    @abstractmethod
    async def action(self) -> None:
        """Lógica do job. Deve ser idempotente."""
        raise NotImplementedError

    async def execute(self) -> None:
        """Ponto de entrada chamado pelo scheduler. Não sobrescrever normalmente."""
        async with AsyncSessionLocal() as session:
            CurrentAsyncSessionContext.set(session)

            acquired = await session.scalar(
                text("SELECT pg_try_advisory_lock(:key)"), {"key": self._lock_key()}
            )
            if not acquired:
                logger.info("Job %s já em execução em outra réplica — pulando.", self.name)
                return

            record = JobExecution(job_name=self.name, status="running")
            session.add(record)
            await session.flush()

            try:
                await self.action()
                record.status = "success"
                await session.commit()
                logger.info("Job %s concluído.", self.name)
            except Exception as exc:  # noqa: BLE001 — registra e re-lança
                await session.rollback()
                record.status = "failed"
                record.error = str(exc)[:2048]
                session.add(record)
                await session.commit()
                logger.error("Job %s falhou.", self.name, exc_info=True)
                raise
            finally:
                await session.execute(
                    text("SELECT pg_advisory_unlock(:key)"), {"key": self._lock_key()}
                )
                await session.commit()
                CurrentAsyncSessionContext.clear()
