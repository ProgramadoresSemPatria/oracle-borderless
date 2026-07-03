"""JobScheduler — wrapper do APScheduler com jobstore PostgreSQL (coordenação distribuída)."""

import logging

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.support.core.database import sync_engine
from src.support.core.scheduling.schedule import Schedule, ScheduledJob

logger = logging.getLogger(__name__)


class JobScheduler:
    """Configura e opera o APScheduler.

    Jobstore em PostgreSQL (`apscheduler_jobs`) + `max_instances=1` garantem que,
    em múltiplas réplicas, cada job dispare uma única vez. O advisory lock em
    `Job.execute()` é a segunda linha de defesa.
    """

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler(
            jobstores={"default": SQLAlchemyJobStore(engine=sync_engine)},
            job_defaults={"max_instances": 1, "coalesce": True, "misfire_grace_time": 300},
            timezone="UTC",
        )

    @staticmethod
    def _build_trigger(entry: ScheduledJob):
        if entry.trigger == "cron":
            return CronTrigger(**entry.trigger_args)
        return IntervalTrigger(**entry.trigger_args)

    @staticmethod
    async def _run(job_class_path: str) -> None:
        # Importação tardia por nome evita serializar objetos no jobstore.
        module_name, class_name = job_class_path.rsplit(".", 1)
        module = __import__(module_name, fromlist=[class_name])
        job = getattr(module, class_name)()
        await job.execute()

    def register(self, schedule: Schedule) -> None:
        for entry in schedule.entries:
            path = f"{entry.job_class.__module__}.{entry.job_class.__name__}"
            self._scheduler.add_job(
                self._run,
                trigger=self._build_trigger(entry),
                args=[path],
                id=entry.job_id,
                replace_existing=True,
            )
            logger.info("Job registrado: %s (%s)", entry.job_id, entry.trigger)

    def start(self) -> None:
        self._scheduler.start()
        logger.info("Scheduler iniciado.")

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Scheduler encerrado.")
